import matplotlib.pyplot as plt

from lib.nfa import DESPlant
from lib.bts import *
from lib.cognitive_nb import *
from plot.aic_plot import draw_fsa, draw_bts
from plot.bcc_cnb_plot import draw_bcc_cnb


SHOW_PLANT = True
SHOW_BTS = True
SHOW_IC_BTS = True


def build_grid_environment_dfa() -> DESPlant:
    """DFA from the right side of Grid_Environment_DFA.pdf."""
    G = DESPlant()

    for x in range(20):
        G.add_des_state(
            x,
            initial=(x == 0),
            marked=(x in {3, 5, 6, 18}),
            legal=True,
        )

    G.set_event_partition(
        Ec={"c1", "c2", "o3"},
        Euc={"u1", "u2", "o1", "o2"},
        Eo={"o1", "o2", "o3"},
        Euo={"u1", "u2", "c1", "c2"},
    )

    G.add_des_transition(0, "u1", 1)
    G.add_des_transition(0, "u2", 2)

    G.add_des_transition(1, "o3", 3)
    G.add_des_transition(1, "o2", 5)
    G.add_des_transition(2, "o3", 4)
    G.add_des_transition(2, "o2", 6)

    G.add_des_transition(3, "c1", 7)
    G.add_des_transition(4, "c1", 8)

    G.add_des_transition(5, "c2", 11)
    G.add_des_transition(6, "c2", 12)
    G.add_des_transition(11, "c1", 9)
    G.add_des_transition(12, "c1", 10)
    G.add_des_transition(9, "o2", 13)
    G.add_des_transition(10, "o2", 14)

    G.add_des_transition(7, "c2", 9)
    G.add_des_transition(7, "o1", 17)
    G.add_des_transition(8, "c2", 10)
    G.add_des_transition(8, "o1", 18)
    G.add_des_transition(11, "o1", 15)
    G.add_des_transition(12, "o1", 16)

    G.add_des_transition(15, "c1", 19)

    G.add_des_transition(16, "o1", 0)
    G.add_des_transition(19, "o3", 0)

    G.add_des_transition(17, "o1", 3)
    G.add_des_transition(18, "o1", 4)

    return G


def print_special_case_report(ic_bts, report=None):
    print("\n===== marked Z-states =====")
    marked_z = ic_bts.marked_z_states() if hasattr(ic_bts, "marked_z_states") else report.get("marked_z", set())
    for zn in sorted(marked_z, key=str):
        print(" ", zn)

    print("\n===== special-case Z-states =====")
    special_z = (
        ic_bts.special_case_z_states()
        if hasattr(ic_bts, "special_case_z_states")
        else report.get("special_case_z", set())
    )
    for zn in sorted(special_z, key=str):
        print(" ", zn)


def print_ic_bts_states(ic_bts):
    print("\n===== IC-BTS states =====")
    print("number of microstates =", len(ic_bts.nodes))
    print("number of transitions =", len(ic_bts.edges))

    print("\n--- decision states ---")
    for yn in sorted(ic_bts.base.y_states(), key=str):
        microstates = sorted(
            [n for n in ic_bts.y_microstates() if ic_bts.information_state_of(n) == yn],
            key=lambda n: ic_bts.plant_state_of(n),
        )
        if not microstates:
            continue
        print(" ", yn, "info =", sorted(ic_bts.base.y_info(yn)))
        for n in microstates:
            print(
                "    ",
                n,
                "plant_state =",
                ic_bts.plant_state_of(n),
                "marked =",
                ic_bts.is_marked_micro(n),
            )

    print("\n--- observation states ---")
    for zn in sorted(ic_bts.base.z_states(), key=str):
        microstates = sorted(
            [n for n in ic_bts.z_microstates() if ic_bts.information_state_of(n) == zn],
            key=lambda n: ic_bts.plant_state_of(n),
        )
        if not microstates:
            continue
        print(
            " ",
            zn,
            "info =",
            sorted(ic_bts.base.z_info(zn)),
            "ctrl =",
            ic_bts.plant.ctrl_to_str(ic_bts.base.z_ctrl(zn)),
            "gamma =",
            ic_bts.plant.gamma_to_str(ic_bts.base.z_ctrl(zn)),
        )
        for n in microstates:
            print(
                "    ",
                n,
                "plant_state =",
                ic_bts.plant_state_of(n),
                "marked =",
                ic_bts.is_marked_micro(n),
            )


def print_ic_bts_transitions(ic_bts):
    print("\n===== IC-BTS transitions =====")
    for u, v, data in sorted(ic_bts.edges(data=True), key=lambda e: (str(e[0]), str(e[2]), str(e[1]))):
        kind = data.get("kind")
        if kind == "ctrl":
            ctrl = data.get("ctrl", set())
            label = f"ctrl:{ic_bts.plant.ctrl_to_str(ctrl)} gamma:{ic_bts.plant.gamma_to_str(ctrl)}"
        else:
            label = f"{kind}:{data.get('event')}"
        print(" ", u, f"--{label}-->", v)


def main():
    g = build_grid_environment_dfa()
    aic = build_aic(g)
    ic_bts = build_bcc_4_cnb(T=aic, mark_y_micro=True)

    report = ic_bts.solve_legal_illegal_information_states(include_special_case=True)
    print_ic_bts_states(ic_bts)
    print_ic_bts_transitions(ic_bts)
    ic_bts.print_legal_illegal_information_state_report(report)
    print_special_case_report(ic_bts, report)

    policy = ic_bts.extract_maximal_memoryless_policy(report)
    print("\n===== maximal memoryless policy =====")
    for yn in sorted(policy.keys(), key=str):
        print(" ", yn, "->", aic.plant.ctrl_to_str(policy[yn]))

    if SHOW_PLANT:
        draw_fsa(
            g,
            title="Grid Environment DFA",
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

    if SHOW_IC_BTS:
        draw_bcc_cnb(
            ic_bts,
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
            show=False,
        )

    plt.show()


if __name__ == "__main__":
    main()
