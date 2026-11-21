"""Readable TXT and PNG export for a DIRM augmented transition system."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from .augmented import AugmentedDFA, AugmentedState
from .plot.routing import rectangle_boundary_point


def _state_key(state: AugmentedState) -> tuple[str, int]:
    return repr(state[0]), int(state[1])


def _format_state(state: AugmentedState) -> str:
    return f"{state[0]}{'Y' if state[1] else 'N'}"


def _edge_label(
    source: AugmentedState,
    target: AugmentedState,
    events: Iterable[str],
) -> str:
    """Return an unambiguous label for an augmented transition.

    Cross-layer arcs are long and can intersect other arcs.  Include their
    endpoints so a nearby label cannot be mistaken for the event on a crossing
    edge (for example ``3Y --a,b--> 4N`` versus ``1N --h2--> 7Y``).
    """
    event_text = ", ".join(sorted(events))
    if source[1] != target[1]:
        return f"{_format_state(source)} --{event_text}--> {_format_state(target)}"
    return event_text


def _state_space(
    system: AugmentedDFA, include_unreachable: bool
) -> frozenset[AugmentedState]:
    return system.product_states if include_unreachable else system.states


def _transitions(
    system: AugmentedDFA, states: Iterable[AugmentedState],
) -> Tuple[Tuple[AugmentedState, str, AugmentedState], ...]:
    state_space = frozenset(states)
    return tuple(
        (source, event, target)
        for source in sorted(state_space, key=_state_key)
        for event in sorted(system.plant.alphabet)
        if (target := system.step(source, event)) is not None and target in state_space
    )


def write_augmented_text(
    system: AugmentedDFA,
    path: str | Path,
    *,
    include_unreachable: bool = False,
) -> Path:
    """Write the reachable system or, on request, the full product system."""
    path = Path(path)
    states = _state_space(system, include_unreachable)
    transitions = _transitions(system, states)
    variant = "full product Q x {N,Y}" if include_unreachable else "BFS reachable from initial"
    lines = [
        "DIRM augmented transition system",
        "=" * 80,
        f"State space: {variant}",
        f"Initial: {_format_state(system.initial)}",
        f"Counts: states={len(states)}, reachable={len(states & system.states)}, "
        f"transitions={len(transitions)}",
        f"Observable: {{{','.join(sorted(system.observable))}}}",
        f"Unobservable: {{{','.join(sorted(system.unobservable))}}}",
        f"Releasable: {{{','.join(sorted(system.releasable))}}}",
        f"Release states: {{{','.join(map(str, sorted(system.release_states, key=repr)))}}}",
        "Secret augmented states [SECRET]: {" + ",".join(
            _format_state(q) for q in sorted(states, key=_state_key)
            if q[0] in system.plant.secret_states
        ) + "}",
        "Suffix: N=no pending releasable information; Y=pending information",
        "",
        "States",
        "-" * 80,
    ]
    for state in sorted(states, key=_state_key):
        tags = []
        if state == system.initial:
            tags.append("initial")
        if system.is_true_release(state):
            tags.append("true release")
        if state[0] in system.plant.secret_states:
            tags.append("SECRET")
        if state not in system.states:
            tags.append("unreachable")
        suffix = f"  [{', '.join(tags)}]" if tags else ""
        lines.append(f"{_format_state(state)}{suffix}")

    lines.extend(("", "Transitions", "-" * 80))
    for source, event, target in transitions:
        lines.append(f"{_format_state(source)} --{event}--> {_format_state(target)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _positions(
    system: AugmentedDFA, states: Iterable[AugmentedState]
) -> Dict[AugmentedState, tuple[float, float]]:
    ordered = sorted(system.plant.states, key=repr)
    state_space = frozenset(states)
    return {
        (state, pending): (10.0 * int(pending), -2.0 * index)
        for index, state in enumerate(ordered)
        for pending in (False, True)
        if (state, pending) in state_space
    }


def draw_augmented_system(
    system: AugmentedDFA,
    path: str | Path,
    *,
    include_unreachable: bool = False,
) -> Path:
    """Draw a large paper-style graph with readable event-labelled arcs."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
    from matplotlib.lines import Line2D

    path = Path(path)
    states = _state_space(system, include_unreachable)
    transitions = _transitions(system, states)
    positions = _positions(system, states)
    grouped: Mapping[tuple[AugmentedState, AugmentedState], list[str]] = defaultdict(list)
    for source, event, target in transitions:
        grouped[(source, target)].append(event)

    fig, ax = plt.subplots(figsize=(24.0, 22.0))
    ax.set_axis_off()
    box_width, box_height = 2.3, 0.84
    boxes: Dict[AugmentedState, FancyBboxPatch] = {}

    # Draw routed arcs first. Same-layer arcs bend outward; cross-layer arcs
    # alternate curvature so labels do not sit on top of one another.
    cross_index = 0
    for (source, target), events in sorted(
        grouped.items(), key=lambda item: (_state_key(item[0][0]), _state_key(item[0][1]))
    ):
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        if source == target:
            start = (x1 + box_width * 0.30, y1 - box_height / 2 - 0.07)
            end = (x1 - box_width * 0.30, y1 - box_height / 2 - 0.07)
            rad = -1.15
        elif source[1] == target[1]:
            distance = abs(y2 - y1) / 2.0
            direction = -1.0 if not source[1] else 1.0
            rad = direction * min(0.18 + 0.055 * distance, 0.58)
        else:
            rad = (-0.10 if cross_index % 2 else 0.10)
            cross_index += 1
        if source != target:
            start = rectangle_boundary_point(
                (x1, y1), (x2, y2), box_width / 2, box_height / 2, margin=0.07
            )
            end = rectangle_boundary_point(
                (x2, y2), (x1, y1), box_width / 2, box_height / 2, margin=0.07
            )
        arrow = FancyArrowPatch(
            start, end,
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>",
            mutation_scale=23,
            linewidth=2.0,
            color="#111111",
            alpha=0.94,
            shrinkA=0,
            shrinkB=0,
            zorder=2.5,
        )
        ax.add_patch(arrow)
        if source == target:
            label_x, label_y = x1, y1 - box_height * 1.25
        else:
            dx, dy = x2 - x1, y2 - y1
            length = max((dx * dx + dy * dy) ** 0.5, 1.0)
            label_x = (x1 + x2) / 2.0 - dy / length * rad * length * 0.38
            label_y = (y1 + y2) / 2.0 + dx / length * rad * length * 0.38
        ax.text(
            label_x, label_y, _edge_label(source, target, events),
            ha="center", va="center", fontsize=8.5, family="serif",
            bbox=dict(
                boxstyle="round,pad=0.20", fc="white", ec="#777777",
                linewidth=0.55, alpha=0.96,
            ),
            zorder=3,
        )

    for state in sorted(states, key=_state_key):
        x, y = positions[state]
        if system.is_true_release(state):
            face = "#e8f3df"
        elif state[1]:
            face = "#fff4d6"
        else:
            face = "white"
        secret = state[0] in system.plant.secret_states
        if secret and not system.is_true_release(state):
            face = "#ffe1e1"
        border = "#c62828" if secret else ("#999999" if state not in system.states else "black")
        box = FancyBboxPatch(
            (x - box_width / 2, y - box_height / 2),
            box_width, box_height,
            boxstyle="round,pad=0.12,rounding_size=0.14",
            linewidth=2.8 if secret else (2.6 if state == system.initial else 1.3),
            linestyle="--" if state not in system.states else "-",
            facecolor=face, edgecolor=border, zorder=3,
        )
        boxes[state] = box
        ax.add_patch(box)
        tags = []
        if system.is_true_release(state):
            tags.append("release")
        if secret:
            tags.append("SECRET")
        if state not in system.states:
            tags.append("unreachable")
        label = _format_state(state)
        if tags:
            label += "\n" + ", ".join(tags)
        ax.text(x, y, label, ha="center", va="center", fontsize=10.5,
                family="serif", fontweight="bold", color=border if secret else "black", zorder=4)

    # Match the observer figure's explicit incoming initial arrow.
    x0, y0 = positions[system.initial]
    ax.annotate(
        "", xy=(x0, y0 + box_height / 2 + 0.04),
        xytext=(x0, y0 + box_height / 2 + 0.9),
        arrowprops=dict(arrowstyle="-|>", lw=1.5, color="black"), zorder=5,
    )

    ax.text(0.0, 1.0, "N: no pending information", ha="center", fontsize=14,
            family="serif", fontweight="bold")
    ax.text(10.0, 1.0, "Y: pending information", ha="center", fontsize=14,
            family="serif", fontweight="bold")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="s", color="none", markerfacecolor="white", markeredgecolor="black", markersize=10, label="N state"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor="#fff4d6", markeredgecolor="black", markersize=10, label="Y state"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor="#e8f3df", markeredgecolor="black", markersize=10, label="true release state"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor="#ffe1e1", markeredgecolor="#c62828", markersize=10, label="SECRET (red border; may also release)"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor="white", markeredgecolor="#999999", markersize=10, label="unreachable"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.015),
        ncol=3,
        fontsize=9,
        framealpha=0.95,
    )
    ax.set_title(
        f"DIRM augmented transition system\n"
        f"{'full product Q x {N,Y}' if include_unreachable else f'BFS reachable from {_format_state(system.initial)}'}\n"
        f"{len(states)} states, {len(transitions)} lifted DFA transitions "
        f"(UR/NX and control are not applied)",
        fontsize=17,
        pad=18,
    )
    ax.set_xlim(-6.5, 16.5)
    ys = [point[1] for point in positions.values()]
    ax.set_ylim(min(ys) - 1.5, max(ys) + 2.1)
    fig.tight_layout()
    if path.exists():
        path.unlink()
    fig.savefig(path, dpi=240, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def export_augmented_system(
    system: AugmentedDFA,
    directory: str | Path,
    stem: str = "dirm_augmented_system",
    *,
    include_unreachable: bool = False,
) -> Tuple[Path, Path]:
    """Export the BFS-reachable system or the legacy full product system."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    text_path = write_augmented_text(
        system, directory / f"{stem}.txt", include_unreachable=include_unreachable
    )
    image_path = draw_augmented_system(
        system, directory / f"{stem}.png", include_unreachable=include_unreachable
    )
    return text_path, image_path


def write_augmented_comparison(system: AugmentedDFA, path: str | Path) -> Path:
    """Record how the BFS system corresponds to the legacy product system."""
    path = Path(path)
    product_transitions = frozenset(_transitions(system, system.product_states))
    reachable_transitions = frozenset(_transitions(system, system.states))
    restricted_product = frozenset(
        transition for transition in product_transitions if transition[0] in system.states
    )
    removed_states = system.product_states - system.states
    removed_transitions = product_transitions - reachable_transitions
    corresponding = (
        system.states <= system.product_states
        and reachable_transitions == restricted_product
        and all(target in system.states for _, _, target in reachable_transitions)
    )
    lines = [
        "DIRM augmented state-space comparison",
        "=" * 80,
        f"Legacy product states: {len(system.product_states)}",
        f"BFS reachable states: {len(system.states)}",
        f"Removed unreachable states: {len(removed_states)}",
        f"Legacy product transitions: {len(product_transitions)}",
        f"BFS reachable transitions: {len(reachable_transitions)}",
        f"Removed unreachable transitions: {len(removed_transitions)}",
        f"Reachable subsystem corresponds to product restriction: {corresponding}",
        "",
        "Removed states",
        "-" * 80,
        *(_format_state(state) for state in sorted(removed_states, key=_state_key)),
        "",
        "Removed transitions",
        "-" * 80,
        *(
            f"{_format_state(source)} --{event}--> {_format_state(target)}"
            for source, event, target in sorted(
                removed_transitions,
                key=lambda item: (_state_key(item[0]), item[1], _state_key(item[2])),
            )
        ),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
