import matplotlib.pyplot as plt

from lib.nfa import DESPlant
from lib.bts import *
from lib.cognitive_nb import *
from plot.bcc_cnb_plot import draw_bcc_cnb

def build_fig1_plant() -> DESPlant:
    G = DESPlant()

    for x in range(16):
        G.add_des_state(
            x,
            initial=(x == 0),
            marked=(x in {7, 10, 12, 14}),
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


def main():
    g = build_fig1_plant()
    aic = build_aic(g)

    ics = build_bcc_4_cnb(T=aic, mark_y_micro=False)

    report = ics.solve_legal_illegal_macro_states()
    ics.print_legal_illegal_macro_report(report)

    policy = ics.extract_maximal_memoryless_policy(report)
    print("\n===== maximal memoryless policy =====")
    for yn in sorted(policy.keys(), key=str):
        print(" ", yn, "->", aic.plant.ctrl_to_str(policy[yn]))

    draw_bcc_cnb(
        ics,
        layout="sfdp",
        report=report,
        #show_ctrl_edges=False,
    )

    plt.show()

if __name__ == "__main__":
    main()
