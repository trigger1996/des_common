"""Paper-style export for the DIRM observer.

This replacement keeps the observer construction unchanged and only changes
how reachable observer states are written and drawn.

Goals:
1. Show the paper's full triple (x_tilde, q_hat, q), not just cardinalities.
2. Use the paper notation 0N / 2Y instead of (0, False) / (2, True).
3. Make the PNG readable: larger rounded rectangles, consistent font, larger
   canvas, and a hand-tuned layout for the paper's Example 6 / Fig. 3.
4. Fall back to a generic layered layout for other observers.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple, Optional

from .observer import DIRMObserver, ObserverState
from .plot.routing import rectangle_boundary_point


# -----------------------------
# Formatting helpers
# -----------------------------

def _aug_state_key(state: tuple[int, bool]) -> tuple[int, int]:
    # N(False) before Y(True) for a stable, human-readable order.
    return (int(state[0]), 1 if bool(state[1]) else 0)


def _state_key(state: ObserverState) -> Tuple[str, str, str]:
    return (
        repr(state.x_tilde),
        repr(sorted(state.q_hat, key=_aug_state_key)),
        repr(sorted(state.q, key=_aug_state_key)),
    )


def _format_aug_state(state: tuple[int, bool]) -> str:
    return f"{state[0]}{'Y' if state[1] else 'N'}"


def _format_aug_set(states: Iterable[tuple[int, bool]]) -> str:
    ordered = sorted(states, key=_aug_state_key)
    return "{" + ",".join(_format_aug_state(s) for s in ordered) + "}"


def _observer_label_lines(state: ObserverState) -> list[str]:
    # Readable three-line version. This is much easier to read than one long line.
    return [
        _format_aug_state(state.x_tilde),
        _format_aug_set(state.q_hat),
        _format_aug_set(state.q),
    ]


def _state_text(state: ObserverState) -> str:
    return "\n".join((
        f"x_tilde = {_format_aug_state(state.x_tilde)}",
        f"q_hat   = {_format_aug_set(state.q_hat)}",
        f"q       = {_format_aug_set(state.q)}",
    ))


# -----------------------------
# TXT export
# -----------------------------

def write_observer_text(
    graph: Mapping[ObserverState, Mapping[str, ObserverState]],
    words: Mapping[ObserverState, Tuple[str, ...]],
    path: str | Path,
) -> Path:
    """Write a deterministic, complete listing of observer states and edges."""
    path = Path(path)
    states = sorted(graph, key=lambda state: (len(words[state]), _state_key(state)))
    indices = {state: index for index, state in enumerate(states)}
    lines = ["DIRM observer", "=" * 72, "", "States"]
    for state in states:
        word = "epsilon" if not words[state] else " ".join(words[state])
        lines.extend((f"S{indices[state]}  shortest plant word: {word}", _state_text(state), ""))
    lines.extend(("Transitions", "-" * 72))
    for source in states:
        for event, target in sorted(graph[source].items(), key=lambda item: (item[0], _state_key(item[1]))):
            lines.append(f"S{indices[source]} --{event}--> S{indices[target]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# -----------------------------
# Layout helpers
# -----------------------------

def _lookup_state(
    graph: Mapping[ObserverState, Mapping[str, ObserverState]],
    x_tilde: tuple[int, bool],
    q_hat: Iterable[tuple[int, bool]],
    q: Iterable[tuple[int, bool]],
) -> Optional[ObserverState]:
    q_hat_f = frozenset(q_hat)
    q_f = frozenset(q)
    for state in graph:
        if state.x_tilde == x_tilde and state.q_hat == q_hat_f and state.q == q_f:
            return state
    return None


def _paper_example_positions(
    graph: Mapping[ObserverState, Mapping[str, ObserverState]],
) -> Optional[Dict[ObserverState, Tuple[float, float]]]:
    """Return hand-tuned positions for the Automatica paper Example 6 / Fig. 3.

    If the graph does not match that example, return None and let the caller
    fall back to a generic layered layout.
    """
    N = False
    Y = True

    specs = [
        # left column
        ((0, N), [(0, N), (1, N)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (0.0, 0.0)),
        ((2, Y), [(2, Y), (3, Y)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (0.0, -1.55)),
        ((4, Y), [(4, Y), (5, Y)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (0.0, -3.10)),
        ((6, Y), [(6, Y), (8, N), (9, N)], [(6, Y), (8, N), (9, N)], (0.0, -4.65)),
        ((8, N), [(6, Y), (8, N), (9, N)], [(6, Y), (8, N), (9, N)], (0.0, -6.20)),
        ((9, N), [(6, Y), (8, N), (9, N)], [(6, Y), (8, N), (9, N)], (0.0, -7.75)),
        # right column
        ((1, N), [(0, N), (1, N)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (6.4, 0.0)),
        ((3, Y), [(2, Y), (3, Y)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (6.4, -1.55)),
        ((5, Y), [(4, Y), (5, Y)], [(0, N), (1, N), (2, Y), (3, Y), (4, Y), (5, Y)], (6.4, -3.10)),
        ((7, Y), [(7, Y)], [(7, Y)], (6.4, -4.65)),
        ((9, Y), [(9, Y)], [(9, Y)], (6.4, -6.20)),
        # bottom singleton 9N in paper figure is centered under 9Y
        ((9, N), [(9, N)], [(9, N)], (4.2, -7.75)),
    ]

    positions: Dict[ObserverState, Tuple[float, float]] = {}
    for x_tilde, q_hat, q, xy in specs:
        state = _lookup_state(graph, x_tilde, q_hat, q)
        if state is None:
            return None
        positions[state] = xy
    # The hand-tuned layout is valid only for the exact graph it describes.
    # Independent example revisions may preserve the listed states while
    # introducing additional observer states; those require the generic layout.
    if set(positions) != set(graph):
        return None
    return positions


def _generic_positions(
    graph: Mapping[ObserverState, Mapping[str, ObserverState]],
    words: Mapping[ObserverState, Tuple[str, ...]],
) -> Dict[ObserverState, Tuple[float, float]]:
    levels: Dict[int, list[ObserverState]] = defaultdict(list)
    for state in graph:
        levels[len(words[state])].append(state)
    for states in levels.values():
        states.sort(key=_state_key)

    positions: Dict[ObserverState, Tuple[float, float]] = {}
    x_gap = 6.1
    y_gap = 1.65
    for depth, states in sorted(levels.items()):
        for idx, state in enumerate(states):
            positions[state] = (depth * x_gap, -idx * y_gap)
    return positions


# -----------------------------
# PNG export
# -----------------------------

def draw_observer(
    graph: Mapping[ObserverState, Mapping[str, ObserverState]],
    words: Mapping[ObserverState, Tuple[str, ...]],
    path: str | Path,
) -> Path:
    """Draw observer states in a paper-like and readable format."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    path = Path(path)

    positions = _paper_example_positions(graph)
    paper_mode = positions is not None
    if positions is None:
        positions = _generic_positions(graph, words)

    # Visual constants.
    if paper_mode:
        box_width = 4.95
        box_height = 0.96
        fig_w = 14.5
        fig_h = 8.3
        font_size = 10.4
        title = "DIRM-observer  Obs(\u1d40G) of G"
    else:
        box_width = 4.85
        box_height = 0.96
        x_values = [xy[0] for xy in positions.values()]
        y_values = [xy[1] for xy in positions.values()]
        fig_w = max(12.0, (max(x_values) - min(x_values) + 7.5) * 0.95)
        fig_h = max(6.5, (max(y_values) - min(y_values) + 4.0) * 0.90)
        font_size = 10.0
        title = "DIRM observer"

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_axis_off()

    # Draw edges first.
    def draw_edge(source: ObserverState, target: ObserverState, event: str) -> None:
        x1, y1 = positions[source]
        x2, y2 = positions[target]

        rad = 0.0
        label_dx = 0.0
        label_dy = 0.0

        if source == target:
            # self loop
            start = (x1 + box_width * 0.18, y1 - box_height / 2 - 0.035)
            end = (x1 - box_width * 0.18, y1 - box_height / 2 - 0.035)
            rad = -1.0
            label_dx, label_dy = 0.0, -0.65
        else:
            # Data-coordinate anchors are independent of DPI and keep the
            # complete arrowhead outside the destination box.
            start = rectangle_boundary_point(
                (x1, y1), (x2, y2), box_width / 2, box_height / 2, margin=0.035
            )
            end = rectangle_boundary_point(
                (x2, y2), (x1, y1), box_width / 2, box_height / 2, margin=0.035
            )
            if abs(y1 - y2) < 1e-9:
                label_dy = 0.16
            elif abs(x1 - x2) < 1e-9:
                label_dx, label_dy = -0.18, 0.02
            else:
                # diagonal / curved edge for the paper figure feel.
                if x1 < x2:
                    rad = -0.22
                    label_dx, label_dy = 0.10, 0.23
                else:
                    rad = 0.22
                    label_dx, label_dy = -0.10, 0.23

        patch = FancyArrowPatch(
            start,
            end,
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=1.35,
            color="black",
            shrinkA=0,
            shrinkB=0,
            zorder=2.5,
        )
        ax.add_patch(patch)
        ax.text(
            (start[0] + end[0]) / 2 + label_dx,
            (start[1] + end[1]) / 2 + label_dy,
            event,
            ha="center",
            va="center",
            fontsize=12,
            family="serif",
            style="italic",
            zorder=5,
        )

    states = sorted(graph, key=_state_key)
    for source in states:
        for event, target in sorted(graph[source].items(), key=lambda item: (item[0], _state_key(item[1]))):
            draw_edge(source, target, event)

    # Draw nodes.
    for state in states:
        x, y = positions[state]
        rect = FancyBboxPatch(
            (x - box_width / 2, y - box_height / 2),
            box_width,
            box_height,
            boxstyle="round,pad=0.11,rounding_size=0.12",
            linewidth=1.25,
            facecolor="white",
            edgecolor="black",
            zorder=3,
        )
        ax.add_patch(rect)
        label = "\n".join(_observer_label_lines(state))
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=font_size,
            family="serif",
            linespacing=1.10,
            zorder=4,
        )

    # Initial-state marker: draw a downward arrow above the unique initial state.
    initial = min(graph, key=lambda s: len(words[s]))
    x0, y0 = positions[initial]
    ax.annotate(
        "",
        xy=(x0, y0 + box_height / 2 + 0.05),
        xytext=(x0, y0 + box_height / 2 + 0.72),
        arrowprops=dict(arrowstyle="-|>", lw=1.15, color="black"),
    )

    # Title/caption style.
    if paper_mode:
        ax.text(
            2.95,
            1.05,
            "Fig. 3. DIRM-observer  Obs(\u1d40G) of G.",
            ha="center",
            va="center",
            fontsize=13,
            family="serif",
            fontweight="bold",
        )
    else:
        ax.set_title(title, fontsize=13, family="serif", pad=12)

    # Frame and save.
    xs = [xy[0] for xy in positions.values()]
    ys = [xy[1] for xy in positions.values()]
    ax.set_xlim(min(xs) - 3.0, max(xs) + 3.0)
    ax.set_ylim(min(ys) - 1.6, max(ys) + 1.8)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# -----------------------------
# Main export API
# -----------------------------

def export_observer(observer: DIRMObserver, directory: str | Path, stem: str = "dirm_observer") -> Tuple[Path, Path]:
    """Write ``<stem>.txt`` and ``<stem>.png`` for one reachable observer."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    graph, words = observer.reachable()
    text_path = write_observer_text(graph, words, directory / f"{stem}.txt")
    image_path = draw_observer(graph, words, directory / f"{stem}.png")
    return text_path, image_path
