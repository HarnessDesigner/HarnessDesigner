# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import math

import numpy as np
from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import config as _config
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import utils as _utils
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire
    from ...gl import shaders as _shaders
    from .. import terminal as _terminal_facade
    from .. import splice as _splice_facade
    from ... import ui as _ui


Config = _config.Config.editor_schematic


# Segment angles are shared, not built per segment. Building one
# (``Angle.from_euler`` then the ``y`` setter) runs quaternion math in Decimal
# and costs about 0.8 ms; a wire recomputes its geometry -- which walks every
# segment several times -- for every waypoint or endpoint that moves, so a
# drag was spending nearly all of its time here (a profile of 20 drag events:
# 95% inside this). Routed wires are orthogonal, so there are only a handful
# of distinct yaws, and a lookup costs about half a microsecond.
#
# Sharing is safe: a segment angle is only ever read (rendering, and
# rotating the OBB/AABB corners), never modified -- ``_recalculate_geometry``
# writes to the wire's OWN angle, which is a different object.
_YAW_ANGLES: dict[float, _angle.Angle] = {}
_MAX_YAW_ANGLES = 512

# How far (degrees) a wire's own aggregate angle may lag behind its start->stop
# chord before it is brought up to date -- see Wire._recalculate_geometry.
_CHORD_YAW_TOLERANCE = 0.05


def _yaw_angle(degrees: float) -> _angle.Angle:
    """A shared :class:`~harness_designer.geometry.angle.Angle` of *degrees*
    about Y. Keyed to 0.001 degree -- on a 1 m wire that is under 0.02 mm,
    and the corners it rotates are float32 anyway."""
    key = round(degrees, 3)
    angle = _YAW_ANGLES.get(key)

    if angle is None:
        if len(_YAW_ANGLES) >= _MAX_YAW_ANGLES:
            # Only arbitrary (hand-dragged, non-orthogonal) wires get here.
            _YAW_ANGLES.clear()

        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        angle.y = key
        _YAW_ANGLES[key] = angle

    return angle


_YAW_MATRICES: dict[float, np.ndarray] = {}
_IDENTITY = np.identity(3, dtype=np.float32)


def _yaw_matrix(degrees: float) -> np.ndarray:
    """The 3x3 float32 matrix ``corners @ matrix`` rotates row-vector corners
    by, for the shared angle :func:`_yaw_angle` returns for *degrees*.

    ``points @ angle`` goes through the Angle's Decimal quaternion (about
    0.1 ms a call, several times per wire per frame); a matrix product is a
    microsecond. Rotating the identity gives the matrix itself."""
    key = round(degrees, 3)
    matrix = _YAW_MATRICES.get(key)

    if matrix is None:
        if len(_YAW_MATRICES) >= _MAX_YAW_ANGLES:
            _YAW_MATRICES.clear()

        matrix = np.asarray(_IDENTITY @ _yaw_angle(degrees), dtype=np.float32)
        _YAW_MATRICES[key] = matrix

    return matrix


class Wire(_base_schematic.BaseSchematic):
    """
    2D representation of a wire for schematic view

    Renders as a cylinder between its two endpoints -- the *same* shared
    ``shapes/cylinder.py`` mesh ``objects_3d/wire.py``'s ``Wire`` uses,
    positioned at the start point and scaled/rotated to reach the stop
    point, plus (if the part has a stripe color) the *same* shared
    growable helix stripe mesh (``shapes/helix.py``) that wire uses too
    -- rendered as part of the same pass (see :meth:`render`), clipped to this
    segment via the ``stripeClipStart``/``stripeClipStop`` uniforms
    ported into ``gl/shaders/schematic2d.py`` for this purpose (mirrors
    ``gl/shaders/faces.py``'s mechanism exactly, minus the geometry-
    shader floor-reflection step that shader has and this one doesn't
    need). The ``schematic2d`` vertex shader already does the full
    3D transform (quaternion rotation, scale, translation) before
    projecting down to 2D -- there's no need for a flat-only mesh here
    the way ``objects_schematic/housing.py``'s rectangle/``objects_schematic/cavity.py``'s
    text are, since a cylinder viewed edge-on from directly above already
    reads as a plain rectangle.

    Renders at a fixed ``Config.editor_schematic.wire.diameter`` -- NOT
    the part's real ``od_mm`` the way ``objects_3d/wire.py``'s ``Wire``
    does -- so gauge is not visually distinguishable in the schematic
    (every 2D wire reads the same thickness regardless of part); unlike
    3D's ``stripe_clip_start``/``stripe_clip_stop`` (calibrated
    to real 3D
    routing length and chained across split segments so the phase never
    jumps at a splice), each 2D segment's stripe starts fresh at its own
    beginning -- the 2D schematic's endpoint distances are laid out
    positions, not physical lengths, so there's no meaningful shared
    phase to preserve across a chain here.

    Wire Connection Rules:
    - Wire endpoints can ONLY attach to: Terminals, Splices, or WireLayouts (handles)
    - WireLayouts (handles) can be added along the wire for positioning
    """
    _parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire"

    # The chord yaw this wire's own angle was last set to (infinity so the very
    # first recompute always sets it).
    _chord_yaw: float = float('inf')

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        self._part = db_obj.part
        self._waypoint_points = []
        self._segment_pool = parent.mainframe.bounds_manager.editor_schematic.segments

        # Extra interior (x, z) bends shown between the last real waypoint and
        # this wire's live stop point while it is being drawn -- the preview of
        # what the auto-router would lay out if the wire were ended right now
        # (see add_handlers.editor_schematic.wire.Wire._preview_route_to and
        # :meth:`set_preview`). Purely a display list: never written to the
        # database, never registered with the segment pool (:meth:`_register_
        # segments` -- an obstacle for OTHER wires' own routing only once it is
        # real), and always empty once the wire isn't being interactively drawn.
        self._preview_points: list[tuple[float, float]] = []

        self._p1 = db_obj.start_position2d
        self._p2 = db_obj.stop_position2d

        material = _materials.Generic(self._part.color.ui)

        stripe_color = self._part.stripe_color
        self._stripe_material = (
            _materials.Generic(stripe_color.ui) if stripe_color is not None else None)

        diameter = Config.object_sizes.wire.diameter
        self._length = self._calc_length()
        scale = _point.Point(diameter, diameter, self._length)

        # No angle2d column on PJTWire -- rotation is fully derived from
        # the two endpoints (see _recalculate_geometry), same reason
        # objects_schematic/splice.py's Splice/objects_schematic/wire_layout.py's
        # WireLayout use a static, unbound identity Angle.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        with parent.mainframe.editor2d.editor.context:
            vbo = _cylinder.create_vbo()

            if self._stripe_material is not None:
                _helix.create_vbo(self._length)

            # BaseSchematic.__init__ (below) already binds self._p1 (passed as
            # position) to _update_position -- this covers the other
            # endpoint, so either one moving recomputes geometry.
            self._p2.bind(self._update_position)

            super().__init__(parent, db_obj, vbo, angle, self._p1, scale, material)

            self._bind_waypoints()
            self._recalculate_geometry()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def _segments(self) -> list[tuple]:
        """Every (p1, p2) sub-segment from start, through each interior
        2D waypoint in idx order, to stop -- as numpy arrays. A wire with
        no interior 2D waypoints (still the common case -- the schematic
        editor's own wire-drawing tool doesn't exist yet) is just the one
        (start, stop) pair, same as before this wire could have any bends
        of its own in this view.

        Read from ``_waypoint_points`` -- the live waypoint ``Point``
        objects, kept in step with the database by :meth:`_bind_waypoints`
        (every add / remove / reorder goes through :meth:`refresh_waypoints`)
        -- NOT from ``db_obj.waypoints2d``, which is a real SQL query. This
        runs several times per frame per wire (every render, and every
        recompute of the geometry, which fires for every waypoint or
        endpoint that moves), so a query here made a drag stutter.
        """
        points = [self._p1.as_numpy]
        points.extend(point.as_numpy for point in self._waypoint_points)
        points.extend(
            np.array([x, 0.0, z], dtype=self._p1.as_numpy.dtype)
            for x, z in self._preview_points)
        points.append(self._p2.as_numpy)

        return list(zip(points, points[1:]))

    @_check_types.do
    def _calc_length(self) -> float:
        """Straight-line seed length used only to size this wire's
        initial scale before BaseSchematic.__init__ runs (self.db_obj isn't set
        yet) -- see objects_3d/wire.py's Wire._calc_length for the same
        reasoning. _recalculate_geometry replaces this with the true,
        possibly multi-segment length once db_obj is valid."""
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        dx = b[0] - a[0]
        dz = b[2] - a[2]
        return math.sqrt(dx * dx + dz * dz)

    @_check_types.do
    def _segment_transforms(self):
        """Yield (position, angle, scale, length) for every sub-segment
        of this wire's current 2D path."""
        diameter = self._scale.x

        for seg_p1, seg_p2 in self._segments():
            dx = seg_p2[0] - seg_p1[0]
            dz = seg_p2[2] - seg_p1[2]
            seg_len = math.sqrt(dx * dx + dz * dz)
            if seg_len < 1e-6:
                continue

            seg_angle = _yaw_angle(math.degrees(math.atan2(dx, dz)))
            seg_position = _point.Point(*seg_p1)
            seg_scale = _point.Point(diameter, diameter, seg_len)

            yield seg_position, seg_angle, seg_scale, seg_len

    @_check_types.do
    def _recalculate_geometry(self):
        """Recompute this wire's total length and OBB/AABB from its
        current path -- called (via :meth:`_update_position`) whenever
        any endpoint or interior waypoint moves.

        Per-segment position/angle/scale for actual drawing are computed
        fresh in render() from _segment_transforms(); this only
        maintains the aggregate values anything outside this class
        still reads (.scale, .angle, .obb, .aabb).
        """
        total_length = 0.0
        for seg_p1, seg_p2 in self._segments():
            dx = seg_p2[0] - seg_p1[0]
            dz = seg_p2[2] - seg_p1[2]
            total_length += math.sqrt(dx * dx + dz * dz)

        if total_length < 0.001:
            return

        self._length = total_length
        self._scale.z = total_length

        if self._stripe_material is not None:
            _helix.create_vbo(self._length)

        # Aggregate angle: overall start->stop chord direction, kept only
        # for any other code reading .angle on a wire (not used for
        # drawing -- each segment computes its own, see render()).
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        dx = b[0] - a[0]
        dz = b[2] - a[2]
        chord_length = math.sqrt(dx * dx + dz * dz)
        if chord_length >= 0.001:
            # Only when it has actually turned by a visible amount. Setting it
            # is not free -- the Angle recomputes its quaternion in Decimal
            # (~0.5 ms) and then fires _update_angle (copy + negate, another
            # ~0.4 ms) -- and this runs for every waypoint or endpoint that
            # moves, several times per mouse move, while nothing DRAWS with this
            # angle (each segment has its own). 0.05 degrees is under 1 mm at
            # the end of a 1 m wire.
            chord_yaw = math.degrees(math.atan2(dx, dz))

            if abs(chord_yaw - self._chord_yaw) > _CHORD_YAW_TOLERANCE:
                self._chord_yaw = chord_yaw
                self._angle.y = chord_yaw

        self._compute_bounds()

    def _update_angle(self, angle: _angle.Angle):
        """Nothing to do: the wire's own angle isn't drawn with or hit-tested
        with (each segment has its own, and picking uses the pooled bounds),
        and :meth:`_recalculate_geometry` -- the only thing that sets it --
        recomputes the bounds itself. The inherited version recomputed them
        AGAIN, and copied and negated the angle in Decimal."""

    def _update_scale(self, scale: _point.Point):
        """See :meth:`_update_angle` -- same for the scale
        :meth:`_recalculate_geometry` sets."""

    def _compute_bounds(self) -> None:
        """OBB and AABB from ONE set of world corners (they are the same
        union-of-segments envelope -- see :meth:`_compute_obb`)."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        self._store_obb(corners)
        self._aabb[:] = _utils.adjust_aabb(corners)

    @_check_types.do
    def _segment_world_corners(self):
        """World-space AABB corners (8 per segment) for every sub-segment,
        stacked into one array -- mirrors objects_3d/wire.py's Wire of
        the same name, the shared building block for _compute_obb/
        _compute_aabb's union-of-segments envelope."""
        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]
        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        local_corners = np.array([
            [x1, y1, z1], [x1, y1, z2],
            [x1, y2, z1], [x1, y2, z2],
            [x2, y1, z1], [x2, y1, z2],
            [x2, y2, z1], [x2, y2, z2]
        ], dtype=np.float32)

        diameter = float(self._scale.x)
        all_corners = []
        for seg_p1, seg_p2 in self._segments():
            dx = seg_p2[0] - seg_p1[0]
            dz = seg_p2[2] - seg_p1[2]
            seg_len = math.sqrt(dx * dx + dz * dz)
            if seg_len < 1e-6:
                continue

            scale = np.array([diameter, diameter, seg_len], dtype=np.float32)
            corners = local_corners * scale
            corners = corners @ _yaw_matrix(math.degrees(math.atan2(dx, dz)))
            corners = corners + seg_p1
            all_corners.append(corners)

        if not all_corners:
            # See objects_3d/wire.py's Wire._segment_world_corners -- same
            # degenerate (all-zero-length) fallback.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    @_check_types.do
    def _compute_obb(self):
        """Union AABB across every sub-segment -- see objects_3d/wire.py's
        Wire._compute_obb for why this degenerates to the same envelope
        as _compute_aabb rather than a single tight rotated box."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        self._store_obb(corners)

    def _store_obb(self, corners: np.ndarray) -> None:
        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        # The pool's own corner order (utils.bounding_boxes.compute_obb):
        # 1 toggles x, 3 toggles y, 4 toggles z -- NOT the order an AABB's
        # corners are built in. The pool derives the box's three edge axes
        # from corners 1/3/4, so the other order made a skewed box centered
        # a whole z-extent off, and a click on the low-z half of a wire
        # missed the OBB pass (which, finding some other wire's phantom box,
        # then skipped the AABB fallback -- see gl.object_picker.find_object).
        obb = np.array([
            [mins[0], mins[1], mins[2]], [maxs[0], mins[1], mins[2]],
            [maxs[0], maxs[1], mins[2]], [mins[0], maxs[1], mins[2]],
            [mins[0], mins[1], maxs[2]], [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], maxs[2]], [mins[0], maxs[1], maxs[2]],
        ], dtype=np.float32)

        if self._obb is None:
            self._obb = self._obb_manager.read(self._obb_index)
            self._obb[:] = obb
        else:
            self._obb[:] = obb

    @_check_types.do
    def _compute_aabb(self):
        """See _compute_obb -- same union-of-segments envelope."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        aabb = _utils.adjust_aabb(corners)

        self._aabb[:] = aabb

    @_check_types.do
    def hit_test_step3(self, ray_origin, ray_dir):
        """Precise per-segment mesh hit test (see ``BaseVar.hit_test_step3``):
        tests every sub-segment's own transformed triangles individually,
        instead of the inherited single-transform version -- which tests
        against this wire's own mesh placed at its AGGREGATE chord
        position/angle/scale (the straight line from true start to true
        stop, ignoring every bend between them). For anything but a
        single unbent segment that chord doesn't correspond to any
        actually-rendered geometry at all, so a click anywhere on a bent
        wire's real, visible path missed every triangle and this object
        was never actually pickable (confirmed 2026-09-22, Kevin: wire
        selection in the schematic editor doesn't work at all).

        ``objects_3d.wire.Wire`` already overrides this the same way, for
        the exact same reason -- this mirrors it here, using
        ``_yaw_matrix`` (a real rotation matrix, ready for a bare
        ``@`` multiply) rather than ``_segment_transforms``'s own
        ``_yaw_angle`` (built for the renderer's position/angle/scale
        call convention, not a bare matrix multiply) -- same distinction
        :meth:`_segment_world_corners` already draws for the identical
        reason.
        """
        if self._vbo is None:
            return False

        vertices_local = self._vbo.vertices.reshape(-1, 3)
        if len(vertices_local) % 3:
            return False

        diameter = float(self._scale.x)

        for seg_p1, seg_p2 in self._segments():
            dx = seg_p2[0] - seg_p1[0]
            dz = seg_p2[2] - seg_p1[2]
            seg_len = math.sqrt(dx * dx + dz * dz)
            if seg_len < 1e-6:
                continue

            scale = np.array([diameter, diameter, seg_len], dtype=np.float32)
            matrix = _yaw_matrix(math.degrees(math.atan2(dx, dz)))

            ray_object = ray_origin - seg_p1

            vertices = (vertices_local * scale) @ matrix
            verts = vertices.reshape(-1, 3, 3)

            if self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts):
                return True

        return False

    @_check_types.do
    def _update_position(self, _position: _point.Point):
        """Recompute geometry immediately whenever any endpoint or
        interior waypoint moves -- mirrors
        ``objects_3d/wire.py``'s ``Wire._update_position`` exactly (this
        wire's own ``numpy_position`` cache is never read; every point is
        read fresh from its live Point object every time, so there's
        nothing for the inherited ``BaseVar`` implementation to usefully
        update here).
        """
        self._recalculate_geometry()

    @_check_types.do
    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this wire's own 2D start end to *point* entirely --
        mirrors ``objects_3d/wire.py``'s ``Wire.set_start_position`` (same
        "caller already computed where this should be, nothing here
        moves it" contract; the old start point is left alone as an
        independent point). Also updates ``self._position`` --
        ``BaseVar``'s own position, an alias for ``self._p1`` set at
        construction -- since OBB/AABB, generic drag, etc. all read that,
        not ``self._p1`` directly.
        """
        self._p1.unbind(self._update_position)
        self._p1 = point
        self._position = point
        self._p1.bind(self._update_position)
        self._register_segments()
        self._recalculate_geometry()

    @_check_types.do
    def set_stop_position(self, point: _point.Point) -> None:
        """See :meth:`set_start_position`."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
        self._register_segments()
        self._recalculate_geometry()

    @_check_types.do
    def _bind_waypoints(self):
        """(Re)bind every current interior 2D waypoint's own Point to
        :meth:`_update_position`, so dragging one recomputes this wire's
        geometry live -- mirrors ``objects_3d/wire.py``'s
        ``Wire._bind_waypoints``.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        self._waypoint_points = [wp.point for wp in self.db_obj.waypoints2d]

        for point in self._waypoint_points:
            point.bind(self._update_position)

        self._register_segments()

    @_check_types.do
    def _register_segments(self) -> None:
        """(Re)register this wire's current path -- start, every interior
        waypoint, stop -- with the schematic view's segment pool
        (``bounds_manager.editor_schematic.segments``), which the router
        reads its wire-to-wire lane obstacles from. The pool references
        each Point's live ``as_numpy`` buffer, so a plain move needs
        nothing; only a change in the SHAPE of the path (waypoints
        added/removed, an endpoint repointed) needs this again.
        """
        buffers = [self._p1.as_numpy]
        buffers.extend(point.as_numpy for point in self._waypoint_points)
        buffers.append(self._p2.as_numpy)

        self._segment_pool.register(self, buffers)

    @_check_types.do
    def set_preview(self, points: list[tuple[float, float]] | None) -> None:
        """Show *points* (interior ``(x, z)`` bends, in order) as extra
        segments between the last real waypoint and this wire's live stop
        point -- see :attr:`_preview_points`. ``None``/empty clears it back
        to the plain single dangling segment. Only this wire's own render
        geometry/bounds are touched; the segment pool other wires' own
        routing reads obstacles from is untouched (see :attr:`_preview_points`'s
        own docstring), so a preview is never itself an obstacle.
        """
        self._preview_points = list(points) if points else []

        self._recalculate_geometry()
        self.editor2d.Refresh(False)

    @_check_types.do
    def _delete(self):
        self._segment_pool.release(self)
        super()._delete()

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this wire's own
        2D waypoint rows change (added, removed, or reordered) so live
        callbacks and geometry all catch up -- mirrors
        ``objects_3d/wire.py``'s ``Wire.refresh_waypoints``.
        """
        self._bind_waypoints()
        self._recalculate_geometry()
        self.editor2d.Refresh()

    @_check_types.do
    def _segment_chain(self) -> tuple[list, list[bool]]:
        """This wire's current path as ``(points, is_fixed)`` -- live
        Point objects ``[start, wp0, wp1, ..., stop]`` and, for each,
        whether it's a fixed endpoint (index 0/-1, this wire's own true
        start/stop -- attached to a Terminal/Splice, must never be moved
        directly) or a draggable interior waypoint.
        """
        waypoints = self.db_obj.waypoints2d
        points = [self._p1] + [wp.point for wp in waypoints] + [self._p2]
        is_fixed = [True] + [False] * len(waypoints) + [True]
        return points, is_fixed

    @staticmethod
    @_check_types.do
    def _dist_to_segment(px: float, pz: float, ax: float, az: float,
                         bx: float, bz: float) -> float:
        dx, dz = bx - ax, bz - az
        length_sq = dx * dx + dz * dz

        if length_sq < 1e-9:
            t = 0.0
        else:
            t = ((px - ax) * dx + (pz - az) * dz) / length_sq
            t = max(0.0, min(1.0, t))

        cx, cz = ax + t * dx, az + t * dz
        return math.hypot(px - cx, pz - cz)

    @_check_types.do
    def _insert_waypoint(self, x: float, z: float, at_start: bool) -> _point.Point:
        """Insert a real, persisted interior waypoint at *(x, z)* --
        at the very start of the chain (``at_start=True``, renumbering
        every existing waypoint's ``idx`` up by one) or the very end
        (``at_start=False``, appended after every existing one).
        Rebinds/recomputes via :meth:`refresh_waypoints` before
        returning the new waypoint's own live Point.
        """
        ptables = self.mainframe.project.ptables
        waypoints = self.db_obj.waypoints2d

        if at_start:
            for wp in waypoints:
                wp.idx = wp.idx + 1
            idx = 0
        else:
            idx = len(waypoints)

        new_wp = ptables.pjt_points2d_table.insert(x, 0.0, z, wire_id=self.db_obj.db_id, idx=idx)
        self.refresh_waypoints()

        return new_wp.point

    @_check_types.do
    def begin_segment_drag(self, world_pos: _point.Point):
        """Start dragging whichever of this wire's current segments is
        nearest *world_pos* -- promoting either bounding end to a real,
        independent waypoint first if it's currently this wire's own
        fixed start/stop (so the Terminal/Splice it's attached to is
        never moved by the drag) -- and return the ``(point_a, point_b,
        horizontal)`` session :meth:`update_segment_drag` needs for the
        rest of the drag. ``None`` if this wire has no path at all yet.
        """
        points, is_fixed = self._segment_chain()
        if len(points) < 2:
            return None

        px, pz = world_pos.x, world_pos.z

        best_i = 0
        best_dist = None
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            dist = self._dist_to_segment(px, pz, a.x, a.z, b.x, b.z)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_i = i

        a_point, a_fixed = points[best_i], is_fixed[best_i]
        b_point, b_fixed = points[best_i + 1], is_fixed[best_i + 1]

        # Orientation is read from the two ORIGINAL (possibly-fixed)
        # points, before either is promoted below -- every existing
        # segment is already exactly horizontal or vertical (the
        # auto-router, wire_routing/routing.py, only ever produces
        # orthogonal paths), so this is stable regardless of promotion.
        horizontal = abs(a_point.z - b_point.z) < 1e-6

        if a_fixed:
            a_point = self._insert_waypoint(a_point.x, a_point.z, at_start=True)

        if b_fixed:
            b_point = self._insert_waypoint(b_point.x, b_point.z, at_start=False)

        return a_point, b_point, horizontal

    @staticmethod
    @_check_types.do
    def update_segment_drag(session, world_pos: _point.Point) -> None:
        """Move the dragged segment's shared perpendicular coordinate
        (both of *session*'s points, together) to *world_pos* -- motion
        parallel to the segment is ignored, since a jog has exactly one
        degree of freedom. Everything on either side of these two points
        -- another waypoint, or this wire's own untouched fixed start/
        stop -- simply changes length on the next render; nothing else
        needs updating here.
        """
        a_point, b_point, horizontal = session

        if horizontal:
            with a_point:
                a_point.z = world_pos.z
            with b_point:
                b_point.z = world_pos.z
        else:
            with a_point:
                a_point.x = world_pos.x
            with b_point:
                b_point.x = world_pos.x

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Render every sub-segment of the wire's current 2D path,
        mirroring ``objects_3d/wire.py``'s ``Wire.render`` -- temporarily
        points this object at each segment's own position/angle/scale
        before delegating to the base class's single-transform draw call,
        once per segment -- then this wire's own color stripe (if its
        part has one) as a clipped window into the shared helix mesh,
        once per segment too. The stripe pass is merged in here rather
        than kept as a separate ``render_extras()`` (which nothing ever
        called) since it only ever piggybacks on this same render pass,
        same as ``objects_3d/wire.py``'s ``WireStripe``, and needs its
        own uniform locations resolved directly (the ``stripeClipStart``/
        ``stripeClipStop`` uniforms the standard ``_render_geometry``
        pipeline doesn't know about).
        """
        # DEBUG (temporary): dump every segment's (x, z) start/stop.
        # print(f'wire {self.db_obj.db_id!r}')
        # for seg_p1, seg_p2 in self._segments():
            # print(f'    ({float(seg_p1[0]):.3f}, {float(seg_p1[2]):.3f}) -> '
                  # f'({float(seg_p2[0]):.3f}, {float(seg_p2[2]):.3f})')

        real_position, real_angle, real_scale = self._position, self._angle, self._scale

        # Built once and used for both passes below -- every entry allocates
        # an Angle and two Points.
        transforms = list(self._segment_transforms())

        for seg_position, seg_angle, seg_scale, _seg_len in transforms:
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render(shaders)

        self._position, self._angle, self._scale = real_position, real_angle, real_scale

        if self._stripe_material is None or self._position is None or not self.is_visible:
            # print()  # DEBUG (temporary)
            return

        faces_program = shaders.faces

        with faces_program:
            stripe_vbo = _helix.create_vbo(self._length)

            self._stripe_material.set(faces_program)

            stripe_offset = 0.0
            for seg_position, seg_angle, _seg_scale, seg_len in transforms:
                faces_program.stripe_clip_start = stripe_offset
                faces_program.stripe_clip_stop = stripe_offset + seg_len

                stripe_vbo.render(
                    faces_program,
                    _point.Point(seg_position.x, 0.0, seg_position.z), seg_angle, self._scale, self.smooth)

                stripe_offset += seg_len

            faces_program.stripe_clip_start = 0.0
            faces_program.stripe_clip_stop = 0.0

        # print()  # DEBUG (temporary)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", terminal: Union["_terminal_facade.Terminal", None] = None,
        splice: Union["_splice_facade.Splice", None] = None
    ) -> Union["_wire.Wire", None]:
        """Terminal/splice-pinned wire placement, ported from
        handlers.wire_handler_2d.AddWireHandler2D. Always pinned to a start
        terminal/splice (no free-space start, unlike the 3D editor's
        Wire.start_add); from there the user draws the wire by clicking
        waypoints, and ends it on a terminal/splice -- see
        add_handlers.editor_schematic.wire's own module docstring.
        """
        from ...handlers.wire_handler import terminal_wire_search_params
        from ...handlers import wire_snap as _wire_snap
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_schematic import wire as _add_wire
        from .. import wire as _wire_facade
        from PySide6.QtWidgets import QDialog, QMessageBox

        canvas = mainframe.editor2d.editor

        start = terminal if terminal is not None else splice
        if start is None:
            return None

        if terminal is not None:
            initial_params = terminal_wire_search_params(terminal)
        else:
            initial_params = None

        dlg = _part_search.SearchDialog(
            mainframe, _editor_db.WiresPage, mainframe.global_db.wires_table, 'Add Wire',
            initial_params=initial_params)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            part_id = dlg.GetValue()
        else:
            part_id = None

        dlg.deleteLater()

        if part_id is None:
            return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.wires_table[part_id]

        start_circuit_id = None
        if terminal is not None:
            ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(terminal, part)
            if not ok:
                block_msg += '\n\nDo you want to use this wire?'
                button = QMessageBox.question(mainframe, 'Incompatible Wire', block_msg)
                if button == QMessageBox.StandardButton.No:
                    return None

            start_circuit_id = terminal.db_obj.circuit_id

        # Placeholder 3D points -- overwritten immediately below by the
        # start attach, and tracked live during hover for the stop, never
        # sharing one point row between start and stop.
        start3d = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        if terminal is not None:
            initial_pos = terminal.db_obj.attach_position3d
        else:
            initial_pos = splice.obj3d.wire_position

        stop3d = ptables.pjt_points3d_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        start_pos2d = start.db_obj.position2d
        stop2d = ptables.pjt_points2d_table.insert(
            float(start_pos2d.x), float(start_pos2d.y), float(start_pos2d.z))

        name = f'{part.manufacturer.name} {part.part_number}'

        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, start_circuit_id,
            start3d.db_id, stop3d.db_id,
            None, stop2d.db_id,
            True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        handler = _add_wire.Wire(canvas, facade, part, stop2d, start)

        if terminal is not None:
            # terminal.add_wire always performs the attachment -- leaves
            # the stale placeholder for the caller to clean up.
            terminal.add_wire(facade, 'start')
            ptables.pjt_points3d_table[start3d.db_id].delete()
        else:
            handler._attach_splice(splice, 'start')  # NOQA

        # The handler needs the start attached (its terminal's exit stub is
        # part of the path being drawn).
        handler.begin()

        # Drawn from the first click on: the canvas otherwise never renders a
        # wire with a dangling end (see Canvas.add_object).
        facade.db_obj.is_visible2d = True
        canvas.add_preview_object(facade)

        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
    ) -> bool:
        """Add-session check first (see start_add), then falls through
        to this class's own existing interior-segment drag handling
        below -- not BaseSchematic's generic single-position drag, so
        this stays a full override rather than a super() call.
        """
        from ...add_handlers.editor_schematic import wire as _add_wire  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_wire.Wire):
            # A local reference, not another read of self._active_handler below
            # -- a right click with nothing left to undo cancels the session,
            # which deletes this wire's own facade; BaseVar's generic delete()
            # sees self._active_handler is this same handler and clears it AND
            # calls its own delete() (idempotent -- cancel() already ran) right
            # there, all before this call even returns. Reading self.
            # _active_handler again afterward would find None -- checked
            # AttributeError, confirmed live 2026-09-21 (Kevin) -- ask the
            # handler itself, and only clear the slot if nothing already did.
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        if self._active_handler is not None:
            if interaction_type is _interaction.MouseInteraction.MOVE:
                self._active_handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                self._active_handler.delete()
                self._active_handler = None
                # No real drag happened -- let a plain click-release fall
                # through to the default select/deselect toggle instead of
                # being eaten here (see objects_3d.base_3d.handle_interaction).
                return had_motion

            return False

        if (
            interaction_type is not _interaction.MouseInteraction.LEFT_DOWN or
            clicked_object is not self.parent or
            self.parent.mainframe.get_selected() is not self.parent
        ):
            return False

        from ...drag_handlers.editor_schematic import wire as _drag_wire

        world_pos = self.editor2d.editor.camera.screen_to_world(current_pos)
        plan = _drag_wire.plan_wire_segment_drag(
            self.parent, (float(world_pos.x), float(world_pos.z)))
        if plan is None:
            return False

        self._active_handler = _drag_wire.Wire(self.editor2d.editor, self.parent, plan)
        return True


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects_schematic.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`WireMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Handle')
        action.triggered.connect(self.on_add_handle)

        action = self.addAction('Add Marker')
        action.triggered.connect(self.on_add_marker)

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        self.addSeparator()
        action = self.addAction('Add to Bundle')
        action.triggered.connect(self.on_add_to_bundle)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_handle(self):
        """Handle the add handle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_marker(self):
        """Handle the add marker event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_splice(self):
        """Handle the add splice event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_wire(self):
        """Handle the add wire event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_wire_service_loop(self):
        """Handle the add wire service loop event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_add_to_bundle(self):
        """Handle the add to bundle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
