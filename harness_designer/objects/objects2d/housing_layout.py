# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Automatic housing placement for the 2D schematic editor.

Arranges every housing in the project around the border of one shared
rectangle, each rotated so its pin edge faces the interior -- wires
connect between housings, so keeping the whole formation's pin edges
facing inward keeps wire routing inside the open middle instead of
tangled around the outside. The highest-cavity-count housings anchor the
left/right sides; if one side would end up badly lopsided, housings are
moved from a "catch-up" pool (3rd-highest cavity count downward) onto the
smaller side until the two are close, without ever letting the catching-up
side exceed the other. Everything left over is split between the top and
bottom edges, greedily balanced by total cavity count.

Single entry point: :func:`recompute_layout`, called after a housing is
added (see ``handlers/housing_handler.py``). A no-op when
``Config.editor2d.layout.auto_layout_enabled`` is ``False``.
"""

from typing import TYPE_CHECKING

from ... import config as _config

if TYPE_CHECKING:
    from .. import project as _project
    from .. import housing as _housing_obj


Config = _config.Config.editor2d


def _cavity_count(housing: "_housing_obj.Housing") -> int:
    return len([c for c in housing.db_obj.cavities if c is not None])


def _cavity_extent(housing: "_housing_obj.Housing") -> float:
    """This housing's along-the-edge (cavity-axis) extent -- see
    ``objects2d/housing.py``'s ``Housing._compute_cavity_extent``, reused
    directly here rather than recomputed so there's one source of truth.
    """
    return housing.obj2d._cavity_extent  # NOQA


def _text_extent(housing: "_housing_obj.Housing") -> float:
    """This housing's perpendicular (text-axis) extent -- fixed at
    ``Config.editor2d.housing.width``, see
    ``objects2d/housing.py``'s ``Housing._recompute``.
    """
    return housing.obj2d._text_extent  # NOQA


def _apply_placement(housing: "_housing_obj.Housing", x: float, z: float, angle_deg: float) -> None:
    """Write *x*/*z* to ``position2d`` and *angle_deg* to ``angle2d.y`` --
    the same bound-callback write path ``Housing2D.move_to`` already uses,
    so this persists immediately and refreshes the canvas. ``.y`` (not
    ``.z``) because that's the axis a Y=0-flat 2D primitive must rotate
    about to stay flat -- this is the one place that decides the axis
    (see ``objects2d/base2d.py``'s ``_render_geometry``, which just uses
    ``angle2d``'s own native quaternion with no reinterpretation).
    Cavity/terminal-row/label positions need no cascade -- they're
    computed procedurally from the housing's own live position every
    frame.
    """
    position = housing.db_obj.position2d
    with position:
        position.x = x
        position.z = z

    housing.db_obj.angle2d.y = angle_deg


def _assign_sides(housings: list) -> "tuple[list, list, list]":
    """Split *housings* (already sorted by cavity count, descending) into
    ``(left, right, remaining)``.

    The single highest-cavity-count housing anchors the right side, the
    second-highest anchors the left (arbitrary but fixed choice -- see
    :func:`_place_column`, both sides use the same placement logic mirrored
    by ``x_sign``). If one side is under half the other's total, housings
    are pulled one at a time from *remaining* (still highest-to-lowest) onto
    the smaller side -- but never past the point where the smaller side's
    total would exceed the larger side's, and never past a <25% relative
    difference.
    """
    right = [housings[0]]
    left = [housings[1]] if len(housings) > 1 else []
    remaining = list(housings[2:])

    right_total = _cavity_count(housings[0])
    left_total = _cavity_count(housings[1]) if left else 0

    if left_total <= right_total:
        small, small_total = left, left_total
        large_total = right_total
    else:
        small, small_total = right, right_total
        large_total = left_total

    if large_total > 0 and small_total < 0.5 * large_total:
        while remaining and (large_total - small_total) / large_total >= 0.25:
            candidate = remaining[0]
            candidate_count = _cavity_count(candidate)

            if small_total + candidate_count > large_total:
                break

            remaining.pop(0)
            small.append(candidate)
            small_total += candidate_count

    return left, right, remaining


def _assign_top_bottom(remaining: list) -> "tuple[list, list]":
    """Greedily split *remaining* (still cavity-count descending) between
    top/bottom, always adding the next (largest remaining) housing to
    whichever side currently has the smaller total -- the standard
    largest-first heuristic for balancing a two-way partition.
    """
    top, bottom = [], []
    top_total = bottom_total = 0

    for candidate in remaining:
        count = _cavity_count(candidate)
        if top_total <= bottom_total:
            top.append(candidate)
            top_total += count
        else:
            bottom.append(candidate)
            bottom_total += count

    return top, bottom


def _edge_span(members: list) -> float:
    if not members:
        return 0.0

    spacing = Config.layout.housing_spacing
    return (sum(_cavity_extent(h) for h in members)
            + spacing * (len(members) - 1))


def _place_column(members: list, x_sign: float, rect_width: float) -> None:
    """Stack *members* along world Z, pin edges flush at the shared
    interior boundary ``rect_width/2 + margin`` on the left (x_sign=-1) or
    right (x_sign=+1) side, each extending outward by its own text extent.
    """
    if not members:
        return

    spacing = Config.layout.housing_spacing
    margin = Config.layout.margin
    angle_deg = 0.0 if x_sign > 0 else 180.0

    span = _edge_span(members)
    z = -span / 2.0

    for housing in members:
        cav = _cavity_extent(housing)
        text = _text_extent(housing)

        z_center = z + cav / 2.0
        x = x_sign * (rect_width / 2.0 + margin + text / 2.0)

        _apply_placement(housing, x, z_center, angle_deg)
        z += cav + spacing


def _place_row(members: list, z_sign: float, rect_height: float) -> None:
    """Stack *members* along world X, pin edges flush at the shared
    interior boundary ``rect_height/2 + margin`` on the bottom (z_sign=-1)
    or top (z_sign=+1) side. Rotation signs verified analytically against
    ``objects2d.base2d._rotate_about_y`` (a pure single-axis rotation, so
    the result is identical whether produced by that helper or by
    ``angle2d.y``'s own native quaternion, which is what actually renders
    it -- see ``_apply_placement``): +90 degrees about world Y sends
    local -X (the pin edge) to +Z (bottom-edge housings, pins toward the
    interior above them); -90 degrees sends it to -Z (top-edge housings,
    pins toward the interior below them).
    """
    if not members:
        return

    spacing = Config.layout.housing_spacing
    margin = Config.layout.margin
    angle_deg = 90.0 if z_sign < 0 else -90.0

    span = _edge_span(members)
    x = -span / 2.0

    for housing in members:
        cav = _cavity_extent(housing)
        text = _text_extent(housing)

        x_center = x + cav / 2.0
        z = z_sign * (rect_height / 2.0 + margin + text / 2.0)

        _apply_placement(housing, x_center, z, angle_deg)
        x += cav + spacing


def recompute_layout(project: "_project.Project") -> None:
    """Recompute and persist every housing's ``position2d``/``angle2d`` in
    *project* -- called after a new housing is added (see
    ``handlers/housing_handler.py``). No-op if
    ``Config.editor2d.layout.auto_layout_enabled`` is ``False``, or if the
    project has no housings.
    """
    if not Config.layout.auto_layout_enabled:
        return

    housings = sorted(project.housings, key=_cavity_count, reverse=True)

    if not housings:
        return

    if len(housings) == 1:
        _apply_placement(housings[0], 0.0, 0.0, 0.0)
        return

    left, right, remaining = _assign_sides(housings)
    top, bottom = _assign_top_bottom(remaining)

    rect_height = max(_edge_span(left), _edge_span(right))
    rect_width = max(_edge_span(top), _edge_span(bottom))

    _place_column(left, -1.0, rect_width)
    _place_column(right, 1.0, rect_width)
    _place_row(top, 1.0, rect_height)
    _place_row(bottom, -1.0, rect_height)
