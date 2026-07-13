import math
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
import networkx as nx


# ============================================================
# Label helpers
# ============================================================

def fmt_set(S):
    return "{" + ",".join(map(str, sorted(S))) + "}"


def fmt_macro_y_label(bcc, yn):
    return "Y\n" + fmt_set(bcc.base.y_info(yn))


def fmt_macro_z_label(bcc, zn):
    return "Z\n" + fmt_set(bcc.base.z_info(zn)) + "\n" + bcc.plant.ctrl_to_str(bcc.base.z_ctrl(zn))


# ============================================================
# Layout helpers
# ============================================================
def get_bcc_macro_layout(
    bcc,
    layout="hybrid_kk",
    scale=5.0,
    yz_sep=1.8,
    x_stretch=1.0,
    y_stretch=1.0,
    spring_k=1.8,
    spring_iter=400,
):
    """
    Compute a macro-layout on the base BTS, then use it as the center of each
    macro group in the BCC figure.

    Parameters
    ----------
    layout:
        "hybrid_kk"      : default, kk then split Y/Z horizontally
        "hybrid_spring"  : spring then split Y/Z horizontally
        "kk"             : pure kamada-kawai
        "spring"         : pure spring
        "circular"       : circular layout
        "shell"          : shell layout
        "spectral"       : spectral layout
        "multipartite"   : Y and Z forced into two columns
        "dot"            : graphviz dot (if available)
        "neato"          : graphviz neato (if available)
        "sfdp"           : graphviz sfdp (if available)

    scale:
        global layout scale

    yz_sep:
        extra horizontal separation between Y and Z groups
        (only used in hybrid/multipartite)

    x_stretch, y_stretch:
        additional anisotropic scaling

    spring_k, spring_iter:
        spring layout parameters
    """
    T = bcc.base
    Y_nodes = list(T.y_states())
    Z_nodes = list(T.z_states())

    if len(T.nodes()) == 0:
        return {}

    H = T.to_undirected()

    # ----------------------------------------------------
    # graphviz layouts if available
    # ----------------------------------------------------
    if layout in {"dot", "neato", "sfdp"}:
        try:
            from networkx.drawing.nx_agraph import graphviz_layout
            base = graphviz_layout(H, prog=layout)
        except Exception:
            try:
                from networkx.drawing.nx_pydot import graphviz_layout
                base = graphviz_layout(H, prog=layout)
            except Exception:
                base = None

        if base is not None:
            pos = {}
            for n, (x, y) in base.items():
                pos[n] = (scale * x_stretch * x, scale * y_stretch * y)
            return pos

    # ----------------------------------------------------
    # multipartite: strongest Y/Z separation
    # ----------------------------------------------------
    if layout == "multipartite":
        G2 = T.copy()
        for n in Y_nodes:
            G2.nodes[n]["layer"] = 0
        for n in Z_nodes:
            G2.nodes[n]["layer"] = 1

        base = nx.multipartite_layout(G2, subset_key="layer", align="vertical")
        pos = {}
        for n, (x, y) in base.items():
            if n in Y_nodes:
                xx = (x - yz_sep)
            else:
                xx = (x + yz_sep)
            pos[n] = (scale * x_stretch * xx, scale * y_stretch * y)
        return pos

    # ----------------------------------------------------
    # pure layouts
    # ----------------------------------------------------
    if layout == "spring":
        base = nx.spring_layout(H, seed=7, k=spring_k, iterations=spring_iter)
        return {
            n: (scale * x_stretch * x, scale * y_stretch * y)
            for n, (x, y) in base.items()
        }

    if layout == "kk":
        base = nx.kamada_kawai_layout(H)
        return {
            n: (scale * x_stretch * x, scale * y_stretch * y)
            for n, (x, y) in base.items()
        }

    if layout == "circular":
        base = nx.circular_layout(H)
        return {
            n: (scale * x_stretch * x, scale * y_stretch * y)
            for n, (x, y) in base.items()
        }

    if layout == "shell":
        base = nx.shell_layout(H)
        return {
            n: (scale * x_stretch * x, scale * y_stretch * y)
            for n, (x, y) in base.items()
        }

    if layout == "spectral":
        base = nx.spectral_layout(H)
        return {
            n: (scale * x_stretch * x, scale * y_stretch * y)
            for n, (x, y) in base.items()
        }

    # ----------------------------------------------------
    # hybrid layouts: relax first, then separate Y/Z
    # ----------------------------------------------------
    if layout == "hybrid_spring":
        base = nx.spring_layout(H, seed=7, k=spring_k, iterations=spring_iter)
    else:  # default hybrid_kk
        base = nx.kamada_kawai_layout(H)

    pos = {}
    for n, (x, y) in base.items():
        if n in Y_nodes:
            xx = x - yz_sep
        else:
            xx = x + yz_sep
        pos[n] = (
            scale * x_stretch * xx,
            scale * y_stretch * y,
        )

    return pos


def stack_micro_positions(center, n, vertical_gap=0.75):
    """
    Stack n microstates around a macro center vertically.
    """
    cx, cy = center
    if n == 1:
        return [(cx, cy)]

    total_h = vertical_gap * (n - 1)
    y0 = cy + total_h / 2.0
    return [(cx, y0 - i * vertical_gap) for i in range(n)]


def bbox_from_points(points, pad_x=0.65, pad_y=0.45):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0 = min(xs) - pad_x
    x1 = max(xs) + pad_x
    y0 = min(ys) - pad_y
    y1 = max(ys) + pad_y
    return x0, y0, (x1 - x0), (y1 - y0)


# ============================================================
# Drawing primitives
# ============================================================

def draw_group_box(ax, bbox, edgecolor="black", facecolor="white", linewidth=1.8, alpha=0.95):
    x, y, w, h = bbox
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
        alpha=alpha,
        zorder=0,
    )
    ax.add_patch(patch)


def draw_micro_node(ax, pos, kind="Y", marked=False, size=0.22, text="", font_size=10):
    x, y = pos

    if kind == "Y":
        face = "#DFF0FF" if not marked else "#CFEFD6"
        patch = Circle((x, y), radius=size, facecolor=face, edgecolor="black", linewidth=1.3, zorder=3)
    else:
        face = "#FFE8C7" if not marked else "#CFEFD6"
        patch = Rectangle((x - size, y - size), 2 * size, 2 * size,
                          facecolor=face, edgecolor="black", linewidth=1.3, zorder=3)

    ax.add_patch(patch)

    txt = ax.text(
        x, y, text,
        ha="center", va="center",
        fontsize=font_size,
        fontfamily="DejaVu Sans",
        zorder=4,
    )
    txt.set_path_effects([pe.withStroke(linewidth=0.8, foreground="white")])


def draw_directed_edge(
    ax,
    p1,
    p2,
    *,
    color="black",
    lw=1.3,
    style="-",
    alpha=0.9,
    rad=0.0,
    label=None,
    label_fontsize=8,
    label_offset=(0.0, 0.08),
    shrink=8,
):
    x1, y1 = p1
    x2, y2 = p2

    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="->",
            linewidth=lw,
            linestyle=style,
            color=color,
            alpha=alpha,
            shrinkA=shrink,
            shrinkB=shrink,
            connectionstyle=f"arc3,rad={rad}",
        ),
        zorder=2,
    )

    if label is not None:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        txt = ax.text(
            mx, my, label,
            fontsize=label_fontsize,
            fontfamily="DejaVu Sans",
            ha="center", va="center",
            bbox=dict(facecolor="white", edgecolor="none", pad=0.08, alpha=0.88),
            zorder=5,
        )
        txt.set_path_effects([pe.withStroke(linewidth=0.8, foreground="white")])

# ============================================================
# Main BCC-CNB drawing function
# ============================================================

def draw_bcc_cnb(
    bcc,
    report=None,
    filename=None,
    title="BCC-CNB",
    layout="hybrid_kk",
    figsize=(12.8, 7.2),     # 适合 1920×1080
    dpi=360,
    micro_font_size=4.5,     # 略小
    macro_font_size=4.8,     # 略小
    edge_font_size=4.5,
    legend_font_size=4.5,
    title_font_size=8,
    micro_node_size=0.64,    # 新增：micro 圆/方块更小
    group_pad_x=0.75,        # 新增：圆角框横向 padding 更小
    group_pad_y=0.30,        # 新增：圆角框纵向 padding 更小
    vertical_gap=0.95,       # 新增：同一信息状态内部 micro 间隔更大
    layout_scale=7.5,        # 新增：不同信息状态之间拉开
    yz_sep=2.7,              # 新增：Y/Z 两列拉开
    x_stretch=1.25,          # 新增：横向再拉开
    y_stretch=1.15,          # 新增：纵向再拉开
    show_ctrl_edges=True,
    show_uo_edges=True,
    show_obs_edges=True,
    show_edge_labels=True,
    show_legend=False,
    show=True,
):
    """
    Draw the BCC with CNB-related highlighting.

    Color / semantbcc:
      - Y macro group: blue-ish
      - Z macro group: orange-ish
      - marked microstate: green fill
      - local legal Z macro group: dark green border
      - accepting Z macro group: stronger green border
      - illegal macro states (if report given): crimson border
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_title(title, fontsize=title_font_size, pad=2)

    T = bcc.base
    macro_pos = get_bcc_macro_layout(
        bcc,
        layout=layout,
        scale=layout_scale,
        yz_sep=yz_sep,
        x_stretch=x_stretch,
        y_stretch=y_stretch,
    )

    # -------------------------
    # status sets from report
    # -------------------------
    if report is None:
        try:
            report = bcc.solve_legal_illegal_macro_states()
        except Exception:
            report = None

    legal_y = set(report["legal_y"]) if report is not None else set()
    legal_z = set(report["legal_z"]) if report is not None else set()
    illegal_y = set(report["illegal_y"]) if report is not None else set()
    illegal_z = set(report["illegal_z"]) if report is not None else set()

    local_legal_z = set()
    try:
        local_legal_z = set(bcc.local_legal_z_states())
    except Exception:
        pass

    accepting_z = set()
    try:
        accepting_z = set(bcc.accepting_z_states())
    except Exception:
        pass

    # -------------------------
    # group microstates by macro
    # -------------------------
    macro_to_micro = defaultdict(list)
    for n in bcc.nodes:
        macro_to_micro[bcc.macro_of(n)].append(n)

    # -------------------------
    # assign micro positions inside each macro group
    # -------------------------
    micro_pos = {}
    group_bbox = {}

    for macro, micro_nodes in macro_to_micro.items():
        center = macro_pos.get(macro, (0.0, 0.0))
        micro_nodes_sorted = sorted(micro_nodes, key=lambda n: bcc.plant_state_of(n))
        pts = stack_micro_positions(
            center,
            len(micro_nodes_sorted),
            vertical_gap=vertical_gap,
        )

        for n, p in zip(micro_nodes_sorted, pts):
            micro_pos[n] = p

        group_bbox[macro] = bbox_from_points(
            pts,
            pad_x=group_pad_x,
            pad_y=group_pad_y,
        )

    # -------------------------
    # draw macro group boxes
    # -------------------------
    for macro, bbox in group_bbox.items():
        kind = "Y" if macro[0] == "Y" else "Z"

        if kind == "Y":
            face = "#F4F9FF"
            edge = "#2C4A73"
            lw = 1.8

            if report is not None:
                if macro in illegal_y:
                    edge = "crimson"
                    lw = 2.0
                elif macro in legal_y:
                    edge = "#2C4A73"
                    lw = 2.0
        else:
            face = "#FFF7EC"
            edge = "#8A5A00"
            lw = 1.8

            if macro in local_legal_z:
                edge = "forestgreen"
                lw = 2.2

            if macro in accepting_z:
                edge = "darkgreen"
                lw = 2.8

            if report is not None and macro in illegal_z:
                edge = "crimson"
                lw = 2.2

        draw_group_box(ax, bbox, edgecolor=edge, facecolor=face, linewidth=lw, alpha=0.98)

        # macro label
        x, y, w, h = bbox
        if kind == "Y":
            label = fmt_macro_y_label(bcc, macro)
        else:
            label = fmt_macro_z_label(bcc, macro)

        txt = ax.text(
            x + w / 2,
            y + h + 0.28,
            label,
            ha="center",
            va="bottom",
            fontsize=macro_font_size,
            fontfamily="DejaVu Sans",
            zorder=6,
        )
        txt.set_path_effects([pe.withStroke(linewidth=1.0, foreground="white")])

    # -------------------------
    # draw micro nodes
    # -------------------------
    for n in sorted(bcc.nodes, key=str):
        pos = micro_pos[n]
        kind = n[0]
        x = bcc.plant_state_of(n)
        draw_micro_node(
            ax,
            pos,
            kind=kind,
            marked=bcc.is_marked_micro(n),
            size=micro_node_size,
            text=str(x),
            font_size=micro_font_size,
        )

    # -------------------------
    # draw edges
    # -------------------------
    for u, v, d in bcc.edges(data=True):
        if u not in micro_pos or v not in micro_pos:
            continue

        p1 = micro_pos[u]
        p2 = micro_pos[v]
        kind = d.get("kind")

        if kind == "ctrl" and show_ctrl_edges:
            draw_directed_edge(
                ax, p1, p2,
                color="gray",
                lw=0.8,
                style="-",
                alpha=0.65,
                rad=0.0,
                label=None,
                shrink=5,
            )

        elif kind == "uo" and show_uo_edges:
            lab = d.get("event") if show_edge_labels else None
            draw_directed_edge(
                ax, p1, p2,
                color="#C47F00",
                lw=1.3,
                style="-",
                alpha=0.9,
                rad=0.12 if u != v else 0.28,
                label=lab,
                label_fontsize=edge_font_size,
                label_offset=(0.0, 0.10),
                shrink=5,
            )

        elif kind == "obs" and show_obs_edges:
            lab = d.get("event") if show_edge_labels else None
            draw_directed_edge(
                ax, p1, p2,
                color="#0066CC",
                lw=1.2,
                style="--",
                alpha=0.9,
                rad=-0.08,
                label=lab,
                label_fontsize=edge_font_size,
                label_offset=(0.0, 0.12),
                shrink=5,
            )

    # -------------------------
    # initial arrow
    # -------------------------
    init_micro = sorted(list(bcc.initial_microstates()), key=str)
    if init_micro:
        n0 = init_micro[0]
        x0, y0 = micro_pos[n0]
        ax.annotate(
            "",
            xy=(x0 - 0.15, y0),
            xytext=(x0 - 1.2, y0),
            arrowprops=dict(arrowstyle="->", lw=1.8),
            zorder=7,
        )

    # -------------------------
    # set visible limits explicitly
    # -------------------------
    if micro_pos:
        xs = [p[0] for p in micro_pos.values()]
        ys = [p[1] for p in micro_pos.values()]

        margin_x = 2.0
        margin_y = 2.0

        ax.set_xlim(min(xs) - margin_x, max(xs) + margin_x)
        ax.set_ylim(min(ys) - margin_y, max(ys) + margin_y)
        ax.set_aspect("equal", adjustable="box")

    # -------------------------
    # legend
    # -------------------------
    if show_legend:
        legend_text = (
            "Y-micro: circle\n"
            "Z-micro: square\n"
            "green fill: marked\n"
            "gray: ctrl\n"
            "orange: unobs.\n"
            "blue dashed: obs.\n"
            "green box: potential feasible Z\n"
            "red box: pruned"
        )
        ax.text(
            0.015, 0.985, legend_text,
            transform=ax.transAxes,
            fontsize=legend_font_size,
            va="top",
            bbox=dict(facecolor="white", edgecolor="gray", alpha=0.90, pad=1.5),
            zorder=20,
        )

    ax.axis("off")
    fig.tight_layout()

    if filename:
        plt.savefig(filename, bbox_inches="tight")
    if show:
        plt.show()