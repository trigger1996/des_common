import matplotlib.pyplot as plt

from lib.nfa import DESPlant
from lib.bts import *
from lib.cognitive_nb import *
from plot.aic_plot import draw_fsa, draw_bts
from plot.bcc_cnb_plot import draw_bcc_cnb


# Toggle these if you only want one figure.
SHOW_PLANT = True
SHOW_BTS = True
SHOW_BCC = True


def build_des_plant_2() -> DESPlant:
    """
    A plant reconstructed to match the hand-drawn BCC structure.

    Notes
    -----
    1) The symbol \\varnothing in the figure is the empty control decision,
       NOT a plant event, so it is NOT added as a transition.
    2) The figure is read as:
         - orange dashed boxes = Y information-state singleton groups
         - blue dashed boxes   = Z information-state groups
         - blue edges          = unobservable events
         - black edges         = observable events
    3) If you want to keep your old naming style, simply rename:
         u1 -> b1, u2 -> b2
    """
    G = DESPlant()

    # -------------------------
    # states
    # -------------------------
    for x in range(20):
        G.add_des_state(
            x,
            initial=(x == 0),
            # Keep a conservative marked set first; adjust if needed to match
            # the exact double-circles in the figure.
            marked=(x in {7, 9, 11, 12, 14, 15}),
            legal=(x != 19),
        )

    # -------------------------
    # event partition
    # -------------------------
    G.set_event_partition(
        Ec={"c1", "c2"},
        Euc={"u1", "u2", "o1", "o2"},
        Eo={"o1", "o2"},
        Euo={"u1", "u2", "c1", "c2"},
    )

    # =======================================================
    # top phase: {q0} --{u1,u2}--> {q1,q0,q2} --o1/o2--> ...
    # =======================================================
    G.add_des_transition(0, "u1", 1)
    G.add_des_transition(0, "u2", 2)

    G.add_des_transition(1, "o1", 3)
    G.add_des_transition(1, "o2", 6)
    G.add_des_transition(2, "o1", 4)
    G.add_des_transition(2, "o2", 5)

    # =======================================================
    # left branch
    # Z_{c1}: {q3,q4,q7,q8}
    # Z_{c2}: {q3,q4,q11,q12} with extra u2 back-edge
    # =======================================================
    G.add_des_transition(3, "c1", 7)
    G.add_des_transition(4, "c1", 8)

    G.add_des_transition(3, "c2", 11)
    G.add_des_transition(4, "c2", 12)

    # extra internal unobservable edge shown in the figure
    G.add_des_transition(11, "u2", 4)

    # observable exits to the lower-left Y states
    G.add_des_transition(7, "o1", 16)
    G.add_des_transition(8, "o1", 15)
    G.add_des_transition(11, "o1", 15)
    G.add_des_transition(12, "o1", 16)

    # =======================================================
    # right branch
    # Z_{c1}: {q5,q6,q9,q10}
    # Z_{c2}: {q5,q6,q13,q14} with internal u1/u2 loop
    # =======================================================
    G.add_des_transition(5, "c1", 9)
    G.add_des_transition(6, "c1", 10)

    G.add_des_transition(5, "c2", 13)
    G.add_des_transition(6, "c2", 14)

    # internal unobservable loop shown between q13 and q14
    G.add_des_transition(13, "u1", 14)
    G.add_des_transition(14, "u2", 13)

    # observable exits to the lower-right Y states
    G.add_des_transition(9, "o2", 18)
    G.add_des_transition(10, "o2", 17)
    G.add_des_transition(13, "o2", 17)
    G.add_des_transition(14, "o2", 18)

    # =======================================================
    # bottom phases
    # Z_{empty}: {q15,q16}, then observable return to q3,q4
    # Z_{empty}: {q17,q18}, then observable return to q5,q6
    # =======================================================
    G.add_des_transition(15, "o2", 3)
    G.add_des_transition(16, "o2", 4)

    G.add_des_transition(17, "o1", 5)
    G.add_des_transition(18, "o1", 6)

    G.add_des_transition(12, "c1", 19)
    G.add_des_transition(13, "c1", 19)

    return G


def print_special_case_report(bcc, report=None):
    """Explicitly call and print the special-case related functions."""
    print("\n===== marked Z-states =====")
    if hasattr(bcc, "marked_z_states"):
        marked_z = bcc.marked_z_states()
    elif report is not None:
        marked_z = report.get("marked_z", set())
    else:
        marked_z = set()
    for zn in sorted(marked_z, key=str):
        print(" ", zn)

    print("\n===== special-case Z-states =====")
    if hasattr(bcc, "special_case_z_states"):
        special_z = bcc.special_case_z_states()
    elif report is not None:
        special_z = report.get("special_case_z", set())
    else:
        special_z = set()
    for zn in sorted(special_z, key=str):
        print(" ", zn)


def main():
    g = build_des_plant_2()
    aic = build_aic(g)

    bcc = build_bcc_4_cnb(T=aic, mark_y_micro=True)

    # Prefer the terminology-consistent solver; keep a fallback for older files.
    if hasattr(bcc, "solve_legal_illegal_information_states"):
        report = bcc.solve_legal_illegal_information_states(include_special_case=True)
    else:
        report = bcc.solve_legal_illegal_macro_states()

    if hasattr(bcc, "print_legal_illegal_information_state_report"):
        bcc.print_legal_illegal_information_state_report(report)
    else:
        bcc.print_legal_illegal_macro_report(report)

    # Added call: explicitly evaluate the special case.
    print_special_case_report(bcc, report)

    policy = bcc.extract_maximal_memoryless_policy(report)
    print("\n===== maximal memoryless policy =====")
    for yn in sorted(policy.keys(), key=str):
        print(" ", yn, "->", aic.plant.ctrl_to_str(policy[yn]))

    if SHOW_PLANT:
        draw_fsa(
            g,
            title="Plant G",
            layout="spring",
            figsize=(4.5, 4.5),
            dpi=300,
            node_size=150,
            font_size=5,
            show=False,
        )

    if SHOW_BTS:
        draw_bts(
            aic,
            title="BTS / AIC",
            layout="hybrid_kk",
            figsize=(7.0, 4.8),
            dpi=300,
            node_size=1200,
            font_size=6,
            show=False,
        )

    if SHOW_BCC:
        draw_bcc_cnb(
            bcc,
            layout="sfdp",
            report=report,
            figsize=(6.8, 5.2),
            dpi=300,
            micro_font_size=5,
            macro_font_size=5,
            edge_font_size=5,
            title_font_size=9,
            show_ctrl_edges=False,
            show_edge_labels=False,
            show_legend=False,
            show=False
        )

    plt.show()


if __name__ == "__main__":
    main()
