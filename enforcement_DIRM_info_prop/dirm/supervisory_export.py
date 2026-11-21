"""TXT and PNG export for the observation-based I-J-L control structure."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Tuple

from .supervisory import (
    BTSEdge,
    BTSState,
    ControlPattern,
    SupervisoryDIRMBTS,
    SynthesisResult,
    IState,
    JState,
    LState,
)
from .plot.routing import rectangle_boundary_point


def _aug_key(state: tuple[object, bool]) -> tuple[str, int]:
    return repr(state[0]), int(state[1])


def _format_aug(state: tuple[object, bool]) -> str:
    return f"{state[0]}{'Y' if state[1] else 'N'}"


def _format_set(states: Iterable[tuple[object, bool]]) -> str:
    return "{" + ",".join(
        _format_aug(item) for item in sorted(frozenset(states), key=_aug_key)
    ) + "}"


def _format_control(gamma: ControlPattern) -> str:
    return "{" + ",".join(sorted(gamma)) + "}"


def _format_set_inline(states: Iterable[tuple[object, bool]]) -> str:
    """Format an augmented-state set for a self-contained transition line."""
    return "{" + ", ".join(
        _format_aug(item) for item in sorted(frozenset(states), key=_aug_key)
    ) + "}"


def _format_control_inline(gamma: ControlPattern) -> str:
    """Format a control pattern for a self-contained transition line."""
    return "{" + ", ".join(sorted(gamma)) + "}"


def _state_key(state: BTSState) -> tuple:
    if isinstance(state, IState):
        q_hat = tuple(_aug_key(item) for item in sorted(state.q_hat, key=_aug_key))
        q = tuple(_aug_key(item) for item in sorted(state.q, key=_aug_key))
        return 0, q_hat, q
    if isinstance(state, JState):
        q_hat = tuple(_aug_key(item) for item in sorted(state.q_hat, key=_aug_key))
        q = tuple(_aug_key(item) for item in sorted(state.q, key=_aug_key))
        return 1, tuple(sorted(state.gamma)), q_hat, q
    return (
        2,
        tuple(sorted(state.gamma)),
        tuple(_aug_key(item) for item in sorted(state.q_mid, key=_aug_key)),
    )


def _state_ids(graph: Mapping[BTSState, Tuple[BTSEdge, ...]]) -> Dict[BTSState, str]:
    result = {}
    for cls, prefix in ((IState, "I"), (JState, "J"), (LState, "L")):
        states = sorted((state for state in graph if isinstance(state, cls)), key=_state_key)
        result.update({state: f"{prefix}{index}" for index, state in enumerate(states)})
    return result


def _state_lines(state: BTSState) -> list[str]:
    lines = []
    if isinstance(state, (JState, LState)):
        lines.append(f"  gamma = {_format_control(state.gamma)}")
    if isinstance(state, LState):
        lines.append(f"  q_mid = {_format_set(state.q_mid)}")
    else:
        lines.append(f"  q_hat = {_format_set(state.q_hat)}")
        lines.append(f"  q     = {_format_set(state.q)}")
    return lines


def _edge_label(edge: BTSEdge) -> str:
    if edge.kind == "IJ":
        return f"gamma={_format_control(edge.gamma or frozenset())}"
    if edge.kind == "JL" and edge.release_language is not None:
        return str(edge.release_language)
    if edge.sigma is not None:
        return edge.sigma
    if edge.kind == "LI":
        return "epsilon"
    return edge.kind


def _display_edges(edges: Iterable[BTSEdge]) -> list[BTSEdge]:
    """Show identical observed edges once while retaining plant witnesses."""
    result = []
    seen = set()
    for edge in edges:
        key = (edge.kind, edge.target, _edge_label(edge))
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result


def _transition_state_text(state: BTSState, state_id: str) -> str:
    """Return a compact, complete state description for transition listings."""
    if isinstance(state, IState):
        return (
            f"{state_id}: {_format_set_inline(state.q_hat)}, "
            f"{_format_set_inline(state.q)}"
        )
    if isinstance(state, JState):
        return (
            f"{state_id}: {_format_set_inline(state.q_hat)}, "
            f"{_format_set_inline(state.q)}, "
            f"{_format_control_inline(state.gamma)}"
        )
    return (
        f"{state_id}: {_format_set_inline(state.q_mid)}, "
        f"{_format_control_inline(state.gamma)}"
    )


def supervisory_diagnostics(bts: SupervisoryDIRMBTS, result: SynthesisResult) -> str:
    """Use the same stable state IDs in TXT, figures, and console reports."""
    ids = _state_ids(bts.graph)
    secret_augmented = (q for q in bts.system.states if q[0] in bts.plant.secret_states)
    lines = [
        "State classification",
        "-" * 78,
        "DFA secret states [SECRET]: {" + ", ".join(
            str(q) for q in sorted(bts.plant.secret_states, key=repr)
        ) + "}",
        f"Augmented secret states [SECRET]: {_format_set_inline(secret_augmented)}",
        "Secret-revealing = J-state with a nonempty, entirely secret low-level estimate.",
        "Inconsistent = removed in later rounds by consistency conditions (i)-(iii).",
        "Round 0 also removes secret-only I/L estimates, as in the existing solver.",
    ]
    groups = (
        ("SECRET-REVEALING J states", result.secret_revealing_states),
        ("SECRET-ONLY I/L estimates (direct safety removal)",
         result.secret_only_states - result.secret_revealing_states),
        ("INCONSISTENT states (consistency pruning)", result.inconsistent_states),
    )
    for title, states in groups:
        ordered = sorted(states, key=_state_key)
        lines.append(f"{title} ({len(ordered)}): " + (", ".join(ids[s] for s in ordered) or "none"))
        for state in ordered:
            causes = sorted(result.blocked_successors.get(state, ()), key=_state_key)
            cause_text = "; removed successors: " + ", ".join(ids[q] for q in causes) if causes else ""
            lines.append(
                f"  {_transition_state_text(state, ids[state])}; "
                f"round={result.removal_rounds[state]}; {result.removal_reasons[state]}{cause_text}"
            )
    lines.append(f"Retained winning states ({len(result.winning_states)}): " + ", ".join(
        ids[state] for state in sorted(result.winning_states, key=_state_key)
    ))
    return "\n".join(lines)


def write_supervisory_text(
    bts: SupervisoryDIRMBTS, result: SynthesisResult, path: str | Path
) -> Path:
    """Write complete information states, policy, and transitions."""
    if not bts.graph:
        bts.construct()
    path = Path(path)
    ids = _state_ids(bts.graph)
    lines = [
        "Observation-based supervisory DIRM transition system",
        "=" * 78,
        f"Structure: {bts.structure}",
        f"Initial: {ids[bts.initial]}",
        f"Initial winning: {result.initial_winning}",
        f"Counts: {dict(bts.state_counts())}",
        f"Controllable: {_format_control(bts.controllable)}",
        f"Uncontrollable: {_format_control(bts.uncontrollable)}",
        f"Observable: {_format_control(bts.system.observable)}",
        f"Unobservable: {_format_control(bts.system.unobservable)}",
        f"Releasable: {_format_control(bts.system.releasable)}",
        (
            "Dominance reduction: "
            f"removed {bts.reduction_stats['control_edges']} control choices and "
            f"{bts.reduction_stats['states']} unreachable J/L states"
        ),
        "I/J contain q_hat and q only (no exact DFA state).",
        "Suffix N/Y denotes the augmented pending-release bit.",
        "J->L labels are released local high-level words (and a visible terminal event).",
        "The actual release-triggering plant event is retained separately as sigma.",
        "",
        "States",
        "-" * 78,
    ]
    lines[-2:-2] = supervisory_diagnostics(bts, result).splitlines() + [""]
    for state in sorted(bts.graph, key=_state_key):
        tags = ["winning" if state in result.winning_states else "losing"]
        if state in result.secret_revealing_states:
            tags.append("SECRET-REVEALING")
        elif state in result.inconsistent_states:
            tags.append("INCONSISTENT")
        elif state in result.secret_only_states:
            tags.append("SECRET-ONLY ESTIMATE")
        if state == bts.initial:
            tags.append("initial")
        lines.append(f"{ids[state]} [{', '.join(tags)}]")
        lines.extend(_state_lines(state))
        if state in result.removal_rounds:
            lines.append(f"  removal round = {result.removal_rounds[state]}")
            lines.append(f"  reason = {result.removal_reasons[state]}")
        if isinstance(state, IState):
            controls = sorted(result.policy.get(state, ()), key=lambda value: tuple(sorted(value)))
            lines.append(
                "  winning controls = "
                + ("; ".join(_format_control(item) for item in controls) if controls else "none")
            )
        lines.append("")

    lines.extend(("Transitions", "-" * 78))
    for source in sorted(bts.graph, key=lambda state: ids[state]):
        for edge in sorted(
            _display_edges(bts.graph[source]),
            key=lambda item: (_edge_label(item), ids[item.target]),
        ):
            lines.append(
                f"{_transition_state_text(source, ids[source])} "
                f"--{_edge_label(edge)}--> "
                f"{_transition_state_text(edge.target, ids[edge.target])}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def draw_supervisory_bts(
    bts: SupervisoryDIRMBTS, result: SynthesisResult, path: str | Path
) -> Path:
    """Draw the tripartite graph with every complete state inside its box."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch

    if not bts.graph:
        bts.construct()
    path = Path(path)
    ids = _state_ids(bts.graph)
    layers = [
        sorted((s for s in bts.graph if isinstance(s, IState)), key=_state_key),
        sorted((s for s in bts.graph if isinstance(s, JState)), key=_state_key),
        sorted((s for s in bts.graph if isinstance(s, LState)), key=_state_key),
    ]
    max_count = max(map(len, layers), default=1)
    fig, ax = plt.subplots(figsize=(34, max(10, max_count * 0.75)))
    ax.set_axis_off()
    positions = {}
    x_values = (0.0, 12.0, 26.0)
    for x, states in zip(x_values, layers):
        offset = (max_count - len(states)) / 2
        for index, state in enumerate(states):
            positions[state] = (x, 1.2 * (max_count - offset - index))

    colors = {IState: "#d9e8ff", JState: "#dcf7df", LState: "#fff0c7"}
    node_widths = {IState: 8.4, JState: 10.4, LState: 10.4}

    def complete_state_text(state: BTSState) -> str:
        if isinstance(state, IState):
            return (
                "I-state (control)\n"
                f"(q_hat={_format_set(state.q_hat)}, q={_format_set(state.q)})"
            )
        if isinstance(state, JState):
            return (
                "J-state (observation)\n"
                f"(q_hat={_format_set(state.q_hat)}, q={_format_set(state.q)}, "
                f"gamma={_format_control(state.gamma)})"
            )
        return (
            "L-state (release / pre-closure)\n"
            f"(q_mid={_format_set(state.q_mid)}, "
            f"gamma={_format_control(state.gamma)})"
        )

    for state, (x, y) in positions.items():
        face, border, style, status = colors[type(state)], "#222222", "-", ""
        if state in result.secret_revealing_states:
            face, border, status = "#ffe1e1", "#c62828", " [SECRET-REVEALING]"
        elif state in result.inconsistent_states:
            face, border, style = "#fff0d6", "#c46b00", "--"
            status = f" [INCONSISTENT r{result.removal_rounds[state]}]"
        elif state in result.secret_only_states:
            face, border, style, status = "#f3e8ff", "#7e22ce", ":", " [SECRET-ONLY ESTIMATE]"
        width = node_widths[type(state)]
        box = FancyBboxPatch(
            (x - width / 2, y - 0.43), width, 0.86,
            boxstyle="round,pad=0.06,rounding_size=0.12",
            facecolor=face, edgecolor=border, linestyle=style,
            linewidth=2.2 if status else 1.7, zorder=3,
        )
        ax.add_patch(box)
        initial = " [INITIAL]" if state == bts.initial else ""
        ax.text(
            x, y, ids[state] + status + initial + "\n" + complete_state_text(state),
            ha="center", va="center", fontsize=6.2, family="monospace",
            linespacing=1.18, zorder=4,
        )

    for source, edges in bts.graph.items():
        for edge in _display_edges(edges):
            x1, y1 = positions[source]
            x2, y2 = positions[edge.target]
            source_half_width = node_widths[type(source)] / 2
            target_half_width = node_widths[type(edge.target)] / 2
            start = rectangle_boundary_point(
                (x1, y1), (x2, y2), source_half_width, 0.43, margin=0.08
            )
            end = rectangle_boundary_point(
                (x2, y2), (x1, y1), target_half_width, 0.43, margin=0.08
            )
            # L -> I wraps back to the left; other edges move right.
            connection = "arc3,rad=0.18" if x2 <= x1 else "arc3,rad=0.04"
            arrow = FancyArrowPatch(
                start, end,
                arrowstyle="-|>", mutation_scale=20, linewidth=1.15,
                color="#303030", connectionstyle=connection,
                shrinkA=0, shrinkB=0, zorder=2.5,
            )
            ax.add_patch(arrow)
            ax.text(
                (x1 + x2) / 2, (y1 + y2) / 2 + 0.10,
                _edge_label(edge), fontsize=5.2, ha="center", va="bottom",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.88), zorder=5,
            )

    header_y = 1.2 * max_count + 0.9
    ax.text(0, header_y, "I: control state", ha="center", fontsize=13, fontweight="bold")
    ax.text(12, header_y, "J: observation state", ha="center", fontsize=13, fontweight="bold")
    ax.text(26, header_y, "L: release state", ha="center", fontsize=13, fontweight="bold")
    ax.set_xlim(-5, 32)
    ax.set_ylim(0, header_y + 0.8)
    ax.set_title(
        f"DIRM supervisory control: {bts.structure}\n"
        f"{len(bts.graph)} information states; classifications shown before pruning",
        fontsize=18,
    )
    ax.legend(handles=[
        Patch(facecolor="#ffe1e1", edgecolor="#c62828", label="Secret-revealing J"),
        Patch(facecolor="#fff0d6", edgecolor="#c46b00", linestyle="--", label="Inconsistent (round shown)"),
        Patch(facecolor="#f3e8ff", edgecolor="#7e22ce", linestyle=":", label="Secret-only I/L estimate"),
        Patch(facecolor="white", edgecolor="#222222", label="Retained / winning"),
    ], loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=4, fontsize=10)
    fig.tight_layout()
    if path.exists():
        path.unlink()
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def export_supervisory_bts(
    bts: SupervisoryDIRMBTS,
    directory: str | Path,
    stem: str = "dirm_supervisory_bts",
    *,
    result: Optional[SynthesisResult] = None,
) -> Tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not bts.graph:
        bts.construct()
    if result is None:
        result = bts.synthesize()
    return (
        write_supervisory_text(bts, result, directory / f"{stem}.txt"),
        draw_supervisory_bts(bts, result, directory / f"{stem}.png"),
    )
