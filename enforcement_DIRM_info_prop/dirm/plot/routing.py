"""Small Matplotlib helpers for explicit multi-bend transition arrows."""

from __future__ import annotations

from typing import Iterable, Tuple


Point = Tuple[float, float]


def rectangle_boundary_point(
    center: Point,
    toward: Point,
    half_width: float,
    half_height: float,
    *,
    margin: float = 0.0,
) -> Point:
    """Return where a center-to-center edge meets a rectangle boundary.

    Matplotlib's shrink values use display points, while our node sizes use
    data coordinates. Explicit anchors keep arrowheads outside nodes at every
    output size and DPI.
    """
    dx = toward[0] - center[0]
    dy = toward[1] - center[1]
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        raise ValueError("center and toward must be different points")
    sx = (half_width + margin) / abs(dx) if abs(dx) >= 1e-12 else float("inf")
    sy = (half_height + margin) / abs(dy) if abs(dy) >= 1e-12 else float("inf")
    scale = min(sx, sy)
    return center[0] + dx * scale, center[1] + dy * scale


def circle_boundary_point(
    center: Point,
    toward: Point,
    radius: float,
    *,
    margin: float = 0.0,
) -> Point:
    """Return the radial anchor for an edge meeting a circular node."""
    dx = toward[0] - center[0]
    dy = toward[1] - center[1]
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-12:
        raise ValueError("center and toward must be different points")
    scale = (radius + margin) / length
    return center[0] + dx * scale, center[1] + dy * scale


def draw_polyline(
    ax,
    points: Iterable[Point],
    *,
    color: str = "#202020",
    linewidth: float = 1.2,
    alpha: float = 1.0,
    zorder: float = 2,
):
    """Draw a non-directed polyline through all supplied bend points."""
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch

    vertices = tuple(points)
    if len(vertices) < 2:
        raise ValueError("a routed line needs at least two points")
    path = Path(vertices, [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1))
    patch = PathPatch(
        path, fill=False, color=color, linewidth=linewidth,
        alpha=alpha, capstyle="round", joinstyle="round", zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def draw_routed_arrow(
    ax,
    points: Iterable[Point],
    *,
    color: str = "#202020",
    linewidth: float = 1.2,
    mutation_scale: float = 12.0,
    alpha: float = 1.0,
    zorder: float = 2,
):
    """Draw an arrow that follows an explicit orthogonal/polyline route."""
    from matplotlib.path import Path
    from matplotlib.patches import FancyArrowPatch

    vertices = tuple(points)
    if len(vertices) < 2:
        raise ValueError("a routed arrow needs at least two points")
    path = Path(vertices, [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1))
    patch = FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=linewidth,
        color=color,
        alpha=alpha,
        capstyle="round",
        joinstyle="round",
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch
