"""Readable state listing and compact diagram for the two comparison BTSs."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from dirm.plot.routing import rectangle_boundary_point

from .aic import AICBTS, Node, YState, ZState


def _estimate(states, mode: str) -> str:
    original = {state if mode == "high" else state[0] for state in states}
    return "{" + ",".join(str(state) for state in sorted(original, key=repr)) + "}"


def export_comparison(
    bts: AICBTS, directory: str | Path, stem: str
) -> Tuple[Path, Path]:
    """Export the complete graph and identify the AES-winning subgraph."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    result = bts.synthesize()
    ys = sorted((n for n in bts.graph if isinstance(n, YState)), key=repr)
    zs = sorted((n for n in bts.graph if isinstance(n, ZState)), key=repr)
    nodes = ys + zs
    ids: Dict[Node, str] = {
        node: f"{'Y' if isinstance(node, YState) else 'Z'}{index}"
        for group in (ys, zs)
        for index, node in enumerate(group)
    }
    lines = [
        f"Example 5 AIC/BTS: {bts.mode} operators",
        "Y --control pattern--> Z --observation--> Y",
        f"Initial: {ids[bts.initial]}",
        f"States: Y={len(ys)}, Z={len(zs)}",
        "Controllable: {" + ",".join(sorted(bts.controllable)) + "}",
        "Uncontrollable: {" + ",".join(sorted(bts.uncontrollable)) + "}",
        "Update observable: {" + ",".join(sorted(bts.observable)) + "}",
        f"AES initial winning: {result.initial_winning}",
        "Opacity is evaluated on the sole Z estimate; terminal states are allowed (uniform paper Remark V.2).",
        "",
        "States",
    ]
    for node in nodes:
        status = "AES" if node in result.winning else "removed"
        line = f"{ids[node]} [{status}] Q={_estimate(node.estimate, bts.mode)}"
        if isinstance(node, ZState):
            line += " gamma={" + ",".join(sorted(node.gamma)) + "}"
        lines.append(line)
    lines.extend(("", "Transitions"))
    for node in nodes:
        for edge in bts.graph[node]:
            lines.append(f"{ids[node]} --{edge.label}--> {ids[edge.target]}")
    lines.extend(("", "Winning control patterns"))
    for y in ys:
        if y in result.policy:
            patterns = sorted(result.policy[y], key=lambda p: (len(p), sorted(p)))
            lines.append(
                f"{ids[y]}: " + ", ".join("{" + ",".join(sorted(p)) + "}" for p in patterns)
            )
    lines.extend(("", "One MAX-SYNT supervisor (reachable Y-states)"))
    for y in ys:
        if y in result.supervisor:
            lines.append(
                f"{ids[y]}: {{" + ",".join(sorted(result.supervisor[y])) + "}"
            )
    text_path = directory / f"{stem}.txt"
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Match the existing supervisory figures: full state text in two columns,
    # colored by Y/Z type, with a red border for states removed from the AES.
    max_count = max(len(ys), len(zs))
    fig, ax = plt.subplots(figsize=(20, max(8, max_count * 0.9)))
    ax.set_axis_off()
    positions: Dict[Node, tuple[float, float]] = {}
    for x, layer in ((0.0, ys), (22.0, zs)):
        offset = (max_count - len(layer)) / 2
        for index, node in enumerate(layer):
            positions[node] = (x, 1.18 * (max_count - offset - index))
    widths = {YState: 12.8, ZState: 18.0}
    half_height = 0.47
    for source, edges in bts.graph.items():
        for edge in edges:
            x1, y1 = positions[source]
            x2, y2 = positions[edge.target]
            start = rectangle_boundary_point(
                (x1, y1), (x2, y2), widths[type(source)] / 2,
                half_height, margin=0.06,
            )
            end = rectangle_boundary_point(
                (x2, y2), (x1, y1), widths[type(edge.target)] / 2,
                half_height, margin=0.06,
            )
            ax.add_patch(FancyArrowPatch(
                start, end, arrowstyle="-|>", mutation_scale=16,
                linewidth=0.9, color="#424750", alpha=0.65,
                connectionstyle="arc3,rad=0.09" if isinstance(source, YState)
                else "arc3,rad=-0.09", zorder=1,
            ))
            ax.text(
                (start[0] + end[0]) / 2,
                (start[1] + end[1]) / 2 + 0.12,
                edge.label, fontsize=8.5, ha="center", va="bottom",
                family="monospace",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.86, pad=0.8),
                zorder=4,
            )
    for node in nodes:
        x, y = positions[node]
        is_y = isinstance(node, YState)
        face = "#e3e9ff" if is_y else "#def2e9"
        border = "#b00020" if node not in result.winning else "#26323b"
        width = widths[type(node)]
        ax.add_patch(FancyBboxPatch(
            (x - width / 2, y - half_height), width, half_height * 2,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor=face, edgecolor=border, linewidth=1.6, zorder=2,
        ))
        label = (
            f"{ids[node]}{' [INITIAL]' if node == bts.initial else ''}\n"
            f"Q={_estimate(node.estimate, bts.mode)}"
        )
        if isinstance(node, ZState):
            label += "\ngamma={" + ",".join(sorted(node.gamma)) + "}"
        ax.text(x, y, label, ha="center", va="center", fontsize=14,
                family="monospace", linespacing=1.15, zorder=3)
    header_y = 1.18 * max_count + 0.9
    ax.text(0, header_y, "Y: control state", ha="center", fontsize=14,
            fontweight="bold")
    ax.text(22, header_y, "Z: observation state", ha="center", fontsize=14,
            fontweight="bold")
    ax.set_xlim(-7.1, 31.6)
    ax.set_ylim(0, header_y + 1.0)
    ax.set_title(
        f"Example 5 {bts.mode} AIC/BTS  |  {len(nodes)} complete states"
        "  |  red border = removed from AES",
        fontsize=17, pad=20,
    )
    fig.tight_layout()
    image_path = directory / f"{stem}.png"
    fig.savefig(image_path, dpi=240, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return text_path, image_path
