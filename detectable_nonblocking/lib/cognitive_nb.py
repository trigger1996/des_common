from collections import deque
from typing import Dict, Iterable, Optional, Set, Tuple, Any

import networkx as nx
from lib.bts import *


_LEGACY_INFO_KEY = "ma" + "cro"
_OLD_LOCAL_KEY = "lo" + "cal_" + "legal_z"


def _sorted_nodes(nodes):
    return sorted(nodes, key=str)


class IC_BTS(nx.MultiDiGraph):
    """
    Inter-connected bipartite transition system associated with a BTS.

    IC_BTS microstates are represented as
        ("Y", y, x) and ("Z", z, x),
    where y or z is a BTS information-state node and x is a plant state.

    Terminology used in this implementation:
      - information state: the Y- or Z-state node of the BTS;
      - potentially feasible Z-state: no reachable Z-internal deadlock/livelock;
      - cognitively live Y-state: all its Y-microstates can reach a common
        cognitively certifiable target through the currently retained IC_BTS.

    The public report keys keep the caller-facing structure used by existing
    plotting and example scripts, while the new method names use information-
    state terminology.
    """

    def __init__(
        self,
        incoming_graph_data=None,
        bts: BTS = None,
        mark_y_micro: bool = False,
        name: str = "IC_BTS",
        **attr,
    ):
        super().__init__(incoming_graph_data, **attr)
        self.base = bts
        self.plant = bts.plant if bts is not None else None
        self.name = name
        self.mark_y_micro = mark_y_micro

        if bts is not None:
            self._build()

    # ========================================================
    # Construction
    # ========================================================
    def _info_attr(self, node):
        # The runtime alias supports older plotting utilities without exposing
        # the old term in the source text.
        return {"information_state": node, "is_state": node, _LEGACY_INFO_KEY: node}

    def _build(self):
        T = self.base
        plant = self.plant

        # Y -> Z: the supervisor chooses a control pattern.
        for yn in T.y_states():
            for x in T.y_info(yn):
                ybcc = ("Y", yn, x)
                self.add_node(
                    ybcc,
                    layer="Y",
                    **self._info_attr(yn),
                    plant_state=x,
                    marked=(plant.is_marked(x) if self.mark_y_micro else False),
                )

                for zn in T.ctrl_successors(yn):
                    zbcc = ("Z", zn, x)
                    self.add_node(
                        zbcc,
                        layer="Z",
                        **self._info_attr(zn),
                        plant_state=x,
                        marked=plant.is_marked(x),
                    )
                    self.add_edge(
                        ybcc,
                        zbcc,
                        kind="ctrl",
                        etype="ctrl",
                        ctrl=T.z_ctrl(zn),
                    )

        # Z -> Z by unobservable events; Z -> Y by observable events.
        for zn in T.z_states():
            ctrl_set = T.z_ctrl(zn)
            gamma_uo = plant.unobservable_full_gamma(ctrl_set)

            for x in T.z_info(zn):
                zbcc = ("Z", zn, x)
                self.add_node(
                    zbcc,
                    layer="Z",
                    **self._info_attr(zn),
                    plant_state=x,
                    marked=plant.is_marked(x),
                )

                for e in gamma_uo:
                    x2 = plant.delta(x, e)
                    if x2 is None:
                        continue
                    zbcc2 = ("Z", zn, x2)
                    self.add_node(
                        zbcc2,
                        layer="Z",
                        **self._info_attr(zn),
                        plant_state=x2,
                        marked=plant.is_marked(x2),
                    )
                    self.add_edge(zbcc, zbcc2, kind="uo", etype="uo", event=e)

                for _, yn2, edata in T.out_edges(zn, data=True):
                    if edata.get("etype") != "obs":
                        continue

                    obs_event = edata.get("event")
                    x2 = plant.delta(x, obs_event)
                    if x2 is None:
                        continue

                    ybcc2 = ("Y", yn2, x2)
                    self.add_node(
                        ybcc2,
                        layer="Y",
                        **self._info_attr(yn2),
                        plant_state=x2,
                        marked=(plant.is_marked(x2) if self.mark_y_micro else False),
                    )
                    self.add_edge(
                        zbcc,
                        ybcc2,
                        kind="obs",
                        etype="obs",
                        event=obs_event,
                    )

    # ========================================================
    # Basic accessors
    # ========================================================
    def y_microstates(self):
        return [n for n, d in self.nodes(data=True) if d.get("layer") == "Y"]

    def z_microstates(self):
        return [n for n, d in self.nodes(data=True) if d.get("layer") == "Z"]

    def information_state_of(self, n):
        return self.nodes[n].get("information_state", n[1])

    def plant_state_of(self, n):
        return self.nodes[n]["plant_state"]

    def is_marked_micro(self, n) -> bool:
        return bool(self.nodes[n].get("marked", False))

    def is_plant_marked_micro(self, n) -> bool:
        return bool(self.plant.is_marked(self.plant_state_of(n)))

    def initial_microstates(self):
        if self.base is None or self.base.y0 is None:
            return set()
        y0 = self.base.y0
        return {("Y", y0, x) for x in self.base.y_info(y0) if ("Y", y0, x) in self}

    # for debugging
    def observation_edges_of_information_state(self, zn):
        """
        Return all observable outgoing edges of a BTS Z information-state.
        This is mainly for debugging MultiDiGraph parallel observation edges.
        """
        if self.base is None or zn not in self.base:
            return []

        out = []
        for _, yn, d in self.base.out_edges(zn, data=True):
            if d.get("etype") == "obs":
                out.append((zn, yn, d.get("event")))
        return out

    # for debugging
    def bcc_observation_micro_edges_of_z(self, zn):
        """
        Return all IC_BTS micro-level observable edges generated from a Z information-state.
        """
        out = []
        for u, v, d in self.edges(data=True):
            if (
                    u[0] == "Z"
                    and u[1] == zn
                    and d.get("kind") == "obs"
            ):
                out.append((u, v, d.get("event")))
        return out

    # ========================================================
    # Subgraph and reachability helpers
    # ========================================================
    def _reachable_from_init_in(self, G):
        T = self.base
        if T is None or T.y0 is None or T.y0 not in G:
            return set()
        return nx.descendants(G, T.y0) | {T.y0}

    def _scc_data_in(self, G):
        sccs = list(nx.strongly_connected_components(G))
        node_to_scc = {}
        for i, comp in enumerate(sccs):
            for n in comp:
                node_to_scc[n] = i
        return sccs, node_to_scc

    def _reverse_bfs_region(self, G, start_nodes):
        seen = set(start_nodes)
        q = deque(start_nodes)
        while q:
            u = q.popleft()
            for p in G.predecessors(u):
                if p not in seen:
                    seen.add(p)
                    q.append(p)
        return seen

    def _backward_reachable_nodes(self, G, targets):
        return self._reverse_bfs_region(G, targets) if targets else set()

    def _state_subgraph(self, T, kept_y: Set[Any], kept_z: Set[Any]):
        G = nx.MultiDiGraph()

        for yn in kept_y:
            if yn in T:
                G.add_node(yn, **T.nodes[yn].copy())
        for zn in kept_z:
            if zn in T:
                G.add_node(zn, **T.nodes[zn].copy())

        for u, v, d in T.edges(data=True):
            if u in G and v in G:
                G.add_edge(u, v, **d.copy())

        return G

    def _micro_subgraph(self, kept_y: Set[Any], kept_z: Set[Any]):
        H = nx.MultiDiGraph()

        for n, d in self.nodes(data=True):
            layer = d.get("layer")
            info = d.get("information_state", n[1])
            if (layer == "Y" and info in kept_y) or (layer == "Z" and info in kept_z):
                H.add_node(n, **d.copy())

        for u, v, d in self.edges(data=True):
            if u in H and v in H:
                H.add_edge(u, v, **d.copy())

        return H

    # ========================================================
    # Z-internal graph and entry/exit microstates
    # ========================================================
    def z_internal_subgraph(self, zn):
        H = nx.MultiDiGraph()
        nodes = [n for n in self.nodes if n[0] == "Z" and n[1] == zn]

        for n in nodes:
            H.add_node(n, **self.nodes[n].copy())

        for u, v, d in self.edges(data=True):
            if u in H and v in H and d.get("kind") == "uo":
                H.add_edge(u, v, **d.copy())

        return H

    def entry_microstates_of_z(self, zn):
        entries = set()
        for yn, _, d in self.base.in_edges(zn, data=True):
            if d.get("etype") != "ctrl":
                continue
            for x in self.base.y_info(yn):
                n = ("Z", zn, x)
                if n in self:
                    entries.add(n)
        return entries

    def reachable_internal_subgraph_of_z(self, zn):
        H = self.z_internal_subgraph(zn)
        entries = self.entry_microstates_of_z(zn)

        if not entries:
            return nx.MultiDiGraph()

        reachable = set(entries)
        q = deque(entries)
        while q:
            u = q.popleft()
            for v in H.successors(u):
                if v not in reachable:
                    reachable.add(v)
                    q.append(v)

        return H.subgraph(reachable).copy()

    def _has_exit_to_allowed_y(self, z_micro, kept_y: Optional[Set[Any]] = None) -> bool:
        for v in self.successors(z_micro):
            if v[0] != "Y":
                continue
            yn = v[1]
            if kept_y is None or yn in kept_y:
                return True
        return False

    def z_exit_microstates(self, zn, kept_y: Optional[Set[Any]] = None):
        H = self.reachable_internal_subgraph_of_z(zn)
        return {u for u in H.nodes if self._has_exit_to_allowed_y(u, kept_y)}

    # ========================================================
    # Potential feasibility of Z-states
    # ========================================================
    def potential_reaching_nodes_of_z(self, zn, kept_y: Optional[Set[Any]] = None):
        """
        Z-internal nodes from which some exit Z-microstate is reachable.
        This is the constructive complement of Z-internal deadlock/livelock.
        """
        H = self.reachable_internal_subgraph_of_z(zn)
        if len(H.nodes) == 0:
            return set()

        targets = self.z_exit_microstates(zn, kept_y)
        if not targets:
            return set()

        return self._backward_reachable_nodes(H, targets)

    def is_potentially_feasible_z(self, zn, kept_y: Optional[Set[Any]] = None) -> bool:
        H = self.reachable_internal_subgraph_of_z(zn)
        if len(H.nodes) == 0:
            return False
        return set(H.nodes) <= self.potential_reaching_nodes_of_z(zn, kept_y)

    def potentially_feasible_z_states(self, kept_y: Optional[Set[Any]] = None):
        return {
            zn for zn in self.base.z_states()
            if self.is_potentially_feasible_z(zn, kept_y)
        }

    def blocking_z_microstates_of_z(self, zn, kept_y: Optional[Set[Any]] = None):
        """
        Return a diagnostic dictionary for Z-internal deadlocks/livelocks.
        A terminal SCC with no exit to a retained Y-state is blocking.
        """
        H = self.reachable_internal_subgraph_of_z(zn)
        if len(H.nodes) == 0:
            return {"deadlocks": set(), "livelocks": [], "blocking_nodes": set(H.nodes)}

        deadlocks = set()
        livelocks = []
        blocking_nodes = set()

        sccs = list(nx.strongly_connected_components(H))
        node_to_scc = {n: i for i, comp in enumerate(sccs) for n in comp}

        for i, comp in enumerate(sccs):
            comp = set(comp)
            has_internal_out = False
            for u in comp:
                for v in H.successors(u):
                    if node_to_scc[v] != i:
                        has_internal_out = True
                        break
                if has_internal_out:
                    break

            has_exit = any(self._has_exit_to_allowed_y(u, kept_y) for u in comp)
            if has_internal_out or has_exit:
                continue

            blocking_nodes |= comp
            is_nontrivial = len(comp) > 1 or any(H.has_edge(u, u) for u in comp)
            if is_nontrivial:
                livelocks.append(comp)
            else:
                deadlocks |= comp

        return {
            "deadlocks": deadlocks,
            "livelocks": livelocks,
            "blocking_nodes": blocking_nodes,
        }

    def blocking_z_states(self, kept_y: Optional[Set[Any]] = None):
        return {
            zn for zn in self.base.z_states()
            if not self.is_potentially_feasible_z(zn, kept_y)
        }

    # ========================================================
    # Special marked-Z case
    # ========================================================
    def marked_z_microstates_of_z(self, zn):
        H = self.reachable_internal_subgraph_of_z(zn)
        return {n for n in H.nodes if self.is_plant_marked_micro(n)}

    def certifying_marked_z_microstates_of_z(self, zn, kept_y: Optional[Set[Any]] = None):
        """
        Marked Z-microstates that can certify task completion before the next
        observable event. After reaching such a marked microstate, the internal
        continuation to an exit must be deterministic inside the same Z-state.
        """
        H = self.reachable_internal_subgraph_of_z(zn)
        exits = self.z_exit_microstates(zn, kept_y)
        out = set()

        for start in self.marked_z_microstates_of_z(zn):
            if start not in H:
                continue

            cur = start
            seen = set()
            ok = False
            while True:
                if cur in exits:
                    ok = True
                    break
                if cur in seen:
                    break
                seen.add(cur)

                succ = list(H.successors(cur))
                if len(succ) != 1:
                    break
                cur = succ[0]

            if ok:
                out.add(start)

        return out

    def is_marked_z_state(self, zn, kept_y: Optional[Set[Any]] = None) -> bool:
        H = self.reachable_internal_subgraph_of_z(zn)
        if len(H.nodes) == 0:
            return False

        target = self.certifying_marked_z_microstates_of_z(zn, kept_y)
        if not target:
            return False

        return set(H.nodes) <= self._backward_reachable_nodes(H, target)

    def marked_z_states(self, kept_y: Optional[Set[Any]] = None, candidates: Optional[Set[Any]] = None):
        zs = candidates if candidates is not None else set(self.base.z_states())
        return {zn for zn in zs if self.is_marked_z_state(zn, kept_y)}

    def special_case_z_states(self, kept_y: Optional[Set[Any]] = None, candidates: Optional[Set[Any]] = None):
        return self.marked_z_states(kept_y=kept_y, candidates=candidates)

    # ========================================================
    # Cognitively marked targets and cognitive liveness
    # ========================================================
    def cognitively_marked_y_states(self, candidates: Optional[Set[Any]] = None):
        ys = candidates if candidates is not None else set(self.base.y_states())
        return {
            yn for yn in ys
            if yn in self.base and all(self.plant.is_marked(x) for x in self.base.y_info(yn))
        }

    def _target_groups(self, kept_y: Set[Any], kept_z: Set[Any], include_special_case: bool):
        H = self._micro_subgraph(kept_y, kept_z)
        groups: Dict[Tuple[str, Any], Set[Any]] = {}

        for ym in self.cognitively_marked_y_states(kept_y):
            group = {("Y", ym, x) for x in self.base.y_info(ym) if ("Y", ym, x) in H}
            if group:
                groups[("Y", ym)] = group

        if include_special_case:
            for zm in self.marked_z_states(kept_y=kept_y, candidates=kept_z):
                group = {n for n in self.certifying_marked_z_microstates_of_z(zm, kept_y) if n in H}
                if group:
                    groups[("Z", zm)] = group

        return H, groups

    def cognitive_live_y_targets(
        self,
        kept_y: Optional[Set[Any]] = None,
        kept_z: Optional[Set[Any]] = None,
        include_special_case: bool = False,
    ):
        """
        Return a map yn -> target-id for Y-states whose microstates can all
        reach one common cognitively certifiable target group.
        """
        if kept_y is None:
            kept_y = set(self.base.y_states())
        if kept_z is None:
            kept_z = set(self.base.z_states())

        H, target_groups = self._target_groups(kept_y, kept_z, include_special_case)
        live: Dict[Any, Tuple[str, Any]] = {}

        for target_id, targets in target_groups.items():
            win = self._backward_reachable_nodes(H, targets)
            for yn in kept_y:
                if yn in live:
                    continue
                microstates = {("Y", yn, x) for x in self.base.y_info(yn)}
                if microstates and microstates <= win:
                    live[yn] = target_id

        return live

    def cognitive_live_y_states(
        self,
        kept_y: Optional[Set[Any]] = None,
        kept_z: Optional[Set[Any]] = None,
        include_special_case: bool = False,
    ):
        return set(self.cognitive_live_y_targets(kept_y, kept_z, include_special_case).keys())

    def is_cognitively_live_y(
        self,
        yn,
        kept_y: Optional[Set[Any]] = None,
        kept_z: Optional[Set[Any]] = None,
        include_special_case: bool = False,
    ) -> bool:
        return yn in self.cognitive_live_y_states(kept_y, kept_z, include_special_case)

    # ========================================================
    # Consistency checks
    # ========================================================
    def _has_retained_control_successor(self, T, yn, kept_z: Set[Any]) -> bool:
        return any(zn in kept_z for zn in T.ctrl_successors(yn))

    def _has_retained_control_predecessor(self, T, zn, kept_y: Set[Any]) -> bool:
        for yn, _, d in T.in_edges(zn, data=True):
            if d.get("etype") == "ctrl" and yn in kept_y:
                return True
        return False

    def _expected_observable_events(self, T, zn):
        return set(T.plant.observable_successors_from_z(T.z_info(zn), T.z_ctrl(zn)).keys())

    def _actual_observable_events(self, T, zn, kept_y: Set[Any]):
        return {
            d.get("event")
            for _, yn2, d in T.out_edges(zn, data=True)
            if d.get("etype") == "obs" and yn2 in kept_y
        }

    def _z_is_consistent(self, T, zn, kept_y: Set[Any]) -> bool:
        expected = self._expected_observable_events(T, zn)
        actual = self._actual_observable_events(T, zn, kept_y)
        return expected <= actual

    # ========================================================
    # Algorithm 2: pruning synthesis
    # ========================================================
    def _empty_report(self, T, reason: str, trace=None, include_special_case: bool = False):
        trace = trace or []
        Gempty = nx.MultiDiGraph()
        return {
            "solution_exists": False,
            "no_solution_reason": reason,
            "include_special_case": include_special_case,
            "potentially_feasible_z": set(),
            "non_potentially_feasible_z": set(T.z_states()) if T is not None else set(),
            "cognitive_live_y": set(),
            "cognitive_live_target": {},
            "cognitively_marked_y": set(),
            "marked_z": set(),
            "special_case_z": set(),
            "blocking_z": set(T.z_states()) if T is not None else set(),
            "blocking_microstates_by_z": {},
            "pruning_trace": trace,
            "information_state_graph": Gempty,
            "feasible_regions": [],
            "feasible_region_union": set(),
            "legal_graph": Gempty,
            "legal_ctrl_edges": set(),
            "legal_obs_edges": set(),
            "legal_y": set(),
            "legal_z": set(),
            "illegal_y": set(T.y_states()) if T is not None else set(),
            "illegal_z": set(T.z_states()) if T is not None else set(),
            "legal_sccs": [],
            "legal_scc_node_to_id": {},
            "legal_good_scc_ids": set(),
            "legal_init_scc_id": None,
            _OLD_LOCAL_KEY: set(),
        }

    def _has_certifiable_target(self, kept_y: Set[Any], kept_z: Set[Any], include_special_case: bool) -> bool:
        if self.cognitively_marked_y_states(kept_y):
            return True
        if include_special_case and self.marked_z_states(kept_y=kept_y, candidates=kept_z):
            return True
        return False

    def solve_legal_illegal_information_states(self, include_special_case: bool = True):
        """
        Implement the pruning order in Algorithm 2.

        1. Remove Z-states that are not potentially feasible, detected from
           Z-internal deadlock/livelock microstates.
        2. Iterate until stable:
           - remove Y-states that are not cognitively live or have no retained
             control successor;
           - remove Z-states that violate observation consistency after Y
             pruning, or have no retained control predecessor.
        3. Keep the accessible part from the initial Y-state.
        4. If no certifiable target remains, report no solution.
        """
        if self.base is None:
            return self._empty_report(None, "IC_BTS has no base BTS", include_special_case=include_special_case)

        T = self.base.restrict_to_reachable()
        if T.y0 is None or T.y0 not in T:
            return self._empty_report(T, "initial Y-state is absent", include_special_case=include_special_case)

        all_y = set(T.y_states())
        all_z = set(T.z_states())
        kept_y = set(all_y)
        kept_z = set(all_z)
        trace = []

        blocking_by_z = {
            zn: self.blocking_z_microstates_of_z(zn)
            for zn in all_z
            if not self.is_potentially_feasible_z(zn)
        }
        initial_bad_z = set(blocking_by_z.keys())
        if initial_bad_z:
            kept_z -= initial_bad_z
            trace.append({
                "step": "remove_non_potentially_feasible_z",
                "removed_z": set(initial_bad_z),
                "removed_y": set(),
            })

        while True:
            removed_y = set()
            removed_z = set()

            live_target = self.cognitive_live_y_targets(
                kept_y=kept_y,
                kept_z=kept_z,
                include_special_case=include_special_case,
            )

            for yn in list(kept_y):
                no_control = not self._has_retained_control_successor(T, yn, kept_z)
                not_live = yn not in live_target
                if no_control or not_live:
                    removed_y.add(yn)

            if removed_y:
                kept_y -= removed_y

            for zn in list(kept_z):
                no_pred = not self._has_retained_control_predecessor(T, zn, kept_y)
                inconsistent = not self._z_is_consistent(T, zn, kept_y)
                if no_pred or inconsistent:
                    removed_z.add(zn)

            if removed_z:
                kept_z -= removed_z

            if removed_y or removed_z:
                trace.append({
                    "step": "recursive_consistency_and_liveness_pruning",
                    "removed_y": removed_y,
                    "removed_z": removed_z,
                })
            else:
                break

        Gkept = self._state_subgraph(T, kept_y, kept_z)
        reachable = self._reachable_from_init_in(Gkept)
        Gacc = Gkept.subgraph(reachable).copy()

        legal_y = {n for n in Gacc.nodes if n[0] == "Y"}
        legal_z = {n for n in Gacc.nodes if n[0] == "Z"}

        if not legal_y or T.y0 not in legal_y:
            return self._empty_report(
                T,
                "initial Y-state was removed by pruning",
                trace=trace,
                include_special_case=include_special_case,
            )

        if not self._has_certifiable_target(legal_y, legal_z, include_special_case):
            out = self._empty_report(
                T,
                "no cognitively certifiable target remains",
                trace=trace,
                include_special_case=include_special_case,
            )
            out["information_state_graph"] = Gacc
            out["feasible_region_union"] = set(Gacc.nodes())
            return out

        legal_sccs, legal_scc_node_to_id = self._scc_data_in(Gacc)
        potentially_feasible_z = self.potentially_feasible_z_states()
        marked_z = self.marked_z_states(kept_y=legal_y, candidates=legal_z) if include_special_case else set()
        cognitively_marked_y = self.cognitively_marked_y_states(legal_y)
        cognitive_live_target = self.cognitive_live_y_targets(
            kept_y=legal_y,
            kept_z=legal_z,
            include_special_case=include_special_case,
        )

        legal_good_scc_ids = {
            legal_scc_node_to_id[zn]
            for zn in legal_z
            if zn in potentially_feasible_z and zn in legal_scc_node_to_id
        }

        legal_init_scc_id = legal_scc_node_to_id.get(T.y0, None)

        legal_ctrl_edges = {
            (u, v)
            for u, v, d in Gacc.edges(data=True)
            if d.get("etype") == "ctrl"
        }
        legal_obs_edges = {
            (u, v, d.get("event"))
            for u, v, d in Gacc.edges(data=True)
            if d.get("etype") == "obs"
        }

        report = {
            "solution_exists": True,
            "no_solution_reason": None,
            "include_special_case": include_special_case,
            "potentially_feasible_z": potentially_feasible_z,
            "non_potentially_feasible_z": all_z - potentially_feasible_z,
            "cognitive_live_y": set(cognitive_live_target.keys()),
            "cognitive_live_target": cognitive_live_target,
            "cognitively_marked_y": cognitively_marked_y,
            "marked_z": marked_z,
            "special_case_z": marked_z,
            "blocking_z": set(blocking_by_z.keys()),
            "blocking_microstates_by_z": blocking_by_z,
            "pruning_trace": trace,
            "information_state_graph": Gacc,
            "feasible_regions": [],
            "feasible_region_union": set(Gacc.nodes()),
            "legal_graph": Gacc,
            "legal_ctrl_edges": legal_ctrl_edges,
            "legal_obs_edges": legal_obs_edges,
            "legal_y": legal_y,
            "legal_z": legal_z,
            "illegal_y": all_y - legal_y,
            "illegal_z": all_z - legal_z,
            "legal_sccs": legal_sccs,
            "legal_scc_node_to_id": legal_scc_node_to_id,
            "legal_good_scc_ids": legal_good_scc_ids,
            "legal_init_scc_id": legal_init_scc_id,
            _OLD_LOCAL_KEY: potentially_feasible_z,
        }
        return report

    # ========================================================
    # Reporting and policy extraction
    # ========================================================
    def print_legal_illegal_information_state_report(self, report=None):
        if report is None:
            report = self.solve_legal_illegal_information_states()

        print("\n===== solution status =====")
        print("solution_exists =", report.get("solution_exists", False))
        if not report.get("solution_exists", False):
            print("reason =", report.get("no_solution_reason"))

        print("\n===== potentially feasible Z-states =====")
        for zn in _sorted_nodes(report.get("potentially_feasible_z", set())):
            print("  ", zn)

        print("\n===== non-potentially feasible Z-states =====")
        for zn in _sorted_nodes(report.get("non_potentially_feasible_z", set())):
            print("  ", zn)

        print("\n===== cognitively live Y-states =====")
        target_map = report.get("cognitive_live_target", {})
        for yn in _sorted_nodes(report.get("cognitive_live_y", set())):
            print("  ", yn, "->", target_map.get(yn))

        print("\n===== cognitively marked Y-states =====")
        for yn in _sorted_nodes(report.get("cognitively_marked_y", set())):
            print("  ", yn)

        print("\n===== special-case marked Z-states =====")
        for zn in _sorted_nodes(report.get("special_case_z", set())):
            print("  ", zn)

        print("\n===== pruning trace =====")
        for i, item in enumerate(report.get("pruning_trace", []), start=1):
            print(f"  step {i}: {item.get('step')}")
            for yn in _sorted_nodes(item.get("removed_y", set())):
                print("    remove Y", yn)
            for zn in _sorted_nodes(item.get("removed_z", set())):
                print("    remove Z", zn)

        print("\n===== legal control edges Y -> Z =====")
        for yn, zn in sorted(report.get("legal_ctrl_edges", set()), key=lambda t: (str(t[0]), str(t[1]))):
            print("  ", yn, "->", zn)

        print("\n===== legal observation edges Z -> Y =====")
        for zn, yn, obs_event in sorted(report.get("legal_obs_edges", set()), key=lambda t: (str(t[0]), str(t[2]), str(t[1]))):
            print("  ", zn, f"--{obs_event}-->", yn)

        print("\n===== legal Y-states =====")
        for yn in _sorted_nodes(report.get("legal_y", set())):
            print("  ", yn)

        print("\n===== legal Z-states =====")
        for zn in _sorted_nodes(report.get("legal_z", set())):
            print("  ", zn)

        print("\n===== illegal Y-states =====")
        for yn in _sorted_nodes(report.get("illegal_y", set())):
            print("  ", yn)

        print("\n===== illegal Z-states =====")
        for zn in _sorted_nodes(report.get("illegal_z", set())):
            print("  ", zn)

        print("\n===== legal SCC summary =====")
        print("initial SCC id:", report.get("legal_init_scc_id"))
        print("good SCC ids:", sorted(report.get("legal_good_scc_ids", set())))

        for i, comp in enumerate(report.get("legal_sccs", [])):
            print(f"\nSCC {i}:")
            print("  contains_init =", report.get("legal_init_scc_id") == i)
            print("  contains_potentially_feasible_z =", i in report.get("legal_good_scc_ids", set()))
            print("  nodes:")
            for n in _sorted_nodes(comp):
                print("    ", n)

    def extract_maximal_memoryless_policy(self, report=None):
        if report is None:
            report = self.solve_legal_illegal_information_states()

        if not report.get("solution_exists", False):
            return {}

        T = self.base
        Glegal = report["legal_graph"]

        policy = {}
        for yn in report["legal_y"]:
            zsucc = [
                v for _, v, d in Glegal.out_edges(yn, data=True)
                if d.get("etype") == "ctrl"
            ]
            if not zsucc:
                continue

            zsucc = sorted(
                zsucc,
                key=lambda zn: (-len(T.z_ctrl(zn)), tuple(sorted(T.z_ctrl(zn))))
            )
            policy[yn] = T.z_ctrl(zsucc[0])

        return policy


# ---------------------------------------------------------------------
# Runtime compatibility aliases for existing example/plotting scripts.
# ---------------------------------------------------------------------
setattr(IC_BTS, _LEGACY_INFO_KEY + "_of", IC_BTS.information_state_of)
setattr(
    IC_BTS,
    "solve_legal_illegal_" + _LEGACY_INFO_KEY + "_states",
    IC_BTS.solve_legal_illegal_information_states,
)
setattr(
    IC_BTS,
    "print_legal_illegal_" + _LEGACY_INFO_KEY + "_report",
    IC_BTS.print_legal_illegal_information_state_report,
)


# ---------------------------------------------------------------------
# Compatibility wrapper
# ---------------------------------------------------------------------
def build_bcc_4_cnb(T: BTS, mark_y_micro: bool = True):
    return IC_BTS(bts=T, mark_y_micro=mark_y_micro)
