from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
import networkx as nx

from lib.nfa import DESPlant
from lib.bts import BTS, UBTS
from util.des_print import fmt_y_label, fmt_z_label, fmt_state_set


# ============================================================
# Generic label helpers
# ============================================================

def _fmt_set(S):
    return "{" + ",".join(map(str, sorted(S))) + "}"


def _info_state_of(bcc, node):
    """Return the BTS information-state represented by a BCC microstate."""
    if hasattr(bcc, "information_state_of"):
        return bcc.information_state_of(node)
    legacy_accessor = getattr(bcc, "ma" + "cro_of", None)
    if legacy_accessor is not None:
        return legacy_accessor(node)
    return node[1]


def _info_kind(info_state):
    return info_state[0] if isinstance(info_state, tuple) and info_state else None


def _fmt_info_y_label(bcc, yn):
    return "Y\n" + _fmt_set(bcc.base.y_info(yn))


def _fmt_info_z_label(bcc, zn):
    return "Z\n" + _fmt_set(bcc.base.z_info(zn)) + "\n" + bcc.plant.ctrl_to_str(bcc.base.z_ctrl(zn))


def _report_set(report, key, default=None):
    if report is None:
        return set() if default is None else set(default)
    return set(report.get(key, set() if default is None else default))


# ============================================================
# FSA/BTS layout helpers
# ============================================================

def get_fsa_layout(G, layout="shell", scale=3.0):
    """
    layout options:
        - "dot"    : graphviz dot
        - "neato"  : graphviz neato
        - "sfdp"   : graphviz sfdp
        - "spring" : networkx spring layout
        - "kk"     : kamada-kawai
        - "shell"  : shell layout
    """
    if layout in {"dot", "neato", "sfdp"}:
        try:
            from networkx.drawing.nx_agraph import graphviz_layout
            pos = graphviz_layout(G, prog=layout)
            return {k: (scale * v[0], scale * v[1]) for k, v in pos.items()}
        except Exception:
            try:
                from networkx.drawing.nx_pydot import graphviz_layout
                pos = graphviz_layout(G, prog=layout)
                return {k: (scale * v[0], scale * v[1]) for k, v in pos.items()}
            except Exception:
                pass

    if layout == "spring":
        pos = nx.spring_layout(G, seed=7, k=1.8, iterations=300)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    else:
        pos = nx.kamada_kawai_layout(G)

    return {k: (scale * v[0], scale * v[1]) for k, v in pos.items()}


def get_bts_layout(T: BTS, layout="kk", scale=4.0, yz_separation=2.5):
    """
    layout options:
        - "spring"
        - "kk"
        - "hybrid_spring"
        - "hybrid_kk"
        - "multipartite"
        - "dot" / "neato" / "sfdp" when graphviz is available
    """
    Y_nodes = list(T.y_states())
    Z_nodes = list(T.z_states())

    if len(T.nodes()) == 0:
        return {}

    if layout in {"dot", "neato", "sfdp"}:
        H = T.to_undirected()
        try:
            from networkx.drawing.nx_agraph import graphviz_layout
            base = graphviz_layout(H, prog=layout)
            return {k: (scale * v[0], scale * v[1]) for k, v in base.items()}
        except Exception:
            try:
                from networkx.drawing.nx_pydot import graphviz_layout
                base = graphviz_layout(H, prog=layout)
                return {k: (scale * v[0], scale * v[1]) for k, v in base.items()}
            except Exception:
                pass

    if layout == "multipartite":
        H = T.copy()
        for n in Y_nodes:
            H.nodes[n]["layer"] = 0
        for n in Z_nodes:
            H.nodes[n]["layer"] = 1
        return nx.multipartite_layout(H, subset_key="layer", align="vertical", scale=scale)

    H = T.to_undirected()

    if layout == "spring":
        pos = nx.spring_layout(H, seed=7, k=1.6, iterations=300)
        return {k: (scale * v[0], scale * v[1]) for k, v in pos.items()}

    if layout == "kk":
        pos = nx.kamada_kawai_layout(H)
        return {k: (scale * v[0], scale * v[1]) for k, v in pos.items()}

    if layout == "hybrid_spring":
        base = nx.spring_layout(H, seed=7, k=1.6, iterations=300)
    else:
        base = nx.kamada_kawai_layout(H)

    pos = {}
    for n, (x, y) in base.items():
        if n in Y_nodes:
            pos[n] = (scale * (x - yz_separation), scale * y)
        else:
            pos[n] = (scale * (x + yz_separation), scale * y)
    return pos


# ============================================================
# BCC layout helpers
# ============================================================

def get_bcc_information_layout(
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
    Compute a layout on the BTS information-state graph, and use it as the
    center layout for the corresponding BCC microstate groups.
    """
    T = bcc.base
    Y_nodes = list(T.y_states())
    Z_nodes = list(T.z_states())

    if len(T.nodes()) == 0:
        return {}

    H = T.to_undirected()

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
            return {
                n: (scale * x_stretch * x, scale * y_stretch * y)
                for n, (x, y) in base.items()
            }

    if layout == "multipartite":
        G2 = T.copy()
        for n in Y_nodes:
            G2.nodes[n]["layer"] = 0
        for n in Z_nodes:
            G2.nodes[n]["layer"] = 1

        base = nx.multipartite_layout(G2, subset_key="layer", align="vertical")
        pos = {}
        for n, (x, y) in base.items():
            xx = x - yz_sep if n in Y_nodes else x + yz_sep
            pos[n] = (scale * x_stretch * xx, scale * y_stretch * y)
        return pos

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

    if layout == "hybrid_spring":
        base = nx.spring_layout(H, seed=7, k=spring_k, iterations=spring_iter)
    else:
        base = nx.kamada_kawai_layout(H)

    pos = {}
    for n, (x, y) in base.items():
        xx = x - yz_sep if n in Y_nodes else x + yz_sep
        pos[n] = (scale * x_stretch * xx, scale * y_stretch * y)
    return pos


def stack_micro_positions(center, n, vertical_gap=0.75):
    """Stack n microstates vertically around a group center."""
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
        patch = Circle((x, y), radius=size, facecolor=face, edgecolor="black", linewidth=1.0, zorder=3)
    else:
        face = "#FFE8C7" if not marked else "#CFEFD6"
        patch = Rectangle(
            (x - size, y - size), 2 * size, 2 * size,
            facecolor=face, edgecolor="black", linewidth=1.0, zorder=3,
        )

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
# Plant / BTS drawing functions
# ============================================================

def draw_fsa(
    G: DESPlant,
    filename=None,
    title="FSA",
    layout="shell",
    figsize=(10, 7),
    dpi=220,
    node_size=1200,
    font_size=11,
    show=True,
):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_title(title, fontsize=max(font_size + 3, 8))

    pos = get_fsa_layout(G, layout=layout)

    normal_nodes = [x for x in G.nodes if G.is_legal(x)]
    illegal_nodes = [x for x in G.nodes if not G.is_legal(x)]
    marked_nodes = [x for x in G.nodes if G.is_marked(x)]

    nx.draw_networkx_nodes(
        G, pos, nodelist=normal_nodes,
        node_size=node_size, linewidths=1.8,
        edgecolors="black", node_color="white", ax=ax,
    )

    if illegal_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=illegal_nodes,
            node_size=node_size, linewidths=2.2,
            edgecolors="crimson", node_color="white", ax=ax,
        )

    if marked_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=marked_nodes,
            node_size=int(node_size * 0.72),
            linewidths=1.8,
            edgecolors=(31 / 255, 127 / 255, 161 / 255),
            node_color="none",
            ax=ax,
        )

    nx.draw_networkx_labels(
        G, pos, labels={x: str(x) for x in G.nodes},
        font_size=font_size, font_family="DejaVu Sans", ax=ax,
    )

    nx.draw_networkx_edges(
        G, pos, width=1.1, arrows=True, arrowsize=5,
        ax=ax, connectionstyle="arc3,rad=0.05",
    )

    edge_labels = {(u, v): d["event"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels,
        font_size=max(font_size - 1, 1), font_family="DejaVu Sans",
        rotate=False, bbox=dict(facecolor="white", edgecolor="none", pad=0.2), ax=ax,
    )

    if G.x0 is not None and G.x0 in pos:
        x0, y0 = pos[G.x0]
        ax.annotate(
            "", xy=(x0 - 0.1, y0), xytext=(x0 - 0.8, y0),
            arrowprops=dict(arrowstyle="->", lw=1.8),
        )

    ax.axis("off")
    fig.tight_layout()

    if filename:
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.05, dpi=dpi)
    if show:
        plt.show()
    return fig, ax


def draw_bts(
    T: BTS,
    filename=None,
    title="AIC",
    layout="hybrid_kk",
    figsize=(13.5, 7.2),
    dpi=220,
    node_size=1350,      # 原来 2600，明显缩小
    font_size=7,         # 原来 10
    layout_scale=6.0,    # 新增：把节点间隔拉开
    yz_separation=3.6,   # 新增：Y/Z 横向间隔拉开
    show=True,
):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_title(title, fontsize=max(font_size + 3, 8))

    pos = get_bts_layout(
        T,
        layout=layout,
        scale=layout_scale,
        yz_separation=yz_separation,
    )

    Y_nodes = list(T.y_states())
    Z_nodes = list(T.z_states())

    nx.draw_networkx_nodes(
        T, pos, nodelist=Y_nodes,
        node_size=node_size, node_shape="o",
        linewidths=1.8, edgecolors="black",
        node_color="#EAF2FF", ax=ax,
    )

    nx.draw_networkx_nodes(
        T, pos, nodelist=Z_nodes,
        node_size=node_size, node_shape="s",
        linewidths=1.8, edgecolors="black",
        node_color="#FFF0D9", ax=ax,
    )

    labels = {}
    for yn in Y_nodes:
        labels[yn] = fmt_y_label(T.y_info(yn))
    for zn in Z_nodes:
        labels[zn] = fmt_z_label(T.z_info(zn), T.z_ctrl(zn), T.plant)

    text_items = nx.draw_networkx_labels(
        T, pos, labels=labels,
        font_size=font_size,
        font_family="DejaVu Sans",
        ax=ax,
    )

    for _, txt in text_items.items():
        txt.set_path_effects([pe.withStroke(linewidth=1.2, foreground="white")])

    ctrl_edges = [(u, v) for u, v, d in T.edges(data=True) if d.get("etype") == "ctrl"]
    obs_edges = [(u, v) for u, v, d in T.edges(data=True) if d.get("etype") == "obs"]

    nx.draw_networkx_edges(
        T, pos, edgelist=ctrl_edges,
        width=1.1,
        arrows=True,
        arrowsize=11,
        ax=ax,
        connectionstyle="arc3,rad=0.0",
    )

    nx.draw_networkx_edges(
        T, pos, edgelist=obs_edges,
        width=1.0,
        arrows=True,
        arrowsize=10,
        ax=ax,
        style="dashed",
        connectionstyle="arc3,rad=0.0",
    )

    obs_edge_labels = {
        (u, v): d["event"]
        for u, v, d in T.edges(data=True)
        if d.get("etype") == "obs"
    }

    nx.draw_networkx_edge_labels(
        T, pos, edge_labels=obs_edge_labels,
        font_size=font_size,
        font_family="DejaVu Sans",
        rotate=False,
        bbox=dict(facecolor="white", edgecolor="none", pad=0.12),
        ax=ax,
    )

    if T.y0 is not None and T.y0 in pos:
        x0, y0 = pos[T.y0]
        ax.annotate(
            "", xy=(x0 - 0.15, y0), xytext=(x0 - 1.0, y0),
            arrowprops=dict(arrowstyle="->", lw=1.8),
        )

    ax.text(
        0.02, 0.98,
        "Y-state: circle\nZ-state: square\nsolid: control\ndashed: observable event",
        transform=ax.transAxes,
        fontsize=max(font_size - 1, 1),
        va="top",
        bbox=dict(facecolor="white", edgecolor="gray", alpha=0.9),
    )

    ax.axis("off")
    fig.tight_layout()

    if filename:
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.05, dpi=dpi)
    if show:
        plt.show()
    return fig, ax


def draw_ubts(
    U: UBTS,
    filename=None,
    title="UBTS",
    layout="hybrid_spring",
    figsize=(16, 10),
    dpi=220,
    node_size=3000,
    font_size=9,
    show=True,
):
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_title(title, fontsize=max(font_size - 1, 1))

    Y_nodes = list(U.y_states())
    Z_nodes = list(U.z_states())

    H = U.to_undirected()
    if layout == "spring":
        base = nx.spring_layout(H, seed=7, k=1.6, iterations=300)
    else:
        base = nx.spring_layout(H, seed=7)

    pos = {}
    for n, (x, y) in base.items():
        if n in Y_nodes:
            pos[n] = (3.5 * (x - 1.2), 3.5 * y)
        else:
            pos[n] = (3.5 * (x + 1.2), 3.5 * y)

    nx.draw_networkx_nodes(
        U, pos, nodelist=Y_nodes,
        node_size=node_size, node_shape="o",
        linewidths=1.8, edgecolors="black",
        node_color="#EAF2FF", ax=ax,
    )
    nx.draw_networkx_nodes(
        U, pos, nodelist=Z_nodes,
        node_size=node_size, node_shape="s",
        linewidths=1.8, edgecolors="black",
        node_color="#FFF0D9", ax=ax,
    )

    labels = {}
    for y in Y_nodes:
        labels[y] = f"Y^{U.y_idx(y)}\n{fmt_state_set(U.y_info(y))}"
    for z in Z_nodes:
        labels[z] = f"Z^{U.z_idx(z)}\n{fmt_state_set(U.z_info(z))}\n{U.plant.ctrl_to_str(U.z_ctrl(z))}"

    text_items = nx.draw_networkx_labels(
        U, pos, labels=labels,
        font_size=font_size,
        font_family="DejaVu Sans",
        ax=ax,
    )
    for _, txt in text_items.items():
        txt.set_path_effects([pe.withStroke(linewidth=1.2, foreground="white")])

    ctrl_edges = [(u, v) for u, v, d in U.edges(data=True) if d.get("etype") == "ctrl"]
    obs_edges = [(u, v) for u, v, d in U.edges(data=True) if d.get("etype") == "obs"]

    nx.draw_networkx_edges(U, pos, edgelist=ctrl_edges, width=1.5, arrows=True, arrowsize=16, ax=ax)
    nx.draw_networkx_edges(U, pos, edgelist=obs_edges, width=1.2, arrows=True, arrowsize=14, style="dashed", ax=ax)

    obs_edge_labels = {
        (u, v): d["event"]
        for u, v, d in U.edges(data=True)
        if d.get("etype") == "obs"
    }
    nx.draw_networkx_edge_labels(
        U, pos, edge_labels=obs_edge_labels,
        font_size=font_size,
        font_family="DejaVu Sans",
        rotate=False,
        bbox=dict(facecolor="white", edgecolor="none", pad=0.12),
        ax=ax,
    )

    if U.y0 is not None and U.y0 in pos:
        x0, y0 = pos[U.y0]
        ax.annotate(
            "", xy=(x0 - 0.1, y0), xytext=(x0 - 0.9, y0),
            arrowprops=dict(arrowstyle="->", lw=1.8),
        )

    ax.axis("off")
    fig.tight_layout()
    if filename:
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.05, dpi=dpi)
    if show:
        plt.show()
    return fig, ax

# ------------------------------------------------------------------
# Compatibility aliases for older plotting scripts.
# ------------------------------------------------------------------
globals()["get_bcc_" + "ma" + "cro_layout"] = get_bcc_information_layout
globals()["fmt_" + "ma" + "cro_y_label"] = _fmt_info_y_label
globals()["fmt_" + "ma" + "cro_z_label"] = _fmt_info_z_label
