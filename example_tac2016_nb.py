import networkx as nx
from collections import deque
from typing import Dict, FrozenSet, Iterable, Optional, Set

from lib.nfa import DESPlant
from lib.bts import *

from util.des_print import print_fsa_edges, print_bts_edges
from plot.aic_plot import draw_fsa, draw_bts, draw_ubts

# ============================================================
# 6. Fig. 1 of the 2016 paper
# ============================================================

def build_fig1_plant() -> DESPlant:
    """
    Corrected Fig. 1 model:
      - marked states are {8,10,12,14}
      - state 15 is illegal and NOT marked
    """
    G = DESPlant()

    for x in range(16):
        G.add_des_state(
            x,
            initial=(x == 0),
            marked=(x in {8, 10, 12, 14}),
            legal=(x != 15),
        )

    G.set_event_partition(
        Ec={"c1", "c2"},
        Euc={"b1", "b2", "o1", "o2"},
        Eo={"o1", "o2"},
        Euo={"b1", "b2", "c1", "c2"},
    )

    G.add_des_transition(0, "b1", 1)
    G.add_des_transition(0, "b2", 2)

    G.add_des_transition(1, "o1", 3)
    G.add_des_transition(1, "o2", 5)
    G.add_des_transition(2, "o1", 4)
    G.add_des_transition(2, "o2", 6)

    G.add_des_transition(3, "c1", 7)
    G.add_des_transition(3, "c2", 8)
    G.add_des_transition(4, "c1", 10)
    G.add_des_transition(4, "c2", 9)

    G.add_des_transition(5, "c1", 12)
    G.add_des_transition(5, "c2", 11)
    G.add_des_transition(6, "c1", 13)
    G.add_des_transition(6, "c2", 14)

    G.add_des_transition(7, "o1", 1)
    G.add_des_transition(8, "o1", 1)
    G.add_des_transition(9, "o1", 2)
    G.add_des_transition(10, "o1", 2)

    G.add_des_transition(11, "o2", 1)
    G.add_des_transition(12, "o2", 1)
    G.add_des_transition(13, "o2", 2)
    G.add_des_transition(14, "o2", 2)

    G.add_des_transition(8, "c1", 15)
    G.add_des_transition(10, "c2", 15)
    G.add_des_transition(12, "c2", 15)
    G.add_des_transition(14, "c1", 15)

    return G


# ============================================================
# 7. Fig. 1 paper-style memoryless U0 policy
# ============================================================

def find_y_node_by_info(T: BTS, raw_info: Iterable[int]):
    raw_info = frozenset(raw_info)
    for yn in T.y_states():
        if T.y_info(yn) == raw_info:
            return yn
    return None


def fig1_u0_policy(nb_aic: BTS):
    """
    Paper-style U0:
      {0}   -> {}
      {1,2} -> {}
      {3,4} -> {c2}
      {5,6} -> {c1}

    NOTE:
      The stored control set is only the enabled controllable set.
      The printed label corresponds to Gamma = Euc union C.
    """
    required_sets = [{0}, {1, 2}, {3, 4}, {5, 6}]
    ymap = {}

    for S in required_sets:
        yn = find_y_node_by_info(nb_aic, S)
        if yn is None:
            raise ValueError(f"NB-AIC does not contain Y-state {S}")
        ymap[frozenset(S)] = yn

    def choose_ctrl(yn, ctrl_set):
        ctrl_set = frozenset(ctrl_set)
        for zn in nb_aic.ctrl_successors(yn):
            if nb_aic.z_ctrl(zn) == ctrl_set:
                return ctrl_set
        raise ValueError(
            f"cannot find control set {set(ctrl_set)} at Y-state {set(nb_aic.y_info(yn))}"
        )

    pol = {}
    pol[ymap[frozenset({0})]] = choose_ctrl(ymap[frozenset({0})], set())
    pol[ymap[frozenset({1, 2})]] = choose_ctrl(ymap[frozenset({1, 2})], set())
    pol[ymap[frozenset({3, 4})]] = choose_ctrl(ymap[frozenset({3, 4})], {"c2"})
    pol[ymap[frozenset({5, 6})]] = choose_ctrl(ymap[frozenset({5, 6})], {"c1"})
    return pol


# ============================================================
# 8. Small demo
# ============================================================

def demo_fig1():
    G = build_fig1_plant()
    AIC = build_aic(G)
    NBAIC = build_nb_aic(G)

    # build paper-style U0
    U0 = build_initial_u0(NBAIC, ctrl_selector=fig1_u0_ctrl_selector)       # to obtain UBTS 在 Fig.1 这个例子里，除了 Fig.3 里展示的U0之外，还有别的控制选择。例如在 {5,6}^0 处也可以选 {c2,uc}，而且那样会直接得到一个 non-blocking 的 IS-based solution，于是根本不需要再做后面的 unfolding。
    # U0 = build_initial_u0(NBAIC, ctrl_selector=None)

    print_ubts_edges(U0, title="Fig.1 U0 (paper-style initial UBTS)")

    celc = find_one_celc_and_entrance(U0)
    if celc is None:
        print("No livelock found in U0.")
        return

    yentr, xcorr, scc, E0, P0 = celc
    print("\nDetected entrance Y-copy in U0:")
    print("  entrance =", yentr)
    print("  corresponding state =", xcorr)

    live_run = find_greedy_live_run(NBAIC, U0.y_info(yentr), xcorr)
    print("\nChosen live run:")
    print("  decisions =", [G.ctrl_to_str(c) for c in live_run.decisions])
    print("  observables =", live_run.observables)

    U1 = U0.copy_ubts(name="U1")
    next_neg = augment_with_live_run(U1, live_run, yentr, next_negative_idx=-1)
    expand_ubts(U1, ctrl_selector=fig1_u0_ctrl_selector)

    U_final, E_final, policy = nbsolu_synthesize(
        NBAIC,
        ctrl_selector=fig1_u0_ctrl_selector,  # 先复现论文 Fig.3 的 U0
        max_iter=10,
        verbose=True,
    )

    print_fsa_edges(G, title="Fig.1 plant edges")
    print_ubts_edges(U1, title="Fig.1 U1 after one unfolding + EXPAND")

    E1 = merge_ubts_to_ebts(U1)
    P1 = build_product_graph_from_ebts(E1)
    scc1 = find_closed_unmarked_scc(P1)

    print("\nLivelock after one unfolding:")
    print("  remaining closed unmarked SCC =", scc1)

    print_memorable_policy(U1, title="Supervisor carried by U1")

    print_bts_edges(AIC, title="AIC edges")
    print_bts_edges(NBAIC, title="NB-AIC edges")

    draw_bts(NBAIC, filename="fig1_nbaic.png", title="NB-AIC")
    draw_ubts(U_final, filename="fig1_ubts_final.png", title="Final UBTS")

if __name__ == "__main__":
    demo_fig1()

