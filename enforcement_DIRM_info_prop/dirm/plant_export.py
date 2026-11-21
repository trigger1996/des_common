"""TXT and PNG export for the original (unaugmented) DFA plants."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from .dfa import DFA, State
from .plot.routing import (
    circle_boundary_point, draw_routed_arrow, rectangle_boundary_point,
)


def _state_key(state: State) -> str:
    return repr(state)


def _format_state(state: State) -> str:
    return f"q_{state}"


def _grouped_transitions(
    plant: DFA,
) -> Mapping[tuple[State, State], list[str]]:
    grouped: Dict[tuple[State, State], list[str]] = defaultdict(list)
    for (source, event), target in plant.transitions.items():
        grouped[(source, target)].append(event)
    return grouped


def write_plant_text(plant: DFA, path: str | Path) -> Path:
    """Write the complete original DFA without DIRM augmentation."""
    path = Path(path)
    lines = [
        "Original DFA plant",
        "=" * 72,
        f"Initial: {_format_state(plant.initial)}",
        f"States: {len(plant.states)}",
        f"Transitions: {len(plant.transitions)}",
        f"Alphabet: {{{','.join(sorted(plant.alphabet))}}}",
        "Secret states: {"
        + ",".join(_format_state(state) for state in sorted(plant.secret_states, key=_state_key))
        + "}",
        "",
        "States ([SECRET] highlights secret DFA states)",
        "-" * 72,
    ]
    for state in sorted(plant.states, key=_state_key):
        tags = []
        if state == plant.initial:
            tags.append("initial")
        if state in plant.secret_states:
            tags.append("SECRET")
        lines.append(_format_state(state) + (f" [{', '.join(tags)}]" if tags else ""))
    lines.extend(("", "Transitions", "-" * 72))
    for (source, target), events in sorted(
        _grouped_transitions(plant).items(),
        key=lambda item: (_state_key(item[0][0]), _state_key(item[0][1])),
    ):
        lines.append(
            f"{_format_state(source)} --{','.join(sorted(events))}--> "
            f"{_format_state(target)}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _example_3_positions() -> Dict[State, tuple[float, float]]:
    """Two-column layout for project Example 3 (Automatica Fig. 2)."""
    return {
        0: (0.0, 0.0), 1: (6.4, 0.0),
        2: (0.0, -1.55), 3: (6.4, -1.55),
        4: (0.0, -3.10), 5: (6.4, -3.10),
        6: (0.0, -4.65), 7: (6.4, -4.65),
        8: (0.0, -6.20), 9: (0.0, -8.0),
    }


def _example_4_positions() -> Dict[State, tuple[float, float]]:
    """Compact two-branch layout derived from project Example 3."""
    return {
        0: (3.2, 0.0),
        1: (0.0, -2.0), 2: (6.4, -2.0),
        3: (0.0, -4.0), 4: (6.4, -4.0),
        5: (0.0, -6.0), 6: (3.2, -8.0),
    }


def _example_5_positions() -> Dict[State, tuple[float, float]]:
    """Two separate Fig. 1 branches with their final o edges aligned."""
    return {
        0: (3.5, 2.0),
        1: (0.0, 0.0), 2: (0.0, -2.0),
        3: (0.0, -4.0), 4: (0.0, -6.0),
        5: (7.0, 0.0), 6: (7.0, -1.5),
        7: (7.0, -3.0), 8: (7.0, -4.5),
        9: (7.0, -6.0),
    }


def _example_6_positions() -> Dict[State, tuple[float, float]]:
    """Two observation branches with a releasable h-cycle between them."""
    return {
        0: (-6.0, 0.0), 1: (-3.0, 0.0),
        2: (0.0, 1.6), 3: (0.0, -1.6),
        4: (3.0, 1.6), 5: (3.0, -1.6),
    }


def _user_example_positions() -> Dict[State, tuple[float, float]]:
    """Layout matching ScreenShot_2026-10-09_163459_282.png."""
    return {
        "0": (6.0, 2.0),
        "1": (6.0, 0.0),
        "2": (3.45, 0.55),
        "3": (1.35, -1.05),
        "4": (1.35, 0.55),
        "5": (-0.75, -1.05),
        "6": (3.45, 2.0),
    }


def _example_2_positions() -> Dict[State, tuple[float, float]]:
    """Seven-state layout for the compact Example 2."""
    return _user_example_positions()


def _generic_positions(states: Iterable[State]) -> Dict[State, tuple[float, float]]:
    ordered = sorted(states, key=_state_key)
    return {
        state: (float(index % 5) * 2.4, -float(index // 5) * 2.0)
        for index, state in enumerate(ordered)
    }


def _positions(plant: DFA, layout: str) -> Dict[State, tuple[float, float]]:
    if layout in {"example_3", "framework_figure_2"}:
        candidate = _example_3_positions()
    elif layout == "example_4":
        candidate = _example_4_positions()
    elif layout == "example_5":
        candidate = _example_5_positions()
    elif layout == "example_6":
        candidate = _example_6_positions()
    elif layout in {"example_1", "user_example_1"}:
        candidate = _user_example_positions()
    elif layout == "example_2":
        candidate = _example_2_positions()
    elif layout == "generic":
        candidate = _generic_positions(plant.states)
    else:
        raise ValueError(f"unknown plant layout: {layout}")
    if set(candidate) != set(plant.states):
        raise ValueError(f"layout {layout!r} does not match the plant state set")
    return candidate


def draw_plant(
    plant: DFA,
    path: str | Path,
    *,
    layout: str = "generic",
    release_states: Iterable[State] = (),
) -> Path:
    """Draw the plant, using square nodes for DIRM release states."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Rectangle, Patch

    path = Path(path)
    releases = frozenset(release_states)
    if not releases <= plant.states:
        raise ValueError("release states must belong to the plant")
    positions = _positions(plant, layout)
    grouped = _grouped_transitions(plant)
    fig_size = (14.5, 9.0) if layout in {"example_3", "example_4", "example_5", "framework_figure_2"} else (12.5, 7.5)
    fig, ax = plt.subplots(figsize=fig_size)
    ax.set_axis_off()
    radius = 0.34
    square_half_side = 0.42

    def boundary(state: State, toward: State) -> tuple[float, float]:
        center = positions[state]
        destination = positions[toward]
        if state in releases:
            return rectangle_boundary_point(
                center, destination, square_half_side, square_half_side,
                margin=0.075,
            )
        return circle_boundary_point(center, destination, radius, margin=0.075)

    for edge_index, ((source, target), events) in enumerate(sorted(
        grouped.items(),
        key=lambda item: (_state_key(item[0][0]), _state_key(item[0][1])),
    )):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        if layout in {"example_3", "framework_figure_2"} and (source, target) == (0, 8):
            # The direct vertical chord would pass through states 2, 4, and 6.
            side_x = min(x for x, _ in positions.values()) - 1.05
            start = circle_boundary_point((x1, y1), (side_x, y1), radius, margin=0.075)
            end = circle_boundary_point((x2, y2), (side_x, y2), radius, margin=0.075)
            draw_routed_arrow(
                ax, (start, (side_x, y1), (side_x, y2), end),
                color="#111111", linewidth=1.7, mutation_scale=22,
                zorder=3.5,
            )
            ax.text(
                side_x, (y1 + y2) / 2, ", ".join(sorted(events)),
                ha="center", va="center", fontsize=13, family="serif",
                style="italic",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.96, pad=1.2),
                zorder=4.5,
            )
            continue
        if source == target:
            node_half_height = square_half_side if source in releases else radius
            start = (x1 + node_half_height * 0.58, y1 - node_half_height - 0.08)
            end = (x1 - node_half_height * 0.58, y1 - node_half_height - 0.08)
            rad = -1.25
            label_x, label_y = x1, y1 - 1.0
        else:
            # Anchor to each node's actual shape, outside its drawn border.
            start = boundary(source, target)
            end = boundary(target, source)
            # Opposite-direction and long diagonal arcs are separated gently.
            reverse = (target, source) in grouped
            rad = (0.18 if _state_key(source) < _state_key(target) else -0.18) if reverse else 0.0
            if layout == "example_2" and {source, target} == {"4", "6"}:
                # The two opposite edges need opposite sides of the chord.
                rad = 0.24
            if layout == "example_6" and {source, target} == {2, 3}:
                rad = 0.28
            if layout in {"example_3", "framework_figure_2"} and {source, target} == {3, 9}:
                rad = 0.12
            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2 + (0.30 if abs(x2 - x1) > 0.2 else 0.0)
            if layout == "example_2" and {source, target} == {"4", "6"}:
                dx, dy = x2 - x1, y2 - y1
                length = (dx * dx + dy * dy) ** 0.5
                label_x += -dy / length * 0.52
                label_y += dx / length * 0.52
            if layout == "example_6" and {source, target} == {2, 3}:
                label_x += 0.45 if source == 2 else -0.45
        arrow = FancyArrowPatch(
            start, end,
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>", mutation_scale=22,
            linewidth=1.7, color="#111111",
            shrinkA=0, shrinkB=0, zorder=3.5,
        )
        ax.add_patch(arrow)
        ax.text(
            label_x, label_y, ", ".join(sorted(events)),
            ha="center", va="center", fontsize=13, family="serif", style="italic",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.88, pad=1.2),
            zorder=4.5,
        )

    for state in sorted(plant.states, key=_state_key):
        x, y = positions[state]
        secret = state in plant.secret_states
        edge_color = "#d94a44" if secret else "#111111"
        face_color = "#ffe1e1" if secret else "white"
        if state in releases:
            ax.add_patch(Rectangle(
                (x - square_half_side, y - square_half_side),
                2 * square_half_side, 2 * square_half_side,
                facecolor=face_color, edgecolor=edge_color,
                linewidth=1.8, zorder=3,
            ))
            if secret:
                inset = 0.06
                ax.add_patch(Rectangle(
                    (x - square_half_side + inset, y - square_half_side + inset),
                    2 * (square_half_side - inset), 2 * (square_half_side - inset),
                    fill=False, edgecolor=edge_color,
                    linewidth=1.2, zorder=3,
                ))
        else:
            ax.add_patch(Circle(
                (x, y), radius, facecolor=face_color, edgecolor=edge_color,
                linewidth=1.8, zorder=3,
            ))
            if secret:
                ax.add_patch(Circle(
                    (x, y), radius * 0.82, fill=False, edgecolor=edge_color,
                    linewidth=1.2, zorder=3,
                ))
        ax.text(
            x, y, f"$q_{{{state}}}$", ha="center", va="center",
            fontsize=15, family="serif", color=edge_color if secret else "black",
            zorder=4,
        )

    x0, y0 = positions[plant.initial]
    initial_half_height = square_half_side if plant.initial in releases else radius
    ax.annotate(
        "", xy=(x0, y0 + initial_half_height + 0.075),
        xytext=(x0, y0 + initial_half_height + 0.78),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="black"), zorder=5,
    )
    xs = [point[0] for point in positions.values()]
    ys = [point[1] for point in positions.values()]
    ax.set_xlim(min(xs) - 1.6, max(xs) + 1.6)
    ax.set_ylim(min(ys) - 1.5, max(ys) + 1.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("Original DFA plant", fontsize=17, family="serif", pad=16)
    ax.legend(handles=[
        Patch(facecolor="#ffe1e1", edgecolor="#d94a44", label="Secret DFA state (double border)"),
        Patch(facecolor="white", edgecolor="black", label="Square = release state"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2)
    fig.tight_layout()
    if path.exists():
        path.unlink()
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def export_plant(
    plant: DFA,
    directory: str | Path,
    stem: str = "dirm_original_plant",
    *,
    layout: str = "generic",
    release_states: Iterable[State] = (),
) -> Tuple[Path, Path]:
    """Write a TXT listing and PNG drawing for an original DFA plant."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return (
        write_plant_text(plant, directory / f"{stem}.txt"),
        draw_plant(
            plant, directory / f"{stem}.png", layout=layout,
            release_states=release_states,
        ),
    )
