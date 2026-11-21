from __future__ import annotations

from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyArrowPatch
from matplotlib.path import Path

from des_core import styles
from des_core.automata import DESExample, DFA, State
from des_core.deadlock import (
    BeliefStateSynthesisSnapshot,
    DeadlockSnapshot,
    PartialObservationSnapshot,
    make_on_the_fly_snapshots,
    make_partial_observation_snapshots,
)
from des_core.ll_bts import make_ll_bts_chain_snapshots, make_ll_bts_synthesis_snapshots


def save_original_system_png(
    dfa: DFA,
    pos: dict[State, tuple[float, float]],
    output: Path,
    title: str,
) -> None:
    graph = dfa.to_networkx()
    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)
    ax.set_title(title, loc="left", fontsize=13, fontweight="bold")
    ax.axis("off")

    node_colors = [styles.DEFAULT_NODE for _node in graph.nodes]
    node_edge_colors = [styles.DEFAULT_BORDER for _node in graph.nodes]
    _draw_nodes(ax, graph, pos, node_colors, node_edge_colors)
    _draw_edges(ax, graph, dfa, pos, snapshot=None)

    ax.text(
        0.01,
        0.02,
        "blue edge=uncontrollable, gray edge=controllable, purple edge=unobservable",
        transform=ax.transAxes,
        fontsize=9,
        va="bottom",
    )
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_animation(example: DESExample, output: Path) -> None:
    if example.original_dfa is not None:
        save_partial_observation_animation(example, output)

        return

    save_observer_synthesis_animation(example, output)


def save_observer_synthesis_animation(example: DESExample, output: Path) -> None:
    """Render on-the-fly synthesis on example.dfa, including observer DFAs."""

    if example.original_dfa is not None:
        save_belief_state_synthesis_animation(example, output)

        return

    snapshots = make_on_the_fly_snapshots(example.dfa)
    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)

    def update(frame: int) -> None:
        draw_snapshot(ax, example.dfa, example.layout, snapshots[frame], example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def save_belief_state_synthesis_animation(example: DESExample, output: Path) -> None:
    plant = example.original_dfa

    if plant is None:
        raise ValueError("belief-state synthesis animation requires original_dfa")

    snapshots = make_ll_bts_synthesis_snapshots(plant, example.lookahead_limit)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)

    def update(frame: int) -> None:
        draw_belief_state_synthesis_snapshot(ax, snapshots[frame], pos, example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def save_ll_bts_synthesis_animation(example: DESExample, output: Path) -> None:
    save_belief_state_synthesis_animation(example, output)


def save_ll_bts_chain_animation(example: DESExample, output: Path) -> None:
    plant = example.original_dfa

    if plant is None:
        raise ValueError("LL-BTS chain animation requires original_dfa")

    snapshots = make_ll_bts_chain_snapshots(plant, example.lookahead_limit)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(22, 12))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.9, bottom=0.08)

    def update(frame: int) -> None:
        draw_belief_state_synthesis_snapshot(ax, snapshots[frame], pos, example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def save_belief_state_synthesis_final_png(example: DESExample, output: Path) -> None:
    plant = example.original_dfa

    if plant is None:
        raise ValueError("belief-state synthesis final PNG requires original_dfa")

    snapshots = make_ll_bts_synthesis_snapshots(plant, example.lookahead_limit)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.86, bottom=0.12)
    draw_belief_state_synthesis_snapshot(ax, snapshots[-1], pos, example.name)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_ll_bts_final_png(example: DESExample, output: Path) -> None:
    save_belief_state_synthesis_final_png(example, output)


def save_ll_bts_chain_final_png(example: DESExample, output: Path) -> None:
    plant = example.original_dfa

    if plant is None:
        raise ValueError("LL-BTS chain final PNG requires original_dfa")

    snapshots = make_ll_bts_chain_snapshots(plant, example.lookahead_limit)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.86, bottom=0.12)
    draw_belief_state_synthesis_snapshot(ax, snapshots[-1], pos, example.name)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_partial_observation_animation(example: DESExample, output: Path) -> None:
    plant = example.original_dfa
    pos = example.original_layout

    if plant is None or pos is None:
        raise ValueError("partial-observation animation requires original_dfa and original_layout")

    snapshots = make_partial_observation_snapshots(plant, plant.observable)
    fig, ax = plt.subplots(figsize=(14, 8))
    fig.subplots_adjust(left=0.03, right=0.98, top=0.86, bottom=0.12)

    def update(frame: int) -> None:
        draw_partial_observation_snapshot(ax, plant, pos, snapshots[frame], example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def _save_animation_with_frames(
    fig: plt.Figure,
    update: Callable[[int], None],
    frame_count: int,
    output: Path,
) -> None:
    animation = FuncAnimation(fig, update, frames=frame_count, interval=1200, repeat=True)
    animation.save(output, writer=PillowWriter(fps=1))


def draw_snapshot(
    ax: plt.Axes,
    dfa: DFA,
    pos: dict[State, tuple[float, float]],
    snapshot: DeadlockSnapshot,
    title_prefix: str,
) -> None:
    ax.clear()
    ax.set_title(f"{_short_title_prefix(title_prefix)}\n{snapshot.title}", loc="left", fontsize=12, fontweight="bold")
    ax.axis("off")

    graph = dfa.to_networkx()
    node_colors = []
    node_edge_colors = []

    for node in graph.nodes:
        if node not in snapshot.known_nodes:
            node_colors.append(styles.UNKNOWN_NODE)
            node_edge_colors.append(styles.UNKNOWN_BORDER)
        elif node in snapshot.frontier:
            node_colors.append(styles.FRONTIER_NODE)
            node_edge_colors.append(styles.FRONTIER_BORDER)
        elif node in snapshot.nondeadlock:
            node_colors.append(styles.NONDEADLOCK_NODE)
            node_edge_colors.append(styles.NONDEADLOCK_BORDER)
        elif node in snapshot.deadlock:
            node_colors.append(styles.DEADLOCK_NODE)
            node_edge_colors.append(styles.DEADLOCK_BORDER)
        else:
            node_colors.append(styles.DEFAULT_NODE)
            node_edge_colors.append(styles.DEFAULT_BORDER)

    _draw_nodes(ax, graph, pos, node_colors, node_edge_colors)
    _draw_edges(ax, graph, dfa, pos, snapshot)
    _set_graph_bounds(ax, pos)

    legend = (
        "green=known non-deadlock, red=known deadlock, yellow=frontier\n"
        "blue edge=uncontrollable, gray edge=controllable, purple edge=unobservable, dotted=edge not discovered yet"
    )
    ax.text(0.01, 0.02, legend, transform=ax.transAxes, fontsize=9, va="bottom")


def draw_partial_observation_snapshot(
    ax: plt.Axes,
    plant: DFA,
    pos: dict[State, tuple[float, float]],
    snapshot: PartialObservationSnapshot,
    title_prefix: str,
) -> None:
    ax.clear()

    if snapshot.certain_deadlock:
        status = "certain deadlock"
    elif snapshot.possible_deadlock:
        status = "possible deadlock risk"
    elif snapshot.robust_nondeadlock:
        status = "robust non-deadlock"
    else:
        status = "plant on-the-fly"

    ax.set_title(
        f"{_short_title_prefix(title_prefix)}\n{snapshot.title} ({status})",
        loc="left",
        fontsize=12,
        fontweight="bold",
    )
    ax.axis("off")

    graph = plant.to_networkx()
    node_colors = []
    node_edge_colors = []

    for node in graph.nodes:
        if node in snapshot.possible_deadlock_states:
            node_colors.append(styles.POSSIBLE_DEADLOCK_NODE)
            node_edge_colors.append(styles.POSSIBLE_DEADLOCK_BORDER)
        elif node in snapshot.belief:
            node_colors.append(styles.BELIEF_NODE)
            node_edge_colors.append(styles.BELIEF_BORDER)
        elif node not in snapshot.known_nodes:
            node_colors.append(styles.UNKNOWN_NODE)
            node_edge_colors.append(styles.UNKNOWN_BORDER)
        elif node in snapshot.nondeadlock:
            node_colors.append(styles.NONDEADLOCK_NODE)
            node_edge_colors.append(styles.NONDEADLOCK_BORDER)
        elif node in snapshot.deadlock:
            node_colors.append(styles.DEADLOCK_NODE)
            node_edge_colors.append(styles.DEADLOCK_BORDER)
        else:
            node_colors.append(styles.DEFAULT_NODE)
            node_edge_colors.append(styles.DEFAULT_BORDER)

    _draw_nodes(ax, graph, pos, node_colors, node_edge_colors)
    _draw_edges(ax, graph, plant, pos, snapshot)
    _set_graph_bounds(ax, pos)

    trace = ", ".join(snapshot.observed_trace) if snapshot.observed_trace else "<empty>"
    belief = "{" + ",".join(sorted(snapshot.belief)) + "}"
    legend = (
        f"observed trace: {trace}    current belief: {belief}\n"
        "yellow=current belief, orange=possible deadlock state, green=known non-deadlock, red=known deadlock\n"
        "purple dashed=unobservable, dotted=edge not discovered yet"
    )
    ax.text(0.01, 0.02, legend, transform=ax.transAxes, fontsize=9, va="bottom")


def draw_belief_state_synthesis_snapshot(
    ax: plt.Axes,
    snapshot: BeliefStateSynthesisSnapshot,
    pos: dict[State, tuple[float, float]],
    title_prefix: str,
) -> None:
    ax.clear()
    ax.set_title(
        f"{_short_title_prefix(title_prefix)}\n{snapshot.title}",
        loc="left",
        fontsize=12,
        fontweight="bold",
    )
    ax.axis("off")

    is_ll_bts = any(node.startswith(("D(", "O(")) for node in snapshot.known_nodes | snapshot.faded_nodes)

    if is_ll_bts:
        if snapshot.layout_style == "tree":
            pos = _ll_bts_tree_layout_for_snapshot(snapshot)
        elif snapshot.layout_style == "chain" or snapshot.title.startswith("chain stage"):
            pos = _ll_bts_chain_layout_for_snapshot(snapshot)
        else:
            pos = _ll_bts_layout_for_nodes(snapshot.known_nodes | snapshot.faded_nodes)

    graph = nx.DiGraph()

    for node in sorted(snapshot.known_nodes | snapshot.faded_nodes):
        graph.add_node(node)

    for source, target, event, kind in sorted(snapshot.known_edges | snapshot.faded_edges):
        graph.add_edge(source, target, event=event, kind=kind)

    node_colors = []
    node_edge_colors = []

    for node in graph.nodes:
        if is_ll_bts and str(node).startswith("D("):
            node_colors.append(styles.BELIEF_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.DEFAULT_BORDER))
        elif is_ll_bts and str(node).startswith("O("):
            node_colors.append(styles.DEFAULT_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.DEFAULT_BORDER))
        elif node == snapshot.current:
            node_colors.append(styles.BELIEF_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.BELIEF_BORDER))
        elif node in snapshot.frontier:
            node_colors.append(styles.FRONTIER_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.FRONTIER_BORDER))
        elif node in snapshot.deadlock:
            node_colors.append(styles.DEADLOCK_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.DEADLOCK_BORDER))
        elif node in snapshot.closed_beliefs:
            node_colors.append(styles.NONDEADLOCK_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.NONDEADLOCK_BORDER))
        elif node in snapshot.raw_beliefs:
            node_colors.append(styles.DEFAULT_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.DEFAULT_BORDER))
        else:
            node_colors.append(styles.UNKNOWN_NODE)
            node_edge_colors.append(_tag_border(snapshot, node, styles.UNKNOWN_BORDER))

    faded_graph = graph.edge_subgraph(
        [(source, target) for source, target, _event, _kind in snapshot.faded_edges]
    ).copy()

    for node in snapshot.faded_nodes:
        faded_graph.add_node(node)

    current_graph = graph.edge_subgraph(
        [(source, target) for source, target, _event, _kind in snapshot.known_edges]
    ).copy()

    for node in snapshot.known_nodes:
        current_graph.add_node(node)

    if faded_graph.nodes:
        faded_node_colors = [styles.UNKNOWN_NODE for _node in faded_graph.nodes]
        faded_border_colors = [styles.UNKNOWN_BORDER for _node in faded_graph.nodes]
        _draw_belief_state_nodes(
            ax,
            faded_graph,
            pos,
            faded_node_colors,
            faded_border_colors,
            alpha=0.25,
            label_style=snapshot.label_style,
        )
        _draw_belief_state_edges(ax, faded_graph, pos, alpha=0.22, draw_labels=False)

    current_node_colors = [node_colors[list(graph.nodes).index(node)] for node in current_graph.nodes]
    current_border_colors = [node_edge_colors[list(graph.nodes).index(node)] for node in current_graph.nodes]
    _draw_belief_state_nodes(
        ax,
        current_graph,
        pos,
        current_node_colors,
        current_border_colors,
        label_style=snapshot.label_style,
    )
    _draw_belief_state_edges(
        ax,
        current_graph,
        pos,
        no_nodes=snapshot.no,
        unknown_nodes=snapshot.unknown,
    )
    _set_graph_bounds(ax, pos)

    if is_ll_bts:
        legend = (
            "node text is LL-BTS information state; yellow=decision, blue=observation\n"
            "border/edge: red=bad state removed, purple=inconsistent state removed"
        )
    else:
        frontier = ", ".join(sorted(snapshot.frontier)) if snapshot.frontier else "<empty>"
        legend = (
            f"frontier: {frontier}\n"
            "node text is information state, tag in {Y,N,U}\n"
            "border: green=Y locally verified, red=N bad, purple=U inconsistent/pending"
        )

    ax.text(0.01, 0.02, legend, transform=ax.transAxes, fontsize=9, va="bottom")


def _tag_border(snapshot: BeliefStateSynthesisSnapshot, node: State, fallback: str) -> str:
    if node in snapshot.yes:
        return styles.TAG_Y_BORDER

    if node in snapshot.no:
        return styles.TAG_N_BORDER

    if node in snapshot.unknown:
        return styles.TAG_U_BORDER

    return fallback


def _set_graph_bounds(ax: plt.Axes, pos: dict[State, tuple[float, float]]) -> None:
    if not pos:
        return

    xs = [point[0] for point in pos.values()]
    ys = [point[1] for point in pos.values()]
    x_span = max(xs) - min(xs) or 1.0
    y_span = max(ys) - min(ys) or 1.0
    ax.set_xlim(min(xs) - x_span * 0.12, max(xs) + x_span * 0.12)
    ax.set_ylim(min(ys) - y_span * 0.32, max(ys) + y_span * 0.18)


def _short_title_prefix(title_prefix: str) -> str:
    return title_prefix.replace("_partial_observation", "").replace("_full", "")


def _draw_nodes(
    ax: plt.Axes,
    graph: nx.DiGraph,
    pos: dict[State, tuple[float, float]],
    node_colors: list[str],
    node_edge_colors: list[str],
) -> None:
    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_color=node_colors,
        edgecolors=node_edge_colors,
        linewidths=2,
        node_size=styles.NODE_SIZE,
    )
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=8, font_weight="bold")


def _draw_belief_state_nodes(
    ax: plt.Axes,
    graph: nx.DiGraph,
    pos: dict[State, tuple[float, float]],
    node_colors: list[str],
    node_edge_colors: list[str],
    alpha: float=1.0,
    label_style: str="full",
) -> None:
    is_ll_bts = any(str(node).startswith(("D(", "O(")) for node in graph.nodes)
    node_count = max(1, graph.number_of_nodes())

    if is_ll_bts and label_style == "compact":
        node_size = 760 if node_count > 40 else 980
        font_size = 4.2 if node_count > 40 else 5
    else:
        node_size = 1300 if is_ll_bts else styles.NODE_SIZE
        font_size = 5 if is_ll_bts and node_count > 30 else 6 if is_ll_bts else 7

    nx.draw_networkx_nodes(
        graph,
        pos,
        ax=ax,
        node_color=node_colors,
        edgecolors=node_edge_colors,
        linewidths=2,
        node_size=node_size,
        alpha=alpha,
    )
    labels = {node: _wrap_belief_label(node, label_style) for node in graph.nodes}
    nx.draw_networkx_labels(
        graph,
        pos,
        labels=labels,
        ax=ax,
        font_size=font_size,
        font_weight="bold",
        alpha=alpha,
    )


def _draw_edges(
    ax: plt.Axes,
    graph: nx.DiGraph,
    dfa: DFA,
    pos: dict[State, tuple[float, float]],
    snapshot: DeadlockSnapshot | PartialObservationSnapshot | None,
) -> None:
    visible_edges = None

    if snapshot is not None:
        visible_edges = {(source, target, event) for source, target, event in snapshot.known_edges}

    for source, target, data in graph.edges(data=True):
        event = data["event"]
        visible = visible_edges is None or (source, target, event) in visible_edges
        observable = event in dfa.observable
        uncontrollable = event in dfa.uncontrollable

        if not visible:
            color = styles.UNDISCOVERED_EDGE
            width = 1.0
            style = "dotted"
            alpha = 0.25
        elif not observable:
            color = styles.UNOBSERVABLE_EDGE
            width = 2.2
            style = "dashed"
            alpha = 1.0
        elif uncontrollable:
            color = styles.UNCONTROLLABLE_EDGE
            width = 2.3
            style = "solid"
            alpha = 1.0
        else:
            color = styles.CONTROLLABLE_EDGE
            width = 1.8
            style = "solid"
            alpha = 1.0

        if source == target:
            _draw_self_loop(ax, pos[source], color, width, style, alpha)
        else:
            nx.draw_networkx_edges(
                graph,
                pos,
                ax=ax,
                edgelist=[(source, target)],
                edge_color=color,
                width=width,
                style=style,
                alpha=alpha,
                arrows=True,
                arrowstyle="-|>",
                arrowsize=26,
                connectionstyle="arc3,rad=0.12",
                min_source_margin=18,
                min_target_margin=22,
            )

    edge_labels = {
        (source, target): _edge_label(dfa, data["event"])
        for source, target, data in graph.edges(data=True)
    }
    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels={edge: label for edge, label in edge_labels.items() if edge[0] != edge[1]},
        ax=ax,
        font_size=7,
        rotate=False,
        bbox=styles.EDGE_LABEL_BOX,
    )

    for (source, target), label in edge_labels.items():
        if source == target:
            x, y = pos[source]
            ax.text(
                x,
                y + 1.0,
                label,
                fontsize=7,
                ha="center",
                va="center",
                bbox=styles.EDGE_LABEL_BOX,
            )


def _draw_self_loop(
    ax: plt.Axes,
    center: tuple[float, float],
    color: str,
    width: float,
    style: str,
    alpha: float,
) -> None:
    x, y = center
    vertices = [
        (x + 0.35, y + 0.45),
        (x + 1.15, y + 1.25),
        (x - 1.15, y + 1.25),
        (x - 0.35, y + 0.45),
    ]
    path = Path(vertices, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
    loop = FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=24,
        color=color,
        linewidth=width,
        linestyle=style,
        alpha=alpha,
        shrinkA=0,
        shrinkB=0,
    )
    ax.add_patch(loop)


def _draw_belief_state_edges(
    ax: plt.Axes,
    graph: nx.DiGraph,
    pos: dict[State, tuple[float, float]],
    alpha: float=1.0,
    draw_labels: bool=True,
    no_nodes: frozenset[State]=frozenset(),
    unknown_nodes: frozenset[State]=frozenset(),
) -> None:
    is_ll_bts = any(str(node).startswith(("D(", "O(")) for node in graph.nodes)

    for source, target, data in graph.edges(data=True):
        is_closure = data["kind"] == "closure"

        if source in no_nodes or target in no_nodes:
            color = styles.TAG_N_BORDER
        elif source in unknown_nodes or target in unknown_nodes:
            color = styles.TAG_U_BORDER
        else:
            color = styles.UNOBSERVABLE_EDGE if is_closure else styles.CONTROLLABLE_EDGE

        style = "dashed" if is_closure else "solid"
        width = 2.6 if color in {styles.TAG_N_BORDER, styles.TAG_U_BORDER} else 2.2 if is_closure else 1.8

        if source == target:
            _draw_self_loop(ax, pos[source], color, width, style, 1.0)

            continue

        nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            edgelist=[(source, target)],
            edge_color=color,
            width=width,
            style=style,
            alpha=alpha,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=26,
            connectionstyle="arc3,rad=0.12",
            min_source_margin=18,
            min_target_margin=22,
        )

    if not draw_labels or is_ll_bts:
        return

    edge_labels = {
        (source, target): data["event"]
        for source, target, data in graph.edges(data=True)
        if source != target
    }

    if edge_labels:
        nx.draw_networkx_edge_labels(
            graph,
            pos,
            edge_labels=edge_labels,
            ax=ax,
            font_size=7,
            rotate=False,
            bbox=styles.EDGE_LABEL_BOX,
        )

    for source, target, data in graph.edges(data=True):
        if source != target:
            continue

        x, y = pos[source]
        ax.text(
            x,
            y + 1.0,
            data["event"],
            fontsize=7,
            ha="center",
            va="center",
            bbox=styles.EDGE_LABEL_BOX,
        )


def _belief_state_layout(
    snapshots: list[BeliefStateSynthesisSnapshot],
) -> dict[State, tuple[float, float]]:
    if any(node.startswith(("D(", "O(")) for snapshot in snapshots for node in snapshot.known_nodes):
        return _ll_bts_layout(snapshots)

    parent: dict[State, State] = {}

    def find(node: State) -> State:
        parent.setdefault(node, node)

        if parent[node] != node:
            parent[node] = find(parent[node])

        return parent[node]

    def union(source: State, target: State) -> None:
        source_root = find(source)
        target_root = find(target)

        if source_root != target_root:
            parent[source_root] = target_root

    for snapshot in snapshots:
        for node in snapshot.known_nodes:
            find(node)

        for source, target in snapshot.layout_aliases:
            union(source, target)

    order: list[State] = []
    seen_roots: set[State] = set()
    known_nodes: set[State] = set()

    for snapshot in snapshots:
        for node in sorted(snapshot.known_nodes):
            known_nodes.add(node)
            root = find(node)

            if root in seen_roots:
                continue

            seen_roots.add(root)
            order.append(root)

    columns = 3
    spacing_x = 4.2
    spacing_y = 2.2
    root_positions = {
        node: ((index % columns) * spacing_x, -(index // columns) * spacing_y)
        for index, node in enumerate(order)
    }

    return {node: root_positions[find(node)] for node in known_nodes}


def _wrap_belief_label(label: State, label_style: str="full") -> str:
    if label.startswith(("D(", "O(")):
        if label_style == "compact":
            return _compact_ll_bts_label(label)

        return _wrap_ll_bts_label(label)

    if len(label) <= 16 or "," not in label:
        return label

    return label.replace(",", ",\n")


def _ll_bts_layout(
    snapshots: list[BeliefStateSynthesisSnapshot],
) -> dict[State, tuple[float, float]]:
    decision_nodes: list[State] = []
    observation_nodes: list[State] = []
    seen: set[State] = set()

    for snapshot in snapshots:
        for node in sorted(snapshot.known_nodes):
            if node in seen:
                continue

            seen.add(node)

            if node.startswith("D("):
                decision_nodes.append(node)
            elif node.startswith("O("):
                observation_nodes.append(node)
            else:
                decision_nodes.append(node)

    pos: dict[State, tuple[float, float]] = {}

    for index, node in enumerate(decision_nodes):
        pos[node] = (0.0, -index * 1.45)

    for index, node in enumerate(observation_nodes):
        pos[node] = (5.2, -index * 0.95)

    return pos


def _ll_bts_layout_for_nodes(nodes: frozenset[State]) -> dict[State, tuple[float, float]]:
    decision_nodes = sorted(node for node in nodes if node.startswith("D("))
    observation_nodes = sorted(node for node in nodes if node.startswith("O("))
    other_nodes = sorted(node for node in nodes if not node.startswith(("D(", "O(")))

    def column_positions(column_nodes: list[State], x: float, spacing: float) -> dict[State, tuple[float, float]]:
        if not column_nodes:
            return {}

        offset = (len(column_nodes) - 1) * spacing / 2.0

        return {
            node: (x, offset - index * spacing)
            for index, node in enumerate(column_nodes)
        }

    pos: dict[State, tuple[float, float]] = {}
    pos.update(column_positions(decision_nodes + other_nodes, 0.0, 1.25))
    pos.update(column_positions(observation_nodes, 5.8, 0.85))

    return pos


def _ll_bts_chain_layout_for_snapshot(
    snapshot: BeliefStateSynthesisSnapshot,
) -> dict[State, tuple[float, float]]:
    current = snapshot.current
    direct_observations = sorted(
        target
        for source, target, _event, kind in snapshot.known_edges
        if kind == "control" and source == current
    )
    successor_decisions = sorted(
        target
        for source, target, _event, kind in snapshot.known_edges
        if kind == "observable" and source in direct_observations
    )
    preview_observations = sorted(
        target
        for source, target, _event, kind in snapshot.known_edges
        if kind == "control" and source in successor_decisions
    )
    assigned = set(direct_observations) | set(successor_decisions) | set(preview_observations)

    if current is not None:
        assigned.add(current)

    remaining = sorted(node for node in snapshot.known_nodes | snapshot.faded_nodes if node not in assigned)

    pos: dict[State, tuple[float, float]] = {}

    def put_column(nodes: list[State], x: float, spacing: float) -> None:
        if not nodes:
            return

        offset = (len(nodes) - 1) * spacing / 2.0

        for index, node in enumerate(nodes):
            pos[node] = (x, offset - index * spacing)

    def put_grid(nodes: list[State], x: float, spacing_x: float, spacing_y: float, rows: int) -> None:
        if not nodes:
            return

        row_count = min(rows, len(nodes))
        offset = (row_count - 1) * spacing_y / 2.0

        for index, node in enumerate(nodes):
            column = index // rows
            row = index % rows
            pos[node] = (x + column * spacing_x, offset - row * spacing_y)

    if current is not None:
        pos[current] = (0.0, 0.0)

    put_column(direct_observations, 5.0, 2.05)
    put_column(successor_decisions, 10.0, 1.85)
    put_column(preview_observations, 15.0, 1.85)
    put_grid(remaining, 20.0, 3.8, 1.65, 10)

    return pos


def _ll_bts_tree_layout_for_snapshot(
    snapshot: BeliefStateSynthesisSnapshot,
) -> dict[State, tuple[float, float]]:
    nodes = sorted(snapshot.known_nodes | snapshot.faded_nodes)
    edges = sorted(snapshot.known_edges | snapshot.faded_edges)

    if not nodes:
        return {}

    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from((source, target) for source, target, _event, _kind in edges)

    roots = sorted(node for node in nodes if graph.in_degree(node) == 0)

    if snapshot.current in graph:
        roots = [node for node in roots if node != snapshot.current]
        roots.insert(0, snapshot.current)

    if not roots:
        roots = [nodes[0]]

    level: dict[State, int] = {node: 0 for node in roots}

    for _ in range(max(1, len(nodes))):
        changed = False

        for source, target in graph.edges:
            if source not in level:
                continue

            next_level = level[source] + 1

            if next_level > level.get(target, -1):
                level[target] = next_level
                changed = True

        if not changed:
            break

    fallback_level = max(level.values(), default=0) + 1

    for node in nodes:
        level.setdefault(node, fallback_level)

    groups: dict[int, list[State]] = {}

    for node, node_level in level.items():
        groups.setdefault(node_level, []).append(node)

    pos: dict[State, tuple[float, float]] = {}
    x_spacing = 5.8
    y_spacing = 2.2

    for node_level in sorted(groups):
        column = sorted(groups[node_level], key=_ll_bts_layout_sort_key)
        offset = (len(column) - 1) * y_spacing / 2.0

        for index, node in enumerate(column):
            pos[node] = (node_level * x_spacing, offset - index * y_spacing)

    return pos


def _ll_bts_layout_sort_key(node: State) -> tuple[int, str]:
    if node.startswith("D("):
        return (0, node)

    if node.startswith("O("):
        return (1, node)

    return (2, node)


def _wrap_ll_bts_label(label: State) -> str:
    tag = ""
    body = label

    if ":" in label:
        body, tag = label.rsplit(":", 1)
        tag = f":{tag}"

    body = body.replace("|", "|\n")
    body = body.replace(",", ",\n")

    return f"{body}{tag}"


def _compact_ll_bts_label(label: State) -> str:
    if label.startswith("D(") and label.endswith(")"):
        body = label[2:-1]
        root, belief = body.split(",", 1)

        return f"D {root}\n{_compact_set_text(belief)}"

    if label.startswith("O(") and label.endswith(")"):
        body = label[2:-1]

        if "},{" in body:
            belief_body, pattern_body = body.split("},{", 1)
            belief = f"{belief_body}}}"
            pattern = f"{{{pattern_body}"
        else:
            belief, pattern = body, "{}"

        return f"O\n{_compact_set_text(belief)}\ng={_compact_set_text(pattern)}"

    return label


def _compact_set_text(text: str) -> str:
    if text == "{}":
        return "{}"

    if not (text.startswith("{") and text.endswith("}")):
        return text

    items = [item for item in text[1:-1].split(",") if item]

    if len(items) <= 3:
        return "{" + ",".join(items) + "}"

    return "{" + ",".join(items[:3]) + f",+{len(items) - 3}" + "}"


def _edge_label(dfa: DFA, event: str) -> str:
    control = "u" if event in dfa.uncontrollable else "c"
    observation = "o" if event in dfa.observable else "uo"

    return f"{event} ({control},{observation})"
