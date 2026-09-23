# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment drag for a bundle in the Peg Board Editor.

Waypoints and bundle ends are already covered by :mod:`~.generic` (a
waypoint is a real ``bundle_layout.BundleLayout`` object; an end is
always attached to a real anchor -- there is no genuinely free-floating
bundle endpoint with nothing to drag). What's left here is clicking the
rendered strand itself, between two consecutive chain nodes, not close
to either: both bounding nodes move together, rigidly, by the same
world-space delta ("if a wire or bundle section is clicked and dragged
between 2 waypoints then that section should move", confirmed
2026-08-16).

The dragged segment's own length never changes -- both its endpoints
move by the identical delta, so the distance between them stays
constant. Only each bounding node's *other* (non-shared) touching edge,
if it has one, needs clamping -- but NOT independently the way
:mod:`~.__init__`'s single-edge clamp does for a lone-point drag:
clamping each of the two points to a different effective distance would
stretch the segment between them. Instead the most restrictive scale
factor across both points' own budgets is found first (see
:meth:`Bundle._max_scale_within_budget`), then applied identically to
both, so the segment truly moves as one rigid unit. A point that is
itself an outermost bundle end has no "other" edge at all (nothing lies
past it), so that side of the drag is unconstrained.

Kept as this class's own self-contained copy, deliberately NOT reusing
:mod:`~.wire`'s own ``Wire`` (mirrors were previously identical, since a
``PJTBundle`` row exposes the same ``start_position_pegboard_id``/
``stop_position_pegboard_id``/``waypoints_pegboard``/``length_mm`` shape
a ``PJTWire`` does) -- ``wire.py`` was rebuilt on
:class:`~harness_designer.handlers.wire_drag_base.WireDragBase` (the
shared 3D/peg-board endpoint-and-segment drag with live snap-probing),
which assumes ``target.db_obj.part`` is a real wire catalog part
(``SnapProbeSet``'s own AWG/crimp-range compat checks need a wire's own
conductor fields, which ``PJTBundle.part`` -- a ``BundleCover``, not a
wire part -- doesn't have the shape of); a bundle also never has a
genuinely free/unattached true end the way a wire's placeholder end can
be, so it never needed that endpoint-and-snap case to begin with, only
this budget-clamped rigid-segment one. Rather than teach the shared
base to skip snap-probing for a chain type with no compatible part at
all, this keeps the bundle's own, already-proven segment-only
implementation self-contained.
"""

from typing import TYPE_CHECKING

import math

from .. import editor_pegboard as _editor_pegboard
from .. import base as _base
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects
    from ...objects import project as _project
    from ...database.project_db import pjt_bundle as _pjt_bundle


class SegmentDragPlan:
    """What a click on a bundle's rendered strand should drag --
    computed once at drag-start by :func:`plan_segment_drag`.

    :ivar points: The two live, mutable :class:`~geometry.point.Point`
        instances bounding the clicked segment -- moved together by the
        same delta every frame.
    :ivar outer_budgets: One entry per point in :attr:`points`, in the
        same order -- ``(neighbor_x, neighbor_z, max_length_mm)`` for
        that point's *other* touching edge (excluding the dragged
        segment itself), or ``None`` if that point is an outermost
        bundle end with nothing further to clamp against.
    """

    __slots__ = ('points', 'outer_budgets')

    def __init__(self, points: tuple[_point.Point, _point.Point],
                 outer_budgets: tuple[tuple[float, float, float] | None,
                                       tuple[float, float, float] | None]) -> None:
        self.points = points
        self.outer_budgets = outer_budgets


@_check_types.do
def _closest_segment_index(positions: list[tuple[float, float]], click_x: float, click_z: float) -> int:
    """Return the index ``i`` such that the segment between
    ``positions[i]`` and ``positions[i + 1]`` is nearest
    ``(click_x, click_z)``.
    """
    best_dist = math.inf
    best_index = 0

    for i in range(len(positions) - 1):
        ax, az = positions[i]
        bx, bz = positions[i + 1]
        dx, dz = bx - ax, bz - az

        seg_len_sq = dx * dx + dz * dz
        if seg_len_sq < 1e-12:
            t = 0.0
        else:
            t = ((click_x - ax) * dx + (click_z - az) * dz) / seg_len_sq
            t = max(0.0, min(1.0, t))

        px, pz = ax + t * dx, az + t * dz
        dist = math.hypot(click_x - px, click_z - pz)

        if dist < best_dist:
            best_dist = dist
            best_index = i

    return best_index


@_check_types.do
def plan_segment_drag(project: "_project.Project", chain_db_obj: "_pjt_bundle.PJTBundle",
                       click_pos: _point.Point) -> SegmentDragPlan | None:
    """Work out what a click on *chain_db_obj*'s rendered strand at
    *click_pos* should drag.

    :param project: The currently open project.
    :param chain_db_obj: A :class:`PJTBundle` row, exposing
        ``start_position_pegboard_id``/``stop_position_pegboard_id``/
        ``waypoints_pegboard``/``length_mm``.
    :param click_pos: World-space (X/Z) click position.
    :returns: The resolved plan, or ``None`` if the chain has fewer than
        two nodes (degenerate).
    """
    ids = [chain_db_obj.start_position_pegboard_id]
    ids += [wp.db_id for wp in chain_db_obj.waypoints_pegboard]
    ids.append(chain_db_obj.stop_position_pegboard_id)

    if len(ids) < 2:
        return None

    points_table = project.ptables.pjt_points_pegboard_table
    live_points = [points_table[point_id].point for point_id in ids]
    positions = [(float(p.x), float(p.z)) for p in live_points]

    index = _closest_segment_index(
        positions, float(click_pos.x), float(click_pos.z))

    # Budgets for every edge in the chain, same proportional-split
    # formula as chain_edges.touching_edges -- computed once here rather
    # than calling that per point, since both this segment's own budget
    # (unused -- see module docstring) and each bounding point's outer
    # budget come from the same single pass.
    total_length_mm = chain_db_obj.length_mm
    distances = [
        math.hypot(positions[i + 1][0] - positions[i][0],
                   positions[i + 1][1] - positions[i][1])
        for i in range(len(positions) - 1)
    ]
    total_distance = sum(distances)

    if total_distance < 1e-9:
        budgets = [total_length_mm / len(distances)] * len(distances)
    else:
        budgets = [total_length_mm * (d / total_distance) for d in distances]

    point_a, point_b = live_points[index], live_points[index + 1]

    outer_a = None
    if index > 0:
        nx, nz = positions[index - 1]
        outer_a = (nx, nz, budgets[index - 1])

    outer_b = None
    if index + 1 < len(positions) - 1:
        nx, nz = positions[index + 2]
        outer_b = (nx, nz, budgets[index + 1])

    return SegmentDragPlan(points=(point_a, point_b), outer_budgets=(outer_a, outer_b))


class Bundle(_editor_pegboard.DragHandlerPegboard):
    """Segment drag for a bundle -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
                 mouse_pos: _point.Point) -> None:
        # Bypass DragHandlerPegboard's own __init__ -- it caches
        # target.objpegboard.touching_budgets(), meaningful for a
        # single-point drag, but a segment drag moves TWO points and the
        # bundle wrapper itself has no position of its own at all (see
        # objects_pegboard.bundle.Bundle's own docstring).
        _base.DragHandlerBase.__init__(self, canvas, target)

        project = canvas.mainframe.project
        bundle_db_obj = target.objpegboard.db_obj

        world_pos = canvas.camera.screen_to_world(mouse_pos)
        plan = plan_segment_drag(project, bundle_db_obj, world_pos)

        self._points = plan.points
        self._outer_budgets = plan.outer_budgets

        # The world position the click itself landed on -- NOT either
        # bounding point's own position, which can (and usually does)
        # sit well away from wherever along the segment was actually
        # clicked. Every __call__ diffs against this (updated each
        # frame to whatever was actually applied) so the segment
        # translates by however far the mouse has moved since the last
        # frame -- using either point's own position as the reference
        # instead (as an earlier version of this did) made that point
        # snap outright onto the cursor on the very first move, since
        # the "delta" would then be the full point-to-click distance
        # rather than a small per-frame increment -- visually
        # indistinguishable from a new bend/waypoint suddenly appearing.
        self._last_x = float(world_pos.x)
        self._last_z = float(world_pos.z)

    @staticmethod
    @_check_types.do
    def _max_scale_within_budget(px: float, pz: float, dx: float, dz: float,
                                 nx: float, nz: float, max_length_mm: float) -> float:
        """Return the largest ``t`` in ``[0, 1]`` such that the point
        currently at ``(px, pz)``, moved by ``t * (dx, dz)``, stays
        within *max_length_mm* of ``(nx, nz)``.

        Assumes ``(px, pz)`` already satisfies the budget at ``t=0`` --
        true by induction, since every previous frame already enforced
        it. Solves ``|((px,pz) - (nx,nz)) + t*(dx,dz)| = max_length_mm``
        for the smallest positive root (where the point would first
        cross the boundary), rather than radially clamping the final
        position the way :meth:`~.DragHandlerPegboard._clamp_to_edge`
        does for a single-point drag -- clamping each of this drag's two
        points to a *different* effective distance would silently
        stretch the segment between them, which must stay rigid (see the
        module docstring).
        """
        ox = px - nx
        oz = pz - nz

        a = dx * dx + dz * dz
        if a < 1e-12:
            return 1.0

        b = 2.0 * (ox * dx + oz * dz)
        c = ox * ox + oz * oz - max_length_mm * max_length_mm

        discriminant = b * b - 4.0 * a * c
        if discriminant < 0.0:
            # The line the point travels along never reaches the budget
            # circle at all (passes entirely inside or entirely outside
            # it) -- no clamp needed either way.
            return 1.0

        # f(t) = a*t^2 + b*t + c is an upward parabola (a > 0); f(0) = c
        # is <= 0 by invariant (the point already satisfies its budget
        # before this frame's move). The two roots' product is c / a
        # <= 0, so they never have the same sign -- the LARGER root
        # (computed with +sqrt) is always the non-negative one, and is
        # exactly where f first crosses back above zero as t increases
        # from 0 -- i.e. the point leaving the budget circle. Do not take
        # the smaller root or filter/rank the roots by "positive" -- for
        # a point starting exactly AT the boundary (c == 0) the smaller
        # root is negative and the correct answer (0.0, no further
        # outward movement allowed) IS the larger root, not a filtered-
        # out candidate.
        sqrt_disc = math.sqrt(discriminant)
        t = (-b + sqrt_disc) / (2.0 * a)

        return max(0.0, min(1.0, t))

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: object, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, locked ortho camera gives an absolute world position directly
        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        target_x, target_z = float(world_pos.x), float(world_pos.z)

        # Incremental, from the last frame's (possibly budget-clamped)
        # world position -- NOT from either bounding point's own
        # position (see __init__'s own comment on why that snapped the
        # segment onto the cursor instead of translating it).
        raw_dx = target_x - self._last_x
        raw_dz = target_z - self._last_z

        # Both points must move by the exact same delta -- find the most
        # restrictive scale factor across each point's own outer budget
        # (if any) first, then apply that single scale to both, rather
        # than clamping each point's own candidate position independently
        # (which would let the segment between them stretch or compress).
        scale = 1.0
        for point, budget in zip(self._points, self._outer_budgets):
            if budget is None:
                continue

            neighbor_x, neighbor_z, max_length_mm = budget
            point_scale = self._max_scale_within_budget(
                float(point.x), float(point.z), raw_dx, raw_dz,
                neighbor_x, neighbor_z, max_length_mm)
            scale = min(scale, point_scale)

        for point in self._points:
            point.x = float(point.x) + raw_dx * scale
            point.z = float(point.z) + raw_dz * scale

        # Track what was actually applied, not the raw mouse target --
        # a budget-clamped frame (scale < 1) must not let the cursor
        # "run ahead" and then snap the segment forward the moment it
        # drifts back within budget.
        self._last_x += raw_dx * scale
        self._last_z += raw_dz * scale
