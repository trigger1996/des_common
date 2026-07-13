from __future__ import annotations

from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation, PillowWriter

from des_core import styles
from des_core.automata import DESExample, DFA, State
from des_core.deadlock import (
    BeliefStateSynthesisSnapshot,
    DeadlockSnapshot,
    PartialObservationSnapshot,
    make_belief_state_synthesis_snapshots,
    make_on_the_fly_snapshots,
    make_partial_observation_snapshots,
)


def save_original_system_png(
    dfa: DFA,
    pos: dict[State, tuple[float, float]],
    output: Path,
    title: str,
) -> None:
    graph = dfa.to_networkx()
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)
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
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)

    def update(frame: int) -> None:
        draw_snapshot(ax, example.dfa, example.layout, snapshots[frame], example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def save_belief_state_synthesis_animation(example: DESExample, output: Path) -> None:
    plant = example.original_dfa
    if plant is None:
        raise ValueError("belief-state synthesis animation requires original_dfa")

    snapshots = make_belief_state_synthesis_snapshots(plant, plant.observable)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)

    def update(frame: int) -> None:
        draw_belief_state_synthesis_snapshot(ax, snapshots[frame], pos, example.name)

    _save_animation_with_frames(fig, update, len(snapshots), output)
    plt.close(fig)


def save_belief_state_synthesis_final_png(example: DESExample, output: Path) -> None:
    plant = example.original_dfa
    if plant is None:
        raise ValueError("belief-state synthesis final PNG requires original_dfa")

    snapshots = make_belief_state_synthesis_snapshots(plant, plant.observable)
    pos = _belief_state_layout(snapshots)
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)
    draw_belief_state_synthesis_snapshot(ax, snapshots[-1], pos, example.name)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_partial_observation_animation(example: DESExample, output: Path) -> None:
    plant = example.original_dfa
    pos = example.original_layout
    if plant is None or pos is None:
        raise ValueError("partial-observation animation requires original_dfa and original_layout")

    snapshots = make_partial_observation_snapshots(plant, plant.observable)
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)

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
    frames_dir = output.with_name(f"{output.stem}_frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale_frame in frames_dir.glob("frame_*.png"):
        stale_frame.unlink()

    for frame in range(frame_count):
        update(frame)
        fig.savefig(frames_dir / f"frame_{frame:04d}.png", dpi=180)

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

    graph = nx.DiGraph()
    for node in sorted(snapshot.known_nodes):
        graph.add_node(node)
    for source, target, event, kind in sorted(snapshot.known_edges):
        graph.add_edge(source, target, event=event, kind=kind)

    node_colors = []
    node_edge_colors = []
    for node in graph.nodes:
        if node == snapshot.current:
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

    _draw_belief_state_nodes(ax, graph, pos, node_colors, node_edge_colors)
    _draw_belief_state_edges(ax, graph, pos)
    _set_graph_bounds(ax, pos)

    frontier = ", ".join(sorted(snapshot.frontier)) if snapshot.frontier else "<empty>"
    legend = (
        f"frontier: {frontier}\n"
        "node text is observer state i=(X, tag), tag in {Y,N,U}; fill colors keep the original meaning\n"
        "border: green=Y expanded non-deadlock, red=N expanded deadlock risk, gray=U not expanded yet"
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
    labels = {node: _wrap_belief_label(node) for node in graph.nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, ax=ax, font_size=7, font_weight="bold")


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
            arrowsize=18,
            connectionstyle="arc3,rad=0.12",
        )

    edge_labels = {
        (source, target): _edge_label(dfa, data["event"])
        for source, target, data in graph.edges(data=True)
    }
    nx.draw_networkx_edge_labels(
        graph,
        pos,
        edge_labels=edge_labels,
        ax=ax,
        font_size=7,
        rotate=False,
        bbox=styles.EDGE_LABEL_BOX,
    )


def _draw_belief_state_edges(
    ax: plt.Axes,
    graph: nx.DiGraph,
    pos: dict[State, tuple[float, float]],
) -> None:
    for source, target, data in graph.edges(data=True):
        if source == target:
            continue
        is_closure = data["kind"] == "closure"
        color = styles.UNOBSERVABLE_EDGE if is_closure else styles.CONTROLLABLE_EDGE
        style = "dashed" if is_closure else "solid"
        width = 2.2 if is_closure else 1.8
        nx.draw_networkx_edges(
            graph,
            pos,
            ax=ax,
            edgelist=[(source, target)],
            edge_color=color,
            width=width,
            style=style,
            arrows=True,
            arrowsize=18,
            connectionstyle="arc3,rad=0.12",
        )

    edge_labels = {
        (source, target): data["event"]
        for source, target, data in graph.edges(data=True)
        if pos[source] != pos[target]
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


def _belief_state_layout(
    snapshots: list[BeliefStateSynthesisSnapshot],
) -> dict[State, tuple[float, float]]:
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


def _wrap_belief_label(label: State) -> str:
    if len(label) <= 16 or "," not in label:
        return label
    return label.replace(",", ",\n")


def _edge_label(dfa: DFA, event: str) -> str:
    control = "u" if event in dfa.uncontrollable else "c"
    observation = "o" if event in dfa.observable else "uo"
    return f"{event} ({control},{observation})"
