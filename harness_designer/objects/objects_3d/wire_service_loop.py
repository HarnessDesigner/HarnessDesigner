# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import numpy as np
from PySide6 import QtCore, QtWidgets

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from . import wire_service_loop_search as _loop_search
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ...shapes import cylinder_helix as _cylinder_helix
from ... import check_types as _check_types
from ... import color as _color
from ...crash_dump import Attr, capturable


if TYPE_CHECKING:
    from ...ui.editor_3d import editor_3d as _editor_3d
    from .. import ObjectBase as _ObjectBase
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from .. import wire_service_loop as _wire_service_loop
    from .. import wire as _wire
    from .. import wire_marker as _wire_marker
    from ... import ui as _ui
    from ...gl import vbo as _vbo_base
    from ...shapes import text as _text


Config = _config.Config.editor_3d


# The roll search turns the loop about the wire in steps of this many degrees at
# the spot it is on, where a narrow gap matters, and in the coarser steps while it
# slides along the wire, where a long slide multiplies the work.
_ROLL_STEP_DEG = 2.0
_SLIDE_ROLL_STEP_DEG = 6.0


@_check_types.do
def _wire_pivot(
    before: np.ndarray, after: np.ndarray, start: np.ndarray, stop: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """The (unit axis, pivot) the loop rolls about.

    The axle is the wire itself: the line through *before* and *after*, the
    wire points just before the loop and just after it. The line between the
    loop's own *start* and *stop* points is NOT that line (it sits at an angle
    to the coil's axis, so rolling about it makes the coil wobble); the two
    lines meet at the start point, which is on the wire, and that meeting point
    is the pivot. Lines that never meet (parallel, or skew from rounding) give
    the point of the wire's line nearest the start point.
    """
    axis = after - before
    axis = axis / np.linalg.norm(axis)

    v = stop - start
    w0 = before - start
    b = float(np.dot(axis, v))
    c = float(np.dot(v, v))
    d = float(np.dot(axis, w0))
    e = float(np.dot(v, w0))
    denom = c - b * b

    if denom < 1e-6 * c:
        s = -d
    else:
        s = (b * e - c * d) / denom

    return axis, before + s * axis


class WireRoll:
    """A loop's roll about the wire it sits in, frozen at the pose the loop
    had when the roll began (see WireServiceLoop.begin_wire_roll).

    :meth:`pose` is always worked out from that starting pose, never from the
    loop's current one, so a drag can not accumulate drift and a roll of 0
    puts the loop back where it began. A roll is a rigid rotation of the mesh
    AND of the start point about the axle through the pivot (see
    _wire_pivot); the object turns about its OWN origin, so what it needs is
    the roll composed AFTER its starting angle (``R' = Q R0``, Q a rotation
    about a WORLD axis) together with the start point carried round the pivot
    -- the same roll _resolve_collision makes.

    :param axis: Unit direction of the wire through the loop (float64).
    :param pivot: Where that wire meets the line between the loop's start and
        stop points (float64).
    :param matrix: The loop's rotation matrix (``Angle.as_matrix_numpy``, the
        column-vector R) when the roll began (float64).
    :param start: The loop's start point when the roll began (float64).
    """

    @_check_types.do
    def __init__(self, axis: np.ndarray, pivot: np.ndarray, matrix: np.ndarray, start: np.ndarray):
        self.axis = axis
        self.pivot = pivot
        self.matrix = matrix
        self.start = start

    @_check_types.do
    def pose(self, degrees: float) -> tuple[np.ndarray, _angle.Angle]:
        """The (start point, angle) the loop has after rolling *degrees*
        (right-handed about :attr:`axis`) from the pose it began in.
        """
        theta = np.radians(degrees)
        x, y, z = self.axis

        cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]], dtype=np.float64)
        rotation = np.eye(3) + np.sin(theta) * cross + (1.0 - np.cos(theta)) * (cross @ cross)

        start = self.pivot + rotation @ (self.start - self.pivot)
        angle = _angle.Angle.from_matrix((rotation @ self.matrix).astype(np.float32))

        return start, angle


class _MoveSession:
    """Cached collision-candidate state for one whole interactive move or
    rotate operation -- see WireServiceLoop.begin_move_session. None of
    this changes for the duration of a single continuous drag, so it's
    computed once at the start of one instead of on every intermediate
    _update_position/_update_angle call.

    loop_search holds every candidate box (one per wire section, one per
    other loop or marker) with the shape its mesh really is, plus the loop's
    own mesh, and runs the whole roll/slide search against them in C -- see
    wire_service_loop_search.
    """
    attached: list | None = None
    markers: list | None = None
    loop_search: _loop_search.LoopSearch | None = None


@capturable()
class WireServiceLoop(_base_3d.Base3D):
    """A wire service loop: a helix-shaped part connecting a start point to
    a derived stop point (see _sync_stop_position) offset from it by the
    loop's own geometry.

    Base3D only knows about one Point (the start -- passed to Base3D.__init__
    as *position*, so it's what the render pivot/OBB/AABB/floor-lock all key
    off). The stop point is this class's own concern: _update_position and
    _update_angle are overridden so that whenever the start point moves or
    the loop rotates, the derived stop point is recomputed to match -- a
    caller only ever needs to move the start point (see
    handlers.wire_service_loop_handler) and everything else -- the stop
    point, and rotation pivoting around the loop's own centroid rather than
    its start point -- is handled here.
    """
    __dump_schema__ = (
        Attr('_part', severity=2),
        Attr('_p1', severity=2),
        Attr('_p2', severity=2),
        Attr('_stripe', severity=2),
        Attr('_last_centroid', severity=2),
    )

    parent: "_wire_service_loop.WireServiceLoop" = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = None

    @_check_types.do
    def __init__(self, parent: "_wire_service_loop.WireServiceLoop",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):
        """Initialise the :class:`WireServiceLoop` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_service_loop.WireServiceLoop`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part
            color = self._part.color.ui
            material = _materials.Plastic(color)

            position = db_obj.start_position3d
            position2 = db_obj.stop_position3d

            vbo = _cylinder_helix.create_vbo()
            diameter = self._part.od_mm
            scale = _point.Point(diameter, diameter, diameter)
            angle = db_obj.angle3d

            self._last_centroid: np.ndarray | None = None
            # Last pose _resolve_collision actually verified as clear -- the
            # fallback to revert to if a later resolve attempt can't find any
            # clear spot at all (see _resolve_collision).
            self._last_resolved_position: np.ndarray | None = None
            self._last_resolved_quat: np.ndarray | None = None
            # Set by begin_move_session/cleared by end_move_session -- see
            # both, and _resolve_collision.
            self._move_session: _MoveSession | None = None

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

            self._p1 = position
            self._p2 = position2

            # Always derive the stop point fresh from the start point/angle/
            # scale rather than trusting whatever was last persisted -- keeps
            # this the single source of truth regardless of how the row got
            # here (self-heals any stale data from before this existed).
            self._last_centroid = self._world_centroid()
            self._sync_stop_position()

            # Collision avoidance runs "anytime a service loop is being moved"
            # (see _resolve_collision) -- that includes the very first
            # placement, not just later interactive moves.
            self._resolve_collision()
            self._sync_stop_position()
            self._last_centroid = self._world_centroid()

            stripe_color = self._part.stripe_color

            if stripe_color is not None:
                self._stripe = WireServiceLoopStripe(parent, self, stripe_color.ui, scale, angle, position)
                # WireStripe's db_obj is always None (it's not its own DB row --
                # see WireStripe.__init__), so Base3D.__init__ hits the
                # `except AttributeError: self._is_visible = False` branch and
                # the stripe is built permanently invisible. Sync it to the
                # wire's own just-computed visibility here.
                self._stripe.is_visible = self._is_visible

                self.editor3d.Refresh()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def _world_centroid(self) -> np.ndarray:
        """World-space centroid of the loop's own OBB -- the rotation pivot
        (see _update_angle), not the start/stop connection points.
        """
        centroid = self._vbo.local_obb.mean(axis=0)
        centroid = centroid * self._scale.as_numpy
        centroid = centroid @ self._angle
        centroid = centroid + self._position.as_numpy

        return centroid

    @_check_types.do
    def _sync_stop_position(self) -> None:
        """Recompute the derived stop point from the current start
        position, angle and scale -- the same scale/rotate/translate of
        the VBO's own endpoint that _mesh_world_triangles applies to the
        full mesh.
        """
        tmp = self._vbo.endpoint.copy()
        tmp *= self._scale
        tmp @= self._angle
        tmp += self._position

        self._p2 += tmp - self._p2

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """Base3D recomputes OBB/AABB/floor-lock off the start point alone
        -- also keep the derived stop point in step with it, resolve any
        collision the move introduced (see _resolve_collision), and keep
        the centroid rotation pivot baseline used by _update_angle current.
        """
        super()._update_position(position)
        self._resolve_collision()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        """Rotate the loop around its own centroid, not its start point.

        Base3D's rendering pivot is always objectPosition (the start
        point), so pivoting around the centroid instead means compensating
        the start position by however far the centroid would otherwise
        move under the new angle -- computed and applied *before* Base3D's
        own bookkeeping (OBB/AABB, floor lock) runs against the corrected
        position. Only this object's own _update_position listener is
        unbound for that one write (the same unbind -> write -> rebind
        idiom used throughout this codebase, e.g.
        gl.canvas3d.rotation_rings.Rings3D.apply_drag_angle) so it isn't
        re-entered; any other object sharing this same Point (e.g. an
        attached wire's endpoint, see
        handlers.wire_service_loop_handler._split_wire_for_loop) still
        sees the move normally.

        Not used for one-shot authoritative placement (finalizing
        interactive placement) -- see set_placement, which bypasses this.
        """
        if self._last_centroid is not None:
            # Where the centroid would land if the position stayed put,
            # under the angle that was just applied.
            unshifted_centroid = self._world_centroid()
            delta = self._last_centroid - unshifted_centroid

            if not np.allclose(delta, 0.0, atol=1e-9):
                self._position.unbind(self._update_position)

                try:
                    self._position += _point.Point(*[float(v) for v in delta])
                finally:
                    self._position.bind(self._update_position)

        super()._update_angle(angle)

        self._resolve_collision()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    @_check_types.do
    def _write_angle(self, target_angle: _angle.Angle) -> None:
        """Write target_angle's exact rotation into self._angle, bypassing
        its normal Euler-driven derivation. Caller is responsible for
        unbind/rebind of _update_angle around this if needed -- this
        method only performs the write.

        Per the codebase-wide rule that any angle change must be made via
        Euler, never the raw quaternion (quaternion -> Euler conversion is
        ambiguous under gimbal lock), this mirrors HandlerBase.reset_angle/
        set_angle_from_housing: mutate the Euler fields inside the angle's
        own write-context, then correct _q/_matrix to the exact target
        rotation and manually re-fire callbacks.
        """
        euler = target_angle.as_euler_float
        with self._angle:
            self._angle.x = euler[0]
            self._angle.y = euler[1]
            self._angle.z = euler[2]
            self._angle._matrix[:] = target_angle.as_matrix_numpy  # NOQA

        self._angle._q.w = target_angle._q.w  # NOQA
        self._angle._q.x = target_angle._q.x  # NOQA
        self._angle._q.y = target_angle._q.y  # NOQA
        self._angle._q.z = target_angle._q.z  # NOQA
        self._angle._process_callbacks()  # NOQA

    @_check_types.do
    def _implied_stop(self) -> np.ndarray:
        """Where the mesh puts the stop point at the current angle and start
        point: the formula of _sync_stop_position, returned instead of
        written. Used rather than _p2 because a resolve that runs in the
        middle of a move (the start point is new, _p2 is not synced yet) must
        see a consistent start/stop pair.
        """
        # vbo.endpoint is a Point (np.asarray cannot take one), and Point.as_numpy is float32
        stop = self._vbo.endpoint.as_numpy.astype(np.float64) * self._scale.as_numpy

        return self._angle.as_matrix_numpy @ stop + self._position.as_numpy

    @_check_types.do
    def _wire_points(self, attached: list["_wire.Wire"]) -> tuple[np.ndarray, np.ndarray] | None:
        """The wire points that bracket the loop: the one just before it
        (the previous point of the attached wire that ends at the loop's
        STOP point, a waypoint or that wire's own start) and the one just
        after it (the next point of the attached wire that starts at the
        loop's START point). None unless both exist.

        The loop sits in the wire with its stop point on the side the wire
        comes from and its start point on the side it goes on to: the helix's
        endpoint lies behind its start along the wire, and
        add_handlers.editor_3d.wire_service_loop.split_wire_for_loop leaves the
        first half ending at the stop point and the second starting at the
        start point.
        """
        before = None
        after = None

        for w in attached:
            points = [w.obj3d.start_position.as_numpy]
            points.extend(waypoint.point.as_numpy for waypoint in w.db_obj.waypoints3d)
            points.append(w.obj3d.stop_position.as_numpy)

            if w.obj3d.stop_position.db_id == self._p2.db_id:
                before = points[-2]

            if w.obj3d.start_position.db_id == self._p1.db_id:
                after = points[1]

        if before is None or after is None:
            return None

        # Point.as_numpy is float32; the pivot maths (a near-parallel test, dot
        # products of long vectors) wants float64
        return before.astype(np.float64), after.astype(np.float64)

    @_check_types.do
    def _attached_wires(self) -> list["_wire.Wire"]:
        """Wires directly touching this loop's own start/stop points --
        found by the object itself (via the shared Point db_id, see
        handlers.wire_service_loop_handler._split_wire_for_loop) rather
        than being told by a handler. Adjacent by construction, never a
        real collision -- excluded from _resolve_collision's candidates.
        """
        ids = {self._p1.db_id, self._p2.db_id}
        return [
            w for w in self.mainframe.project.wires
            if w.obj3d.start_position.db_id in ids or w.obj3d.stop_position.db_id in ids
        ]

    @_check_types.do
    def _markers_on_attached_wires(self) -> list["_wire_marker.WireMarker"]:
        """Wire markers sitting on either of this loop's attached wires --
        both a collision obstacle and a hard slide boundary (see
        _resolve_collision): sliding must never cross a marker to reach
        clear space on its far side.
        """
        wire_ids = {w.db_obj.db_id for w in self._attached_wires()}
        if not wire_ids:
            return []
        return [m for m in self.mainframe.project.wire_markers if m.db_obj.wire_id in wire_ids]

    @_check_types.do
    def _apply_resolved(self, position_np: np.ndarray, q_arr: np.ndarray) -> None:
        """Commit a (position, quaternion) pair found by _resolve_collision
        without re-entering _update_position/_update_angle -- the search
        that produced them already accounts for their combined effect
        (roll candidates are tested at a fixed position; see
        _resolve_collision), so re-deriving via the normal callbacks
        (which would, e.g., re-apply centroid-pivot compensation on top)
        would invalidate the very placement just verified as clear.
        """
        current_pos = self._position.as_numpy
        if not np.allclose(position_np, current_pos, atol=1e-9):
            self._position.unbind(self._update_position)

            try:
                self._position += _point.Point(*[float(v) for v in (position_np - current_pos)])
            finally:
                self._position.bind(self._update_position)

        current_q = np.array(self._angle.as_quat_float, dtype=np.float64)
        if not np.allclose(q_arr, current_q, atol=1e-9):
            self._angle.unbind(self._update_angle)

            try:
                self._write_angle(_angle.Angle.from_quat(q_arr.tolist()))
            finally:
                self._angle.bind(self._update_angle)

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _viewport_candidates(self) -> list:
        """Wires and other loops currently visible in the viewport -- the
        filter tier for begin_move_session.

        This is a rendering-frustum concept, not a spatial-locality one:
        an obstacle just outside the frustum while genuinely close in world
        space would be missed. Accepted -- the user is necessarily looking
        at the wire they just clicked on to start this placement, and a
        fresh move/rotate session rebuilds this list from scratch, so
        releasing the mouse and moving/clicking again picks up anything a
        gap here let through.

        No further distance cull on top of this: the search rejects a far
        box with one axis-aligned compare in C, so an extra candidate costs
        nanoseconds, not a Python-level loop iteration.
        """
        return [
            view.parent for view in self._aabb_manager.visible_objects()
            if view.parent is not self.parent
            and (view.parent.is_wire or view.parent.is_wire_service_loop)
        ]

    @_check_types.do
    def begin_move_session(self) -> None:
        """Start caching the collision-candidate list -- and every
        candidate's boxes, handed to the C search once -- for a whole
        interactive move or rotate operation, instead of rebuilding any of
        it on every single intermediate _update_position/_update_angle
        call during one continuous drag.

        Called once when a drag/rotate begins:
        gl.canvas3d.dragging.DragObject and gl.canvas3d.rotation_rings.
        DragRotate call this (duck-typed -- only when the dragged/rotated
        object actually defines it) from their own __init__; handlers.
        wire_service_loop_handler.AddWireServiceLoopHandler calls it right
        after constructing the preview object, treating its whole
        interactive placement as one such operation. Pair with
        end_move_session.
        """
        session = _MoveSession()
        session.attached = self._attached_wires()
        attached_wire_ids = {w.db_obj.db_id for w in session.attached}
        session.markers = self._markers_on_attached_wires()

        candidates = [
            obj for obj in self._viewport_candidates()
            if not (obj.is_wire and obj.db_obj.db_id in attached_wire_ids)
        ] + session.markers

        # Every candidate's collision boxes, each tagged with the shape its
        # mesh really is. A wire is one box per section (Wire.segment_obbs):
        # its pool OBB is the envelope of the whole path, which for a bent
        # or diagonal wire is a far larger box than the wire itself, and a
        # section's mesh is a cylinder (KIND_CYLINDER). Anything else
        # (another loop, a marker) is its single pool OBB (KIND_BOX). The
        # boxes are only the hit list: the search goes on to test this
        # loop's own mesh against the real shape of every box that overlaps.
        boxes = []
        kinds = []
        for candidate in candidates:
            if candidate.is_wire:
                for box in candidate.obj3d.segment_obbs():
                    boxes.append(box)
                    kinds.append(_loop_search.KIND_CYLINDER)
            elif candidate.obj3d.obb is not None:
                boxes.append(candidate.obj3d.obb)
                kinds.append(_loop_search.KIND_BOX)

        session.loop_search = _loop_search.LoopSearch(
            boxes, kinds, self._vbo.local_obb, self._scale.as_numpy,
            self._vbo.vertices.reshape(-1, 3))

        self._move_session = session

    @_check_types.do
    def end_move_session(self) -> None:
        """Stop caching -- the next call to _resolve_collision without an
        active session builds and uses a throwaway one-shot list instead
        (see _resolve_collision), and the next begin_move_session call
        starts a fresh cache. Pair with begin_move_session.
        """
        self._move_session = None

    @_check_types.do
    def _resolve_collision(self) -> None:
        """Turn the loop about the wire, and slide it along it if it must,
        until it is clear of nearby wires, other loops, and wire markers on
        the attached wires -- mutates self._position/self._angle as needed
        (see _apply_resolved).

        The loop is a coil in a wire, so it can only spin about the wire.
        The axle is the line through the two wire points either side of it
        (_wire_points), NOT the line between the loop's own start and stop
        points, which sits at an angle to the coil's axis and would make it
        wobble; the pivot is where the two lines meet (_wire_pivot). A roll
        is a rigid rotation of the mesh AND of the start and stop points about
        that axle through that pivot, and what is committed is the angle the
        object itself needs for that (the roll composed with its current
        angle, since the object turns about its own origin, not the pivot)
        together with the new start point -- see wire_service_loop_search.

        1. Look for the NEAREST clear roll at the current spot, in small
           steps outward from the current angle, either way.
        2. If none clears, slide along the wire in both directions, scanning
           the full turn at each step, each direction capped at the wire
           point on that side or the nearest wire marker, whichever is closer
           -- sliding never crosses either.
        3. Keep whichever direction reaches a clear spot in fewer steps.
        4. If neither direction ever clears within its bound, the pose is
           left unchanged -- "the placement should not be allowed" past
           that point; canceling and re-placing on the other side of
           whatever's blocking it is the way out, not an automatic
           slide-through.

        All of that runs in C (wire_service_loop_search.LoopSearch.search):
        a pose is clear when, for every candidate, either its box misses the
        loop's box or the loop's mesh misses the candidate's real shape.
        This method only works out the axle, pivot and slide limits, and
        applies what the search returns.

        Runs from _update_position/_update_angle (and once at the end of
        __init__), so this fires for any move regardless of what triggered
        it -- this handler's own preview drag today, or anything else that
        moves this loop's shared start point or rotates it in the future.
        Nothing to resolve (and nothing done) while the loop is not yet in a
        wire on both sides, e.g. while a project is still loading its wires.

        Candidate gathering (viewport filter, attached-wire/marker lookups,
        every candidate's boxes) is cached for the whole operation by
        begin_move_session, not redone on every one of these calls -- see
        there. If no session is active (this was reached outside a
        begin/end_move_session bracket), a throwaway one-shot session is
        built here instead of skipping collision avoidance entirely.
        """
        session = self._move_session
        if session is None:
            self.begin_move_session()
            session = self._move_session
            self._move_session = None  # one-shot -- nothing to keep cached

        wire_points = self._wire_points(session.attached)
        if wire_points is None:
            return

        before, after = wire_points
        p1_np = self._p1.as_numpy.astype(np.float64)
        p2_np = self._implied_stop()
        axis, pivot = _wire_pivot(before, after, p1_np, p2_np)
        q0 = np.array(self._angle.as_quat_float, dtype=np.float64)
        scale_np = self._scale.as_numpy
        t0 = float(np.dot(self._position.as_numpy - p1_np, axis))

        # Bound each slide direction by the nearest obstacle point (the wire
        # point on that side, or a marker) projected onto the axle --
        # whichever is closer. The loop is not a point: along the axle it spans
        # from its start point to its stop point (the stop sits behind the
        # start), and it is the end that leads in each direction that has to
        # stop at the boundary.
        reach = float(np.dot(p2_np - p1_np, axis))
        lo = min(0.0, reach)
        hi = max(0.0, reach)

        boundary_ts = [float(np.dot(before - p1_np, axis)), float(np.dot(after - p1_np, axis))]
        for m in session.markers:
            boundary_ts.append(float(np.dot(m.obj3d.position.as_numpy - p1_np, axis)))

        pos_limit = min([bt - hi for bt in boundary_ts if bt >= t0 + hi], default=t0)
        neg_limit = max([bt - lo for bt in boundary_ts if bt <= t0 + lo], default=t0)

        step = max(float(scale_np[0]) * 0.5, 0.5)

        found = session.loop_search.search(
            p1_np, p2_np, pivot, axis, q0, t0, pos_limit, neg_limit, step,
            _ROLL_STEP_DEG, _SLIDE_ROLL_STEP_DEG)

        if found is not None:
            self._commit_resolved(
                np.array(found[3], dtype=np.float64), np.array(found[2], dtype=np.float64))
            return

        # Nothing clears anywhere within bounds -- revert to the last pose
        # actually verified clear, instead of leaving the loop sitting
        # wherever the move that triggered this attempt landed it (which
        # may itself be colliding). "The placement should not be allowed"
        # past this point; canceling and re-placing elsewhere is the way
        # out, not an automatic slide-through or a silently-accepted
        # collision.
        if self._last_resolved_position is not None:
            self._apply_resolved(self._last_resolved_position, self._last_resolved_quat)

    @_check_types.do
    def _commit_resolved(self, position_np: np.ndarray, q_arr: np.ndarray) -> None:
        """Apply a pose _resolve_collision just verified as clear, and
        remember it as the fallback for a future resolve attempt that
        can't find anything clear at all (see _resolve_collision)."""
        self._apply_resolved(position_np, q_arr)
        self._last_resolved_position = self._position.as_numpy.copy()
        self._last_resolved_quat = np.array(self._angle.as_quat_float, dtype=np.float64)

    @_check_types.do
    def set_placement(self, position: _point.Point, quat: np.ndarray) -> None:
        """Snap the loop to an exact start position + rotation (a
        [w, x, y, z] quaternion) in one atomic step, bypassing the
        rotate-around-centroid compensation _update_angle normally applies.

        Used to finalize interactive placement, where the handler (or
        _resolve_collision, via a live drag) has already arrived at an
        exact, already-resolved target position/orientation and wants it
        applied as-is -- not for incremental interactive rotation, which is
        what _update_angle's centroid pivoting is for, and not re-run
        through collision avoidance again (it's already been resolved
        continuously throughout the drag that led here -- see
        _resolve_collision).
        """
        target_angle = _angle.Angle.from_quat(quat.tolist())

        self._position.unbind(self._update_position)
        self._angle.unbind(self._update_angle)
        try:
            self._position += position - self._position
            self._write_angle(target_angle)
        finally:
            self._position.bind(self._update_position)
            self._angle.bind(self._update_angle)

        self._compute_obb()
        self._compute_aabb()
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()
        self.editor3d.Refresh(False)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: "_wire.Wire", mouse_pos: _point.Point
    ) -> _Union["_wire_service_loop.WireServiceLoop", None]:
        """Fixed-wire service-loop placement, ported from
        handlers.wire_service_loop_handler.AddWireServiceLoopHandler --
        only ever started from a wire's own context menu, never a
        toolbar tool. *wire* is split immediately (before the real
        preview object is even constructed -- see
        add_handlers.editor_3d.wire_service_loop's own module docstring
        for why), so there is no placeholder-preview phase here.
        """
        from ...add_handlers.editor_3d import wire_service_loop as _add_wsl
        from .. import wire_service_loop as _wsl_facade

        canvas = mainframe.editor3d.editor
        ptables = mainframe.project.ptables

        position, wire_angle, seg_idx = wire.obj3d.get_closest_point(mouse_pos)
        if position is None or wire_angle is None:
            return None

        preview_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))

        q_arr = np.array(wire_angle.as_quat_float, dtype=np.float64)

        p_start_db = ptables.pjt_points3d_table.insert(*position.as_float)
        p_stop_db = ptables.pjt_points3d_table.insert(*position.as_float)

        part = wire.db_obj.part
        name = f'{part.manufacturer.name} {part.part_number}'

        loop_db = ptables.pjt_wire_service_loops_table.insert(
            wire.db_obj.part_id, name,
            p_start_db.db_id, p_stop_db.db_id,
            wire.db_obj.circuit_id,
            True, q_arr)

        if wire.db_obj.operating_temp is not None:
            loop_db.operating_temp = wire.db_obj.operating_temp

        with mainframe.editor3d.context:
            split_state = _add_wsl.split_wire_for_loop(
                mainframe, wire, p_start_db.db_id, p_stop_db.db_id, seg_idx)

            facade = _wsl_facade.WireServiceLoop(mainframe, loop_db)
            facade.identify(preview_material)

            facade.set_siblings(split_state.wire1, split_state.wire2)
            split_state.wire1.set_sibling(facade, split_state.wire1.obj3d.stop_position)
            split_state.wire2.set_sibling(facade, split_state.wire2.obj3d.start_position)

            facade.obj3d.begin_move_session()

        handler = _add_wsl.WireServiceLoop(canvas, facade, split_state)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import wire_service_loop as _add_wsl  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_wsl.WireServiceLoop):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self) -> "WireServiceLoopMenu":
        """Return the context menu.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireServiceLoopMenu(self.mainframe.editor3d.editor, self)

    @property
    @_check_types.do
    def start_position(self) -> _point.Point:
        """Wire start position (Point instance)"""
        return self._p1

    @property
    @_check_types.do
    def stop_position(self) -> _point.Point:
        """Wire stop position (Point instance)"""
        return self._p2

    @property
    @_check_types.do
    def centroid(self) -> _point.Point:
        """World-space centroid of the loop (a new Point, not shared) -- the
        point it turns about under an ordinary rotation (see _update_angle),
        and so where the rotation rings are centered.
        """
        centroid = self._world_centroid()

        return _point.Point(float(centroid[0]), float(centroid[1]), float(centroid[2]))

    @property
    @_check_types.do
    def can_roll_on_wire(self) -> bool:
        """Whether the wires on both sides of the loop are there to roll it
        about (they are not while a project is still loading its wires).
        """
        return self._wire_points(self._attached_wires()) is not None

    @_check_types.do
    def begin_wire_roll(self) -> WireRoll | None:
        """Freeze the loop's present pose as the start of a roll about the
        wire it sits in (see WireRoll); None when :attr:`can_roll_on_wire` is
        False.
        """
        points = self._wire_points(self._attached_wires())
        if points is None:
            return None

        before, after = points
        start = self._position.as_numpy.astype(np.float64)

        axis, pivot = _wire_pivot(before, after, start, self._implied_stop())

        return WireRoll(axis, pivot, self._angle.as_matrix_numpy.astype(np.float64), start)

    @_check_types.do
    def roll_to(self, roll: WireRoll, degrees: float) -> None:
        """Put the loop *degrees* round the wire from the pose *roll* froze.

        Nothing is searched or avoided: the roll the user drags is the roll
        the loop gets (the nearest-clear-roll search belongs to placing a
        loop). Written through _apply_resolved so the attached wires follow
        the start point and the stop point is re-derived from the mesh.
        """
        start, angle = roll.pose(degrees)

        self._apply_resolved(start, np.array(angle.as_quat_float, dtype=np.float64))
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()
        self.editor3d.Refresh(False)

    @_check_types.do
    def start_wire_roll(self) -> None:
        """Select this loop and show the single ring that rolls it about the
        wire (rotation_handlers.rotation_rings.WireRollRings), in place of
        whatever rotation gizmo is up.
        """
        from ...rotation_handlers import rotation_rings as _rotation_rings  # NOQA -- avoid a cycle at import time

        # The menu entry is disabled without wires either side, but this runs
        # a tick after the click, and the wires can have gone by then
        if not self.can_roll_on_wire:
            return

        if self.mainframe.get_selected() is not self.parent:
            _menu_ops.select_object(self)

        if self._active_handler is not None:
            self._active_handler.delete()
            self._active_handler = None

        editor = self.editor3d.editor

        self._active_handler = _rotation_rings.WireRollRings(editor, self.parent)
        self._rotation_just_armed = False
        editor.active_handler_obj = self
        self.editor3d.Refresh(False)


@capturable()
class WireServiceLoopStripe(_base_3d.Base3D):
    """Represent a wire stripe in :mod:`harness_designer.objects.objects_3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __dump_schema__ = (
        Attr('_wireserviceloop', severity=2),
    )

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", wireserviceloop: WireServiceLoop, color: _color.Color, scale: _point.Point,
                 angle: _angle.Angle, position: _point.Point):
        """Initialise the :class:`WireStripe` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param wire: Value for ``wire``.
        :type wire: :class:`Wire`
        :param color: Value for ``color``.
        :type color: :class:`_color.Color`
        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        # Already big enough after _ensure_stripe_capacity -- this just
        # fetches the resulting handle (a cheap no-op fast path, see
        # create_vbo).
        vbo = _cylinder_helix.create_stripe_vbo()
        material = _materials.Plastic(color)
        self._wireserviceloop = wireserviceloop

        stripe_scale = _point.Point(scale.x, scale.y, scale.z)
        super().__init__(parent, None, vbo, angle, position, stripe_scale, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        """Always smooth-shaded -- the helix is a swept curved surface with
        no flat faces, so there's no reason for this to ever be flat (see
        Base3D._render_geometry, which defaults to flat shading when a
        subclass doesn't define this)."""
        return True

    @_check_types.do
    def _compute_obb(self) -> None:
        """No-op: the stripe has no independent geometry of its own. See
        the _obb property below."""
        pass

    @_check_types.do
    def _compute_aabb(self) -> None:
        """See _compute_obb."""
        pass

    @property
    @_check_types.do
    def _obb(self) -> np.ndarray:
        """Always the wire's current OBB array -- read-only everywhere
        obb/aabb are used (hit-testing, debug overlay boxes), so there's
        never a need for the stripe to hold its own copy."""
        return self._wireserviceloop.obb

    @_obb.setter
    @_check_types.do
    def _obb(self, value: np.ndarray) -> None:
        # Base3D.__init__ assigns this once before calling _compute_obb();
        # the wire is the source of truth, so the write is discarded.
        pass

    @property
    @_check_types.do
    def _aabb(self) -> np.ndarray:
        """See _obb."""
        return self._wireserviceloop.aabb

    @_aabb.setter
    @_check_types.do
    def _aabb(self, value: np.ndarray) -> None:
        pass

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """Recompute (copy) OBB/AABB from the wire; the wire's own
        _update_position already triggers a repaint, so this doesn't need
        its own Refresh() call.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        """See _update_position.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    @_check_types.do
    def _update_scale(self, scale: _point.Point) -> None:
        """See _update_position.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    @property
    @_check_types.do
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool) -> None:
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value


class WireServiceLoopMenu(QtWidgets.QMenu):
    """Represent a wire service loop menu in :mod:`harness_designer.objects.objects_3d.wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", selected: "WireServiceLoop"):
        """Initialise the :class:`WireServiceLoopMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Rotate on Wire')
        action.setEnabled(selected.can_roll_on_wire)
        action.triggered.connect(self.on_rotate_on_wire)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_wire(self) -> None:
        """Start placing a wire using this service loop's part type."""
        from . import wire as _wire_3d

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        @_check_types.do
        def _do() -> None:
            _wire_3d.Wire.start_add(mainframe, preset_part_id=part_id)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_rotate_on_wire(self) -> None:
        """Show the single ring that rolls this service loop about its wire."""
        selected = self.selected

        @_check_types.do
        def _do() -> None:
            selected.start_wire_roll()

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_trace_circuit(self) -> None:
        """Highlight every object on this service loop's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self) -> None:
        """Make this wire service loop the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self) -> None:
        """Arm clone mode using this wire service loop as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this wire service loop from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this wire service loop's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
