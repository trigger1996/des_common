import networkx as nx
from collections import deque, defaultdict
from itertools import combinations
from typing import Dict, FrozenSet, Iterable, Optional, Set

RawInfo = FrozenSet[int]
CtrlSet = FrozenSet[str]
# ============================================================
# 0. Core conventions
# ------------------------------------------------------------
# Raw information state:
#     frozenset({plant_state_1, plant_state_2, ...})
#
# BTS graph node ids:
#     Y-node = ("Y", raw_info_state)
#     Z-node = ("Z", raw_info_state_after_UR, enabled_controllable_set)
#
# IMPORTANT:
#     - UR / UR_plus / Next_e always operate on RAW information states,
#       never on graph node ids.
#     - A Z-state stores only the enabled controllable events C(z) subseteq Ec.
#       The full admissible event set is derived as:
#           Gamma(z) = Euc union C(z)
# ============================================================


# ============================================================
# 1. Plant model (event-observation DES)
# ============================================================

class DESPlant(nx.MultiDiGraph):
    def __init__(self):
        super().__init__()
        self.x0: Optional[int] = None

        self.Ec: Set[str] = set()
        self.Euc: Set[str] = set()
        self.Eo: Set[str] = set()
        self.Euo: Set[str] = set()

        self._delta = {}   # (x, e) -> y

    # -------------------------
    # State / event definition
    # -------------------------
    def add_des_state(self, x: int, *, initial=False, marked=False, legal=True):
        self.add_node(x, marked=bool(marked), legal=bool(legal))
        if initial:
            self.x0 = x

    def set_event_partition(
        self,
        *,
        Ec: Iterable[str],
        Euc: Iterable[str],
        Eo: Iterable[str],
        Euo: Iterable[str],
    ):
        self.Ec = set(Ec)
        self.Euc = set(Euc)
        self.Eo = set(Eo)
        self.Euo = set(Euo)

        assert self.Ec.isdisjoint(self.Euc)
        assert self.Eo.isdisjoint(self.Euo)

    def add_des_transition(self, x: int, e: str, y: int):
        self._delta[(x, e)] = y
        self.add_edge(x, y, event=e)

    # -------------------------
    # Basic query
    # -------------------------
    def delta(self, x: int, e: str) -> Optional[int]:
        return self._delta.get((x, e), None)

    def is_marked(self, x: int) -> bool:
        return bool(self.nodes[x].get("marked", False))

    def is_legal(self, x: int) -> bool:
        return bool(self.nodes[x].get("legal", False))

    # -------------------------
    # Admissible decisions
    # -------------------------
    def all_enabled_controllable_sets(self):
        """
        Enumerate all C subseteq Ec.
        We store only C in Z-states.
        The full admissible event set is Gamma(C) = Euc union C.
        """
        ec_list = sorted(self.Ec)
        out = []
        for r in range(len(ec_list) + 1):
            for comb in combinations(ec_list, r):
                out.append(frozenset(comb))
        return out

    def observable_full_gamma(self, ctrl_set: Iterable[str]) -> Set[str]:
        """
        Gamma(C) = Euc union C
        """
        C = set(ctrl_set)
        return (self.Euc & self.Eo) | (C & self.Eo)

    def unobservable_full_gamma(self, ctrl_set: Iterable[str]) -> Set[str]:
        """
        Gamma(C) = Euc union C
        """
        C = set(ctrl_set)
        return (self.Euc & self.Euo) | (C & self.Euo)

    def ctrl_to_str(self, ctrl_set: Iterable[str]) -> str:
        ctrl_set = set(ctrl_set)
        if not ctrl_set:
            return "{uc}"
        return "{" + ",".join(sorted(ctrl_set) + ["uc"]) + "}"

    # -------------------------
    # Paper operators on RAW information states
    # -------------------------
    def UR(self, info_state: Iterable[int], ctrl_set: Iterable[str]) -> RawInfo:
        """
        UR_{Gamma(C)}(I)
        Unobservable reach under Gamma(C) = Euc union C

        NOTE:
            info_state is a RAW information state, not a graph node id.
        """
        gamma = self.unobservable_full_gamma(ctrl_set) | self.observable_full_gamma(ctrl_set)   # TODO
        allowed_uo = gamma & self.Euo

        q = deque(info_state)
        seen = set(info_state)

        while q:
            x = q.popleft()
            for e in allowed_uo:
                y = self.delta(x, e)
                if y is not None and y not in seen:
                    seen.add(y)
                    q.append(y)

        return frozenset(seen)

    def UR_plus(self, info_state: Iterable[int], ctrl_set: Iterable[str]) -> RawInfo:
        """
        UR^+_{Gamma(C)}(I)
        """
        base = set(self.UR(info_state, ctrl_set))
        obs_part = self.observable_full_gamma(ctrl_set)
        out = set(base)
        # observable step
        obs_succ = set()
        for x in base:
            for e in obs_part:
                y = self.delta(x, e)
                if y is not None:
                    obs_succ.add(y)
        # unobservable closure of observable successors
        for y in obs_succ:
            out.update(self.UR([y], ctrl_set))
        out.update(obs_succ)
        return frozenset(out)

    def next_y(self, z_info_state: Iterable[int], obs_event: str) -> RawInfo:
        """
        Next_{obs_event}(I)
        """
        out = set()
        for x in z_info_state:
            y = self.delta(x, obs_event)
            if y is not None:
                out.add(y)
        return frozenset(out)

    def observable_successors_from_z(self, z_info_state: Iterable[int], ctrl_set: Iterable[str]):
        """
        Return:
            { obs_event : next_raw_y_info_state }
        """
        gamma = self.observable_full_gamma(ctrl_set)
        out = {}
        for e in sorted(gamma & self.Eo):
            y_next = self.next_y(z_info_state, e)
            if y_next:
                out[e] = y_next
        return out

    def is_irredundant_ctrl(self, raw_y_info: Iterable[int], ctrl_set: Iterable[str]) -> bool:
        """
        We only prune redundant *controllable* additions.

        ctrl_set is the set C ⊆ Ec that we actively choose to enable.
        If some c in C can never be executed anywhere in UR(y, C),
        then C is redundant at y and should be removed.
        """
        ctrl_set = set(ctrl_set)

        # the empty controllable choice {} is always kept
        if not ctrl_set:
            return True

        reach = self.UR(raw_y_info, ctrl_set)

        # every chosen controllable event must be executable somewhere in the UR
        for c in ctrl_set:
            if not any(self.delta(x, c) is not None for x in reach):
                return False

        return True
