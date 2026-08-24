# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

import numpy as np
from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import config as _config
from ...gl import materials as _materials
from ... import utils as _utils
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire
    from ...gl import shaders as _shaders


Config = _config.Config.editor_schematic


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
        of its own in this view."""
        points = [self._p1.as_numpy]
        for waypoint in self.db_obj.waypoints2d:
            points.append(waypoint.point.as_numpy)
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

            seg_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
            seg_angle.y = math.degrees(math.atan2(dx, dz))
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
            self._angle.y = math.degrees(math.atan2(dx, dz))

        self._compute_obb()
        self._compute_aabb()

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

        all_corners = []
        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            corners = local_corners * seg_scale.as_numpy
            corners = corners @ seg_angle
            corners = corners + seg_position.as_numpy
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

        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        self._obb = np.array([
            [mins[0], mins[1], mins[2]], [mins[0], mins[1], maxs[2]],
            [mins[0], maxs[1], mins[2]], [mins[0], maxs[1], maxs[2]],
            [maxs[0], mins[1], mins[2]], [maxs[0], mins[1], maxs[2]],
            [maxs[0], maxs[1], mins[2]], [maxs[0], maxs[1], maxs[2]],
        ], dtype=np.float32)

    @_check_types.do
    def _compute_aabb(self):
        """See _compute_obb -- same union-of-segments envelope."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

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
        self._recalculate_geometry()

    @_check_types.do
    def set_stop_position(self, point: _point.Point) -> None:
        """See :meth:`set_start_position`."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
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

        new_wp = ptables.pjt_points2d_table.insert(x, z, wire_id=self.db_obj.db_id, idx=idx)
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
        # auto-router, objects_schematic/wire_routing.py, only ever produces
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
        real_position, real_angle, real_scale = self._position, self._angle, self._scale

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render(shaders)

        self._position, self._angle, self._scale = real_position, real_angle, real_scale

        if self._stripe_material is None or self._position is None or not self.is_visible:
            return

        faces_program = shaders.faces

        with faces_program:
            stripe_vbo = _helix.create_vbo(self._length)

            self._stripe_material.set(faces_program)

            stripe_offset = 0.0
            for seg_position, seg_angle, _seg_scale, seg_len in self._segment_transforms():
                faces_program.stripe_clip_start = stripe_offset
                faces_program.stripe_clip_stop = stripe_offset + seg_len

                stripe_vbo.render(
                    faces_program,
                    _point.Point(seg_position.x, 0.0, seg_position.z), seg_angle, self._scale, self.smooth)

                stripe_offset += seg_len

            faces_program.stripe_clip_start = 0.0
            faces_program.stripe_clip_stop = 0.0


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
