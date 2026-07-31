# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

import numpy as np
from OpenGL import GL
from PySide6.QtWidgets import QMenu

from . import base2d as _base2d
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


Config = _config.Config.editor2d


class Wire(_base2d.Base2D):
    """
    2D representation of a wire for schematic view

    Renders as a cylinder between its two endpoints -- the *same* shared
    ``shapes/cylinder.py`` mesh ``objects3d/wire.py``'s ``Wire`` uses,
    positioned at the start point and scaled/rotated to reach the stop
    point, plus (if the part has a stripe color) the *same* shared
    growable helix stripe mesh (``shapes/helix.py``) that wire uses too
    -- rendered as an extra (see :meth:`render_extras`), clipped to this
    segment via the ``stripeClipStart``/``stripeClipStop`` uniforms
    ported into ``gl/shaders/schematic2d.py`` for this purpose (mirrors
    ``gl/shaders/faces.py``'s mechanism exactly, minus the geometry-
    shader floor-reflection step that shader has and this one doesn't
    need). The ``schematic2d`` vertex shader already does the full
    3D transform (quaternion rotation, scale, translation) before
    projecting down to 2D -- there's no need for a flat-only mesh here
    the way ``objects2d/housing.py``'s rectangle/``objects2d/cavity.py``'s
    text are, since a cylinder viewed edge-on from directly above already
    reads as a plain rectangle.

    Unlike the 3D editor's real ``od_mm``, every wire renders at the same
    fixed width (``Config.editor2d.wire.diameter``); unlike 3D's
    ``stripe_clip_start``/``stripe_clip_stop`` (calibrated to real 3D
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

        self._p1 = db_obj.start_position2d
        self._p2 = db_obj.stop_position2d

        material = _materials.Generic(self._part.color.ui)

        stripe_color = self._part.stripe_color
        self._stripe_material = (
            _materials.Generic(stripe_color.ui) if stripe_color is not None else None)

        diameter = Config.wire.diameter
        self._length = self._calc_length()
        scale = _point.Point(diameter, diameter, self._length)

        # No angle2d column on PJTWire -- rotation is fully derived from
        # the two endpoints (see _recalculate_geometry), same reason
        # objects2d/splice.py's Splice/objects2d/wire_layout.py's
        # WireLayout use a static, unbound identity Angle.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        with parent.mainframe.editor2d.editor.context:
            vbo = _cylinder.create_vbo()

            if self._stripe_material is not None:
                _helix.create_vbo(self._length)

            # Base2D.__init__ (below) already binds self._p1 (passed as
            # position) to _update_position -- this covers the other
            # endpoint, so either one moving recomputes geometry.
            self._p2.bind(self._update_position)

            super().__init__(parent, db_obj, vbo, angle, self._p1, scale, material)

            self._recalculate_geometry()

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
        initial scale before Base2D.__init__ runs (self.db_obj isn't set
        yet) -- see objects3d/wire.py's Wire._calc_length for the same
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
        fresh in render()/render_extras from _segment_transforms(); this
        only maintains the aggregate values anything outside this class
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
        stacked into one array -- mirrors objects3d/wire.py's Wire of
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
            # See objects3d/wire.py's Wire._segment_world_corners -- same
            # degenerate (all-zero-length) fallback.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    @_check_types.do
    def _compute_obb(self):
        """Union AABB across every sub-segment -- see objects3d/wire.py's
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
        ``objects3d/wire.py``'s ``Wire._update_position`` exactly (this
        wire's own ``numpy_position`` cache is never read; every point is
        read fresh from its live Point object every time, so there's
        nothing for the inherited ``BaseVar`` implementation to usefully
        update here).
        """
        self._recalculate_geometry()

    @_check_types.do
    def render(self, program, pos_loc, rot_loc, scale_loc, normal_loc):
        """Render every sub-segment of the wire's current 2D path,
        mirroring ``objects3d/wire.py``'s ``Wire.render`` -- temporarily
        points this object at each segment's own position/angle/scale
        before delegating to the base class's single-transform draw call,
        once per segment.
        """
        real_position, real_angle, real_scale = self._position, self._angle, self._scale

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render(program, pos_loc, rot_loc, scale_loc, normal_loc)

        self._position, self._angle, self._scale = real_position, real_angle, real_scale

    @_check_types.do
    def render_extras(self, program, pos_loc, rot_loc, scale_loc, normal_loc):
        """Render this wire's stripe (if its part has a stripe color) as
        a clipped window into the shared helix mesh, once per sub-segment
        -- see the class docstring. Piggybacks on this wire's own render
        pass, same as ``objects3d/wire.py``'s ``WireStripe`` (not a
        separately-registered scene object; nothing else ever calls this
        for it).
        """
        if self._stripe_material is None or self._position is None:
            return

        stripe_vbo = _helix.create_vbo(self._length)

        start_loc = GL.glGetUniformLocation(program, 'stripeClipStart')
        stop_loc = GL.glGetUniformLocation(program, 'stripeClipStop')

        self._stripe_material.set(program)
        GL.glUniform1i(normal_loc, 0)

        stripe_offset = 0.0
        for seg_position, seg_angle, _seg_scale, seg_len in self._segment_transforms():
            GL.glUniform4f(rot_loc, *[float(str(v)) for v in seg_angle.as_quat_numpy.tolist()])
            GL.glUniform3f(scale_loc, *self._scale.as_float)
            GL.glUniform3f(pos_loc, seg_position.x, 0.0, seg_position.z)

            GL.glUniform1f(start_loc, stripe_offset)
            GL.glUniform1f(stop_loc, stripe_offset + seg_len)

            stripe_vbo.render()

            stripe_offset += seg_len

        GL.glUniform1f(start_loc, 0.0)
        GL.glUniform1f(stop_loc, 0.0)


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects2d.wire`.

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
