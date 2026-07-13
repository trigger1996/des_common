from lib.nfa import DESPlant
from lib.bts import BTS

def fmt_state_set(S):
    return "{" + ",".join(map(str, sorted(S))) + "}"


def fmt_y_label(raw_y):
    return "Y\n" + fmt_state_set(raw_y)


def fmt_z_label(raw_z, ctrl_set, plant):
    return "Z\n" + fmt_state_set(raw_z) + "\n" + plant.ctrl_to_str(ctrl_set)

def print_fsa_edges(G: DESPlant, title="FSA edges"):
    print(f"\n===== {title} =====")
    for x, y, d in G.edges(data=True):
        print(f"{x} --{d.get('event')}--> {y}")

def print_bts_edges(T: BTS, title="BTS edges"):
    print(f"\n===== {title} =====")
    for u, v, d in T.edges(data=True):
        if d.get("etype") == "ctrl":
            if T.nodes[u]["kind"] == "Y" and T.nodes[v]["kind"] == "Z":
                print(
                    f"{u}  --ctrl {T.plant.ctrl_to_str(T.z_ctrl(v))}-->  {v}"
                )
            else:
                print(f"{u}  --ctrl-->  {v}")
        elif d.get("etype") == "obs":
            print(f"{u}  --{d.get('event')}-->  {v}")
        else:
            print(f"{u}  --{d}-->  {v}")