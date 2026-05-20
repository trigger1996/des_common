import networkx as nx
from collections import deque
from typing import Dict, FrozenSet, Iterable, Optional, Set

from lib.nfa import DESPlant


RawInfo = FrozenSet[int]
CtrlSet = FrozenSet[str]


# ============================================================
# 2. BTS / AIC / NB-AIC
# ============================================================

class BTS(nx.MultiDiGraph):
    """
    MultiDiGraph-based bipartite transition system.

    Graph node ids are wrappers around RAW information states.

    We use MultiDiGraph because the same Z information-state may reach the
    same Y information-state through different observable events. A DiGraph
    would silently overwrite one of these parallel Z->Y observation edges.

    Y-node id:
        ("Y", raw_y_info)

    Z-node id:
        ("Z", raw_z_info, ctrl_set)

    where
        raw_z_info = UR(raw_y_info, ctrl_set)
        ctrl_set   = enabled controllable events only
    """

    def __init__(self, incoming_graph_data=None, plant=None, name="BTS", **attr):
        super().__init__(incoming_graph_data, **attr)
        self.plant = plant
        self.name = name
        self.y0 = None

    @staticmethod
    def y_node(raw_y_info: RawInfo):
        return ("Y", frozenset(raw_y_info))

    @staticmethod
    def z_node(raw_z_info: RawInfo, ctrl_set: CtrlSet):
        return ("Z", frozenset(raw_z_info), frozenset(ctrl_set))

    def add_y_state(self, raw_y_info: RawInfo, *, initial=False):
        n = self.y_node(raw_y_info)
        self.add_node(n, kind="Y", info=frozenset(raw_y_info))
        if initial:
            self.y0 = n
        return n

    def add_z_state(self, raw_z_info: RawInfo, ctrl_set: CtrlSet):
        n = self.z_node(raw_z_info, ctrl_set)
        self.add_node(n, kind="Z", info=frozenset(raw_z_info), ctrl=frozenset(ctrl_set))
        return n

    def y_states(self):
        return [n for n, d in self.nodes(data=True) if d.get("kind") == "Y"]

    def z_states(self):
        return [n for n, d in self.nodes(data=True) if d.get("kind") == "Z"]

    def y_info(self, yn) -> RawInfo:
        return self.nodes[yn]["info"]

    def z_info(self, zn) -> RawInfo:
        return self.nodes[zn]["info"]

    def z_ctrl(self, zn) -> CtrlSet:
        return self.nodes[zn]["ctrl"]

    def ctrl_successors(self, yn):
        return [v for _, v, d in self.out_edges(yn, data=True) if d.get("etype") == "ctrl"]

    def obs_successors(self, zn):
        """
        Return observable successors as
            {observable_event: successor_Y_node}.

        Important:
            Since BTS is a MultiDiGraph, multiple observable edges may have the
            same source and target but different event labels, e.g.,
                z --o1--> y
                z --o3--> y
            Both events are preserved here as separate dictionary keys.
        """
        out = {}
        for _, v, d in self.out_edges(zn, data=True):
            if d.get("etype") != "obs":
                continue

            e = d["event"]
            if e in out and out[e] != v:
                raise ValueError(
                    f"Nondeterministic observable edge detected at {zn}: "
                    f"event {e!r} reaches both {out[e]} and {v}."
                )
            out[e] = v
        return out

    def has_ctrl_edge(self, yn, zn) -> bool:
        return any(
            v == zn and d.get("etype") == "ctrl"
            for _, v, d in self.out_edges(yn, data=True)
        )

    def has_obs_edge(self, zn, obs_event: str, yn=None) -> bool:
        for _, v, d in self.out_edges(zn, data=True):
            if d.get("etype") == "obs" and d.get("event") == obs_event:
                if yn is None or v == yn:
                    return True
        return False

    def add_yz_edge(self, raw_y_info: RawInfo, ctrl_set: CtrlSet):
        """
        Add edge:
            ("Y", raw_y_info) -> ("Z", UR(raw_y_info, ctrl_set), ctrl_set)
        """
        yn = self.add_y_state(raw_y_info)
        raw_z_info = self.plant.UR(raw_y_info, ctrl_set)
        zn = self.add_z_state(raw_z_info, ctrl_set)
        self.add_edge(yn, zn, etype="ctrl", ctrl=frozenset(ctrl_set))
        return yn, zn

    def add_zy_edge(self, raw_z_info: RawInfo, ctrl_set: CtrlSet, obs_event: str, raw_y_next: RawInfo):
        zn = self.add_z_state(raw_z_info, ctrl_set)
        yn = self.add_y_state(raw_y_next)
        self.add_edge(zn, yn, etype="obs", event=obs_event)
        return zn, yn

    def restrict_to_reachable(self):
        out = BTS(plant=self.plant, name=self.name + "_reachable")

        if self.y0 is None or self.y0 not in self:
            return out

        reachable = nx.descendants(self, self.y0) | {self.y0}

        # copy nodes
        for n in reachable:
            out.add_node(n, **self.nodes[n].copy())

        # copy edges inside reachable part
        for u, v, d in self.edges(data=True):
            if u in reachable and v in reachable:
                out.add_edge(u, v, **d.copy())

        out.y0 = self.y0
        return out

    def copy_bts(self, name=None):
        out = BTS(plant=self.plant, name=name or self.name)

        for n, d in self.nodes(data=True):
            out.add_node(n, **d.copy())

        for u, v, d in self.edges(data=True):
            out.add_edge(u, v, **d.copy())

        out.y0 = self.y0 if self.y0 in out else None
        return out


# ============================================================
# 3. AIC construction
# ============================================================

def build_aic(plant: DESPlant, keep_irredundant=True) -> BTS:
    """
    IMPORTANT DATA-FLOW SEPARATION:

    Queue elements are RAW Y-information states:
        frozenset({...})

    Graph nodes are wrappers:
        ("Y", frozenset({...}))
        ("Z", frozenset({...}), frozenset(ctrl_set))

    This avoids the bug of mixing graph node ids with raw information states.
    """
    if plant.x0 is None:
        raise ValueError("plant.x0 is not set")
    if not plant.is_legal(plant.x0):
        raise ValueError("initial state is illegal; AIC does not exist")

    T = BTS(plant=plant, name="AIC")

    raw_y0 = frozenset({plant.x0})
    T.add_y_state(raw_y0, initial=True)

    q = deque([raw_y0])
    seen_raw_y = {raw_y0}

    all_ctrl_choices = plant.all_enabled_controllable_sets()

    while q:
        raw_y = q.popleft()

        for ctrl_set in all_ctrl_choices:
            if keep_irredundant and not plant.is_irredundant_ctrl(raw_y, ctrl_set):
                continue

            # safety: UR^+(raw_y, ctrl_set) subseteq legal states
            if not all(plant.is_legal(x) for x in plant.UR_plus(raw_y, ctrl_set)):
                continue

            _, zn = T.add_yz_edge(raw_y, ctrl_set)
            raw_z = T.z_info(zn)

            for obs_event, raw_y_next in plant.observable_successors_from_z(raw_z, ctrl_set).items():
                T.add_zy_edge(raw_z, ctrl_set, obs_event, raw_y_next)
                if raw_y_next not in seen_raw_y:
                    seen_raw_y.add(raw_y_next)
                    q.append(raw_y_next)

    return T.restrict_to_reachable()


# ============================================================
# 4. ICS + liveness + deadlock-free + NB-AIC
# ============================================================

def build_ics(T: BTS):
    ICS = nx.MultiDiGraph()
    plant = T.plant

    for yn in T.y_states():
        raw_y = T.y_info(yn)
        for x in raw_y:
            yics = ("Y", yn, x)
            ICS.add_node(yics, marked=plant.is_marked(x))

            # 其实这个办法很讨巧
            for zn in T.ctrl_successors(yn):
                zics = ("Z", zn, x)
                ICS.add_node(zics, marked=plant.is_marked(x))
                ICS.add_edge(yics, zics)

    for zn in T.z_states():
        raw_z = T.z_info(zn)
        ctrl_set = T.z_ctrl(zn)
        gamma = plant.unobservable_full_gamma(ctrl_set) | plant.observable_full_gamma(ctrl_set)

        for x in raw_z:
            zics = ("Z", zn, x)
            ICS.add_node(zics, marked=plant.is_marked(x))

            for e in gamma & plant.Euo:
                x2 = plant.delta(x, e)
                if x2 is not None:              # 显然如果前面没求错的话, x2必然会在raw_z内
                    zics2 = ("Z", zn, x2)
                    ICS.add_node(zics2, marked=plant.is_marked(x2))
                    ICS.add_edge(zics, zics2, event=e)

            for obs_event, yn2 in T.obs_successors(zn).items():
                x2 = plant.delta(x, obs_event)
                if x2 is not None:
                    yics2 = ("Y", yn2, x2)
                    ICS.add_node(yics2, marked=plant.is_marked(x2))
                    ICS.add_edge(zics, yics2, event=obs_event)

    return ICS


def live_y_states(T: BTS):
    ICS = build_ics(T)
    marked_nodes = [n for n, d in ICS.nodes(data=True) if d.get("marked", False)]

    if not marked_nodes:
        return set()

    rev = ICS.reverse(copy=False)
    coacc = set(marked_nodes)
    q = deque(marked_nodes)

    while q:
        u = q.popleft()
        for p in rev.neighbors(u):
            if p not in coacc:
                coacc.add(p)
                q.append(p)

    live = set()
    for yn in T.y_states():
        raw_y = T.y_info(yn)
        if all(("Y", yn, x) in coacc for x in raw_y):
            live.add(yn)

    return live


def is_deadlock_free_z(T: BTS, zn) -> bool:
    plant = T.plant
    raw_z = T.z_info(zn)
    ctrl_set = T.z_ctrl(zn)
    gamma = plant.unobservable_full_gamma(ctrl_set) | plant.observable_full_gamma(ctrl_set)

    allowed_uo = gamma & plant.Euo
    allowed_o = gamma & plant.Eo

    for x0 in raw_z:
        q = deque([x0])
        seen = {x0}
        ok = False

        while q and not ok:
            x = q.popleft()

            if plant.is_marked(x):
                ok = True
                break

            if any(plant.delta(x, e) is not None for e in allowed_o):
                ok = True
                break

            for e in allowed_uo:
                x2 = plant.delta(x, e)
                if x2 is not None and x2 not in seen:
                    seen.add(x2)
                    q.append(x2)

        if not ok:
            return False

    return True


def prune_incomplete(T: BTS) -> BTS:
    cur = T.copy_bts(T.name + "_pruned")

    changed = True
    while changed:
        changed = False
        bad_nodes = set()

        for yn in cur.y_states():
            if len(cur.ctrl_successors(yn)) == 0:
                bad_nodes.add(yn)

        for zn in cur.z_states():
            raw_z = cur.z_info(zn)
            ctrl_set = cur.z_ctrl(zn)

            expected_obs = set(cur.plant.observable_successors_from_z(raw_z, ctrl_set).keys())
            actual_obs = set(cur.obs_successors(zn).keys())

            if expected_obs != actual_obs:
                bad_nodes.add(zn)

        if bad_nodes:
            cur.remove_nodes_from(bad_nodes)
            cur = cur.restrict_to_reachable()
            changed = True

    return cur


def build_nb_aic(plant: DESPlant) -> BTS:
    cur = build_aic(plant)
    cur = prune_incomplete(cur)

    while True:
        prev_nodes = set(cur.nodes())

        bad_z = [zn for zn in cur.z_states() if not is_deadlock_free_z(cur, zn)]
        if bad_z:
            cur.remove_nodes_from(bad_z)
            cur = cur.restrict_to_reachable()
            cur = prune_incomplete(cur)

        live = live_y_states(cur)
        bad_y = [yn for yn in cur.y_states() if yn not in live]
        if bad_y:
            cur.remove_nodes_from(bad_y)
            cur = cur.restrict_to_reachable()
            cur = prune_incomplete(cur)

        if set(cur.nodes()) == prev_nodes:
            break

    if cur.y0 is None or cur.y0 not in cur:
        raise RuntimeError("NB-AIC became empty; check the plant/model implementation")

    return cur


# ============================================================
# 5. Supervisor subtree + verification
# ============================================================

def build_subtree_from_policy(T: BTS, policy: Dict[tuple, CtrlSet]) -> BTS:
    U = BTS(plant=T.plant, name=T.name + "_subtree")

    if T.y0 is None or T.y0 not in T:
        return U

    U.add_y_state(T.y_info(T.y0), initial=True)

    q = deque([T.y0])
    seen_y = {T.y0}

    while q:
        yn = q.popleft()
        if yn not in policy:
            continue

        ctrl_set = frozenset(policy[yn])

        z_candidates = [
            zn for zn in T.ctrl_successors(yn)
            if T.z_ctrl(zn) == ctrl_set
        ]
        if not z_candidates:
            raise KeyError(
                f"policy assigns {ctrl_set} at Y-state {set(T.y_info(yn))}, "
                f"but this control edge is absent in BTS"
            )

        zn = z_candidates[0]
        raw_y = T.y_info(yn)
        raw_z = T.z_info(zn)

        U.add_yz_edge(raw_y, ctrl_set)

        for obs_event, yn2 in T.obs_successors(zn).items():
            raw_y2 = T.y_info(yn2)
            U.add_zy_edge(raw_z, ctrl_set, obs_event, raw_y2)
            if yn2 not in seen_y:
                seen_y.add(yn2)
                q.append(yn2)

    return U.restrict_to_reachable()


def classical_target_y(T: BTS):
    return {
        yn for yn in T.y_states()
        if any(T.plant.is_marked(x) for x in T.y_info(yn))
    }

def backward_reach_y(T: BTS, target_ys):
    H = nx.DiGraph()
    for yn in T.y_states():
        H.add_node(yn)

    for zn in T.z_states():
        pred_ys = [u for u, _, d in T.in_edges(zn, data=True) if d.get("etype") == "ctrl"]
        succ_ys = [v for _, v, d in T.out_edges(zn, data=True) if d.get("etype") == "obs"]

        for p in pred_ys:
            for s in succ_ys:
                H.add_edge(s, p)

    q = deque(target_ys)
    seen = set(target_ys)

    while q:
        y = q.popleft()
        for p in H.neighbors(y):
            if p not in seen:
                seen.add(p)
                q.append(p)

    return seen


def verify_classical_nb(T_sub: BTS) -> bool:
    R = set(T_sub.y_states())
    L = backward_reach_y(T_sub, classical_target_y(T_sub))
    return R == L

from dataclasses import dataclass


# ============================================================
# 9. Helpers on top of the current BTS / NB-AIC
# ============================================================

def raw_y_to_node(T: BTS, raw_y: RawInfo):
    n = BTS.y_node(raw_y)
    return n if n in T else None


def raw_z_to_node(T: BTS, raw_z: RawInfo, ctrl_set: CtrlSet):
    n = BTS.z_node(raw_z, ctrl_set)
    return n if n in T else None


def raw_y_ctrl_to_znode(T: BTS, raw_y: RawInfo, ctrl_set: CtrlSet):
    yn = raw_y_to_node(T, raw_y)
    if yn is None:
        return None
    ctrl_set = frozenset(ctrl_set)
    for zn in T.ctrl_successors(yn):
        if T.z_ctrl(zn) == ctrl_set:
            return zn
    return None


def subset_maximal_ctrl_choices(T: BTS, raw_y: RawInfo):
    """
    Return inclusion-maximal control choices available at raw_y in BTS T.
    """
    yn = raw_y_to_node(T, raw_y)
    if yn is None:
        return []

    choices = [frozenset(T.z_ctrl(zn)) for zn in T.ctrl_successors(yn)]
    out = []
    for c in choices:
        dominated = False
        for d in choices:
            if set(c) < set(d):
                dominated = True
                break
        if not dominated:
            out.append(c)

    # remove duplicates and sort: larger cardinality first, then lexicographically
    out = list(set(out))
    out.sort(key=lambda c: (-len(c), tuple(sorted(c))))
    return out


def choose_default_ctrl(candidates):
    """
    Pick one inclusion-maximal control choice.
    Default tie-break:
      larger cardinality first, then lexicographically.
    """
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda c: (-len(c), tuple(sorted(c))))
    return candidates[0]


def fig1_u0_ctrl_selector(raw_y: RawInfo, candidates):
    """
    Reproduce the paper-style U0 in Fig. 3 for Fig. 1:
      {0}   -> {}
      {1,2} -> {}
      {3,4} -> {c2}
      {5,6} -> {c1}
    """
    S = set(raw_y)
    pref = None
    if S == {0}:
        pref = frozenset()
    elif S == {1, 2}:
        pref = frozenset()
    elif S == {3, 4}:
        pref = frozenset({"c2"})
    elif S == {5, 6}:
        pref = frozenset({"c1"})

    if pref is not None and pref in candidates:
        return pref
    return choose_default_ctrl(candidates)


# ============================================================
# 10. UBTS / EBTS
# ============================================================

class UBTS(nx.MultiDiGraph):
    """
    MultiDiGraph-based unfolded BTS over a base BTS (typically the NB-AIC).

    Parallel observable edges must be preserved here as well; otherwise an EBTS
    can again lose transitions such as z --o1--> y and z --o3--> y when both
    reach the same Y-copy.

    Y-copy:
        ("Y", raw_y_info, idx)

    Z-copy:
        ("Z", raw_z_info, ctrl_set, idx)

    idx >= 0 : control copy
    idx < 0  : transient copy
    """

    def __init__(self, base_bts: BTS, name="UBTS"):
        super().__init__()
        self.base = base_bts
        self.plant = base_bts.plant
        self.name = name
        self.y0 = None

    @staticmethod
    def y_node(raw_y: RawInfo, idx: int):
        return ("Y", frozenset(raw_y), int(idx))

    @staticmethod
    def z_node(raw_z: RawInfo, ctrl_set: CtrlSet, idx: int):
        return ("Z", frozenset(raw_z), frozenset(ctrl_set), int(idx))

    def add_y_state(self, raw_y: RawInfo, idx: int, *, initial=False):
        n = self.y_node(raw_y, idx)
        self.add_node(n, kind="Y", info=frozenset(raw_y), idx=int(idx))
        if initial:
            self.y0 = n
        return n

    def add_z_state(self, raw_z: RawInfo, ctrl_set: CtrlSet, idx: int):
        n = self.z_node(raw_z, ctrl_set, idx)
        self.add_node(
            n,
            kind="Z",
            info=frozenset(raw_z),
            ctrl=frozenset(ctrl_set),
            idx=int(idx),
        )
        return n

    def y_states(self):
        return [n for n, d in self.nodes(data=True) if d.get("kind") == "Y"]

    def z_states(self):
        return [n for n, d in self.nodes(data=True) if d.get("kind") == "Z"]

    def y_info(self, yn):
        return self.nodes[yn]["info"]

    def z_info(self, zn):
        return self.nodes[zn]["info"]

    def y_idx(self, yn):
        return self.nodes[yn]["idx"]

    def z_idx(self, zn):
        return self.nodes[zn]["idx"]

    def z_ctrl(self, zn):
        return self.nodes[zn]["ctrl"]

    def ctrl_successors(self, yn):
        return [v for _, v, d in self.out_edges(yn, data=True) if d.get("etype") == "ctrl"]

    def obs_successors(self, zn):
        """
        Return observable successors as
            {observable_event: successor_Y_copy}.

        Because UBTS is also a MultiDiGraph, different observable events may
        share the same source and target while remaining distinct edges.
        """
        out = {}
        for _, v, d in self.out_edges(zn, data=True):
            if d.get("etype") != "obs":
                continue

            e = d["event"]
            if e in out and out[e] != v:
                raise ValueError(
                    f"Nondeterministic observable edge detected at {zn}: "
                    f"event {e!r} reaches both {out[e]} and {v}."
                )
            out[e] = v
        return out

    def has_ctrl_edge(self, ycopy, zcopy) -> bool:
        return any(
            v == zcopy and d.get("etype") == "ctrl"
            for _, v, d in self.out_edges(ycopy, data=True)
        )

    def has_obs_edge(self, zcopy, obs_event: str, ycopy=None) -> bool:
        for _, v, d in self.out_edges(zcopy, data=True):
            if d.get("etype") == "obs" and d.get("event") == obs_event:
                if ycopy is None or v == ycopy:
                    return True
        return False

    def add_yz_edge(self, ycopy, zcopy):
        self.add_edge(ycopy, zcopy, etype="ctrl", ctrl=self.z_ctrl(zcopy))

    def add_zy_edge(self, zcopy, obs_event, ycopy):
        self.add_edge(zcopy, ycopy, etype="obs", event=obs_event)

    def copy_ubts(self, name=None):
        U = UBTS(self.base, name=name or self.name)
        for n, d in self.nodes(data=True):
            U.add_node(n, **d.copy())
        for u, v, d in self.edges(data=True):
            U.add_edge(u, v, **d.copy())
        U.y0 = self.y0 if self.y0 in U else None
        return U


def print_ubts_edges(U: UBTS, title="UBTS edges"):
    print(f"\n===== {title} =====")
    for u, v, d in U.edges(data=True):
        if d.get("etype") == "ctrl":
            print(f"{u} --ctrl {U.plant.ctrl_to_str(U.z_ctrl(v))}--> {v}")
        elif d.get("etype") == "obs":
            print(f"{u} --{d.get('event')}--> {v}")
        else:
            print(f"{u} --{d}--> {v}")


# ============================================================
# 11. Index rules in the UBTS / EXPAND
# ============================================================

def count_same_nonneg_y_predecessors(U: UBTS, node, raw_y: RawInfo) -> int:
    raw_y = frozenset(raw_y)
    cnt = 0
    for p in nx.ancestors(U, node):
        if U.nodes[p].get("kind") == "Y" and U.y_info(p) == raw_y and U.y_idx(p) >= 0:
            cnt += 1
    return cnt


def count_same_nonneg_z_predecessors(U: UBTS, node, raw_z: RawInfo, ctrl_set: CtrlSet) -> int:
    raw_z = frozenset(raw_z)
    ctrl_set = frozenset(ctrl_set)
    cnt = 0
    for p in nx.ancestors(U, node):
        if (
            U.nodes[p].get("kind") == "Z"
            and U.z_info(p) == raw_z
            and U.z_ctrl(p) == ctrl_set
            and U.z_idx(p) >= 0
        ):
            cnt += 1
    return cnt


# ============================================================
# 12. EXPAND: build initial UBTS U0 and complete later Ui
# ============================================================

def expand_ubts(U: UBTS, ctrl_selector=None):
    """
    EXPAND(U) in the spirit of the paper.

    Rule A:
      For any Y-copy y^n with no control successor and n = 0,
      choose one inclusion-maximal control decision and add y^n -> z^m.

    Rule B:
      For any Z-copy z^n with some observable successor defined in the base NB-AIC
      but absent in U, add that observable edge z^n -obs-> y^m.

    The successor index m is determined by the paper's counting rule:
      m = number of nonnegative predecessor copies with the same raw component.
    """
    base = U.base

    while True:
        changed = False

        # -------------------------
        # A. Add one control choice at each base Y-copy y^0 lacking one
        # -------------------------
        for ycopy in list(U.y_states()):
            if U.y_idx(ycopy) != 0:
                continue
            if len(U.ctrl_successors(ycopy)) > 0:
                continue

            raw_y = U.y_info(ycopy)
            candidates = subset_maximal_ctrl_choices(base, raw_y)
            if not candidates:
                continue

            ctrl = ctrl_selector(raw_y, candidates) if ctrl_selector is not None else choose_default_ctrl(candidates)
            if ctrl is None:
                continue

            z_base = raw_y_ctrl_to_znode(base, raw_y, ctrl)
            if z_base is None:
                continue

            raw_z = base.z_info(z_base)
            z_idx = count_same_nonneg_z_predecessors(U, ycopy, raw_z, ctrl)
            zcopy = U.add_z_state(raw_z, ctrl, z_idx)
            if not U.has_ctrl_edge(ycopy, zcopy):
                U.add_yz_edge(ycopy, zcopy)
                changed = True

        # -------------------------
        # B. Add all missing observable successors at every Z-copy
        # -------------------------
        pending = []
        for zcopy in list(U.z_states()):
            raw_z = U.z_info(zcopy)
            ctrl = U.z_ctrl(zcopy)
            z_base = raw_z_to_node(base, raw_z, ctrl)
            if z_base is None:
                continue

            full_obs = base.obs_successors(z_base)
            cur_obs = U.obs_successors(zcopy)

            for obs_event, y_base in full_obs.items():
                if obs_event not in cur_obs:
                    raw_y_next = base.y_info(y_base)
                    pending.append((zcopy, obs_event, raw_y_next))

        for zcopy, obs_event, raw_y_next in pending:
            y_idx = count_same_nonneg_y_predecessors(U, zcopy, raw_y_next)
            ycopy = U.add_y_state(raw_y_next, y_idx)
            if not U.has_obs_edge(zcopy, obs_event, ycopy):
                U.add_zy_edge(zcopy, obs_event, ycopy)
                changed = True

        if not changed:
            break

    return U


def build_initial_u0(nb_aic: BTS, ctrl_selector=None) -> UBTS:
    U = UBTS(nb_aic, name="U0")
    U.add_y_state(nb_aic.y_info(nb_aic.y0), 0, initial=True)
    expand_ubts(U, ctrl_selector=ctrl_selector)
    return U


# ============================================================
# 13. Merge terminal repeated Y-copies to obtain the EBTS
# ============================================================

def merge_ubts_to_ebts(U: UBTS) -> UBTS:
    """
    Construct the EBTS \\tilde U by removing terminal repeated Y-copies
    y^n, n>=1, and redirecting all incoming edges to y^0.
    """
    E = UBTS(U.base, name=U.name + "_merged")

    terminal_repeated_y = {
        yn
        for yn in U.y_states()
        if U.y_idx(yn) >= 1 and len(U.ctrl_successors(yn)) == 0
    }

    # copy non-removed nodes
    for n, d in U.nodes(data=True):
        if n not in terminal_repeated_y:
            E.add_node(n, **d.copy())

    # redirect edges
    for u, v, d in U.edges(data=True):
        if u in terminal_repeated_y:
            continue

        vv = v
        if v in terminal_repeated_y:
            raw_y = U.y_info(v)
            vv = UBTS.y_node(raw_y, 0)
            if vv not in E:
                E.add_y_state(raw_y, 0, initial=(vv == U.y0))

        if u in E and vv in E:
            E.add_edge(u, vv, **d.copy())

    E.y0 = U.y0 if U.y0 in E else UBTS.y_node(U.y_info(U.y0), 0)
    return E


# ============================================================
# 14. Induced automaton / product / livelock detection
# ============================================================

def unique_ctrl_successor(U: UBTS, ycopy):
    zs = U.ctrl_successors(ycopy)
    if len(zs) == 0:
        return None
    if len(zs) > 1:
        raise ValueError(f"UBTS/EBTS violated: Y-copy {ycopy} has more than one control successor.")
    return zs[0]


def build_product_graph_from_ebts(E: UBTS):
    """
    Build the product graph of the induced supervisor automaton A_U and the plant G.

    Product state:
        (ycopy, x)
    """
    plant = E.plant
    P = nx.MultiDiGraph()

    if E.y0 is None:
        return P

    start = (E.y0, plant.x0)
    q = deque([start])
    seen = {start}

    while q:
        state = q.popleft()
        ycopy, x = state
        P.add_node(state, marked=plant.is_marked(x), ycopy=ycopy, x=x)

        zcopy = unique_ctrl_successor(E, ycopy)
        if zcopy is None:
            continue

        ctrl = E.z_ctrl(zcopy)
        gamma_uo = plant.unobservable_full_gamma(ctrl)
        gamma_o = plant.observable_full_gamma(ctrl)

        # unobservable enabled events keep the EBTS Y-copy
        for e in gamma_uo:
            x2 = plant.delta(x, e)
            if x2 is None:
                continue
            nxt = (ycopy, x2)
            P.add_edge(state, nxt, event=e, observable=False)
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)

        # observable enabled events jump to the successor Y-copy
        obs_succ = E.obs_successors(zcopy)
        for obs_event, y2copy in obs_succ.items():
            x2 = plant.delta(x, obs_event)
            if x2 is None:
                continue
            nxt = (y2copy, x2)
            P.add_edge(state, nxt, event=obs_event, observable=True)
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)

    return P


def find_closed_unmarked_scc(P: nx.DiGraph):
    """
    Find one closed SCC in the product that contains no marked plant state.
    """
    for comp in nx.strongly_connected_components(P):
        if any(P.nodes[q].get("marked", False) for q in comp):
            continue

        # need an actual cycle
        has_cycle = False
        if len(comp) > 1:
            has_cycle = True
        else:
            q = next(iter(comp))
            if P.has_edge(q, q):
                has_cycle = True
        if not has_cycle:
            continue

        # closedness
        closed = True
        for q in comp:
            for nxt in P.successors(q):
                if nxt not in comp:
                    closed = False
                    break
            if not closed:
                break

        if closed:
            return comp

    return None


def find_one_celc_and_entrance(U: UBTS):
    """
    Detect one product-livelock SCC in the merged EBTS and return:
        (entrance_y_copy, corresponding_state, scc, merged_ebts, product_graph)

    The entrance Y-copy is chosen as a terminal repeated Y-copy y^n, n>=1,
    whose base copy y^0 lies in the livelock SCC of the merged EBTS product.
    """
    E = merge_ubts_to_ebts(U)
    P = build_product_graph_from_ebts(E)
    scc = find_closed_unmarked_scc(P)
    if scc is None:
        return None

    base_y_in_scc = {ycopy for (ycopy, _x) in scc}

    candidates = []
    for yterm in U.y_states():
        if U.y_idx(yterm) < 1:
            continue
        if len(U.ctrl_successors(yterm)) != 0:
            continue

        raw_y = U.y_info(yterm)
        ybase = UBTS.y_node(raw_y, 0)
        if ybase not in base_y_in_scc:
            continue

        xs = [x for (yy, x) in scc if yy == ybase and x in raw_y]
        for x in xs:
            candidates.append((yterm, x))

    if not candidates:
        return None

    # deterministic choice
    candidates.sort(key=lambda t: (len(U.y_info(t[0])), tuple(sorted(U.y_info(t[0]))), U.y_idx(t[0]), t[1]))
    yentr, xcorr = candidates[0]
    return yentr, xcorr, scc, E, P


# ============================================================
# 15. Greedy search for a locally-maximal live decision string
# ============================================================

@dataclass
class LiveRun:
    decisions: list               # [ctrl_set_1, ..., ctrl_set_n]
    observables: list             # [obs_1, ..., obs_{n-1}]
    y_seq: list                   # [y0, y1, ..., y_{n-1}]
    z_seq: list                   # [(z1, c1), ..., (zn, cn)]
    end_x: int


def sorted_maximal_z_choices(base: BTS, raw_y: RawInfo):
    yn = raw_y_to_node(base, raw_y)
    if yn is None:
        return []

    zsucc = base.ctrl_successors(yn)
    ctrls = [base.z_ctrl(zn) for zn in zsucc]

    maximal_ctrls = []
    for c in ctrls:
        if not any(set(c) < set(d) for d in ctrls):
            maximal_ctrls.append(c)

    maximal_ctrls = list(set(maximal_ctrls))
    maximal_ctrls.sort(key=lambda c: (-len(c), tuple(sorted(c))))

    out = []
    for c in maximal_ctrls:
        zn = raw_y_ctrl_to_znode(base, raw_y, c)
        if zn is not None:
            out.append(zn)
    return out


def find_greedy_live_run(base: BTS, raw_y0: RawInfo, x0: int):
    """
    Find one live decision string for (raw_y0, x0) in the base BTS (typically NB-AIC).

    Strategy:
      depth-first search;
      at each Y-state, try inclusion-maximal control decisions first
      (larger cardinality first).

    This is a practical implementation of the paper's "find a locally maximal
    live decision string" idea. It is sufficient for Fig. 1 / Example VI.2.
    """
    plant = base.plant

    def dfs_y(raw_y, x, stack):
        key = ("Y", frozenset(raw_y), x)
        if key in stack:
            return None

        for zn in sorted_maximal_z_choices(base, raw_y):
            raw_z = base.z_info(zn)
            ctrl = base.z_ctrl(zn)

            res = dfs_z(raw_z, ctrl, x, stack | {key})
            if res is not None:
                return LiveRun(
                    decisions=[ctrl] + res.decisions,
                    observables=res.observables,
                    y_seq=[frozenset(raw_y)] + res.y_seq,
                    z_seq=[(frozenset(raw_z), frozenset(ctrl))] + res.z_seq,
                    end_x=res.end_x,
                )
        return None

    def dfs_z(raw_z, ctrl, x, stack):
        key = ("Z", frozenset(raw_z), frozenset(ctrl), x)
        if key in stack:
            return None

        if plant.is_marked(x):
            return LiveRun([], [], [], [], x)

        gamma_uo = plant.unobservable_full_gamma(ctrl)

        # first search through unobservable paths
        for e in sorted(gamma_uo):
            x2 = plant.delta(x, e)
            if x2 is None:
                continue
            res = dfs_z(raw_z, ctrl, x2, stack | {key})
            if res is not None:
                return res

        # then try observable exits
        znode = raw_z_to_node(base, raw_z, ctrl)
        if znode is None:
            return None

        for obs_event, yn2 in sorted(base.obs_successors(znode).items(), key=lambda kv: kv[0]):
            x2 = plant.delta(x, obs_event)
            if x2 is None:
                continue

            raw_y2 = base.y_info(yn2)
            res = dfs_y(raw_y2, x2, stack | {key})
            if res is not None:
                return LiveRun(
                    decisions=res.decisions,
                    observables=[obs_event] + res.observables,
                    y_seq=res.y_seq,
                    z_seq=res.z_seq,
                    end_x=res.end_x,
                )

        return None

    return dfs_y(raw_y0, x0, set())


# ============================================================
# 16. Unfold from an entrance Y-copy using a live run
# ============================================================

def augment_with_live_run(U: UBTS, live_run: LiveRun, entrance_y_copy, next_negative_idx=-1):
    """
    Add the transient run described in paper Step 3:

        y_e^k --c1--> z1^(neg1) --sigma1--> y1^(neg2) -- ... --cn--> zn^(neg_last)

    The newly added states are transient (negative indices).
    """
    cur_y = entrance_y_copy
    neg = next_negative_idx

    decisions = live_run.decisions
    observables = live_run.observables
    y_seq = live_run.y_seq
    z_seq = live_run.z_seq

    assert len(decisions) == len(z_seq)
    assert len(observables) == max(0, len(decisions) - 1)

    for i in range(len(decisions)):
        raw_z, ctrl = z_seq[i]

        zcopy = U.add_z_state(raw_z, ctrl, neg)
        if not U.has_ctrl_edge(cur_y, zcopy):
            U.add_yz_edge(cur_y, zcopy)
        neg -= 1

        if i < len(observables):
            obs_event = observables[i]
            raw_y_next = y_seq[i + 1]

            ycopy = U.add_y_state(raw_y_next, neg)
            if not U.has_obs_edge(zcopy, obs_event, ycopy):
                U.add_zy_edge(zcopy, obs_event, ycopy)

            cur_y = ycopy
            neg -= 1

    return neg


# ============================================================
# 17. Extract the memorable supervisor carried by a UBTS
# ============================================================

def extract_memorable_policy(U: UBTS):
    """
    Return a policy keyed by Y-copies:
        policy[y^n] = ctrl_set

    This is the finite-memory supervisor carried by U.
    """
    pol = {}
    for ycopy in U.y_states():
        zs = U.ctrl_successors(ycopy)
        if len(zs) == 1:
            pol[ycopy] = U.z_ctrl(zs[0])
    return pol


def print_memorable_policy(U: UBTS, title="Memorable supervisor policy"):
    pol = extract_memorable_policy(U)
    print(f"\n===== {title} =====")
    for ycopy in sorted(
        pol.keys(),
        key=lambda n: (U.y_idx(n), len(U.y_info(n)), tuple(sorted(U.y_info(n)))),
    ):
        print(f"{ycopy} -> {U.plant.ctrl_to_str(pol[ycopy])}")


# ============================================================
# 18. NB-SOLU-style synthesis on top of the NB-AIC
# ============================================================

def nbsolu_synthesize(
    nb_aic: BTS,
    ctrl_selector=None,
    max_iter=20,
    verbose=True,
):
    """
    Practical NB-SOLU-style synthesis.

    Returns:
        U_final  : final UBTS
        E_final  : merged EBTS
        policy   : memorable supervisor on Y-copies
    """
    U = build_initial_u0(nb_aic, ctrl_selector=ctrl_selector)
    next_neg = -1

    if verbose:
        print_ubts_edges(U, title="Initial U0")

    for it in range(max_iter):
        celc = find_one_celc_and_entrance(U)
        if celc is None:
            E = merge_ubts_to_ebts(U)
            return U, E, extract_memorable_policy(U)

        yentr, xcorr, scc, E, P = celc

        if verbose:
            print(f"\n[NB-SOLU] iteration {it}: found livelock SCC")
            print(f"  entrance Y-copy = {yentr}")
            print(f"  corresponding state = {xcorr}")

        raw_y = U.y_info(yentr)
        live_run = find_greedy_live_run(nb_aic, raw_y, xcorr)
        if live_run is None:
            raise RuntimeError(
                f"Failed to find a live decision string for entrance state {yentr} and plant state {xcorr}."
            )

        if verbose:
            print("  live decision string:")
            for i, c in enumerate(live_run.decisions):
                print(f"    c{i+1} = {nb_aic.plant.ctrl_to_str(c)}")
            if live_run.observables:
                print(f"  observable separators = {live_run.observables}")

        next_neg = augment_with_live_run(U, live_run, yentr, next_negative_idx=next_neg)
        expand_ubts(U, ctrl_selector=ctrl_selector)

        if verbose:
            print_ubts_edges(U, title=f"UBTS after unfolding iteration {it}")

    raise RuntimeError("NB-SOLU iteration cap reached without convergence.")
