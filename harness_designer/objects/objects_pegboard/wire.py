# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import numpy as np
import math

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base_pegboard as _base_pegboard
from ..objects_3d import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from ... import utils as _utils
from . import mixins as _mixins
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire
    from ...gl import shaders as _shaders


Config = _config.Config.editor_pegboard

# Real-world mm of extra headroom built into the shared stripe helix mesh
# beyond whatever's currently required (see WireStripe._ensure_stripe_capacity).
# A live drag/preview can then grow a wire's own total length without
# forcing a GPU buffer reallocation on every frame -- only once the
# overshoot itself is exhausted does the mesh actually need to regrow.
_HELIX_OVERSHOOT_MM = 1000.0


class Wire(_base_pegboard.BasePegboard, _mixins.WireTypeMixin):
    """Represent a wire in :mod:`harness_designer.objects.objects_pegboard.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire" = None

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        with parent.mainframe.editor_pegboard.context:
            self._stripe = None

            self._part = db_obj.part
            color = self._part.color.ui
            stripe_color = self._part.stripe_color
            diameter = self._part.od_mm

            # Wires hold strong references to bundles as a sanity check
            self._bundle = None

            material = _materials.Plastic(color)

            # Bare-conductor look for whichever end segment(s) crimp into a
            # terminal (see render()) -- conductor_dia_mm already falls back
            # to an AWG-derived estimate when the wire_size_dia column is
            # NULL; od_mm * 2/3 is the final fallback for a part missing both,
            # per the same ratio a stranded conductor's copper core typically
            # is of its own fully-insulated OD.
            conductor_dia = self._part.conductor_dia_mm
            if not conductor_dia:
                conductor_dia = diameter * (2.0 / 3.0)

            self._conductor_dia = conductor_dia
            self._conductor_material = _materials.Polished(self._part.core_material.color.ui)

            self._p1 = db_obj.start_position_pegboard
            self._p2 = db_obj.stop_position_pegboard

            # Live Point objects for every interior waypoint (idx order),
            # kept in sync with the DB via refresh_waypoints() -- called by
            # whichever handler adds/removes/reorders this wire's own
            # waypoints (handlers.wire_layout_handler, handlers.wire_handler,
            # objects.terminal.Terminal.add_wire).
            self._waypoint_points: list[_point.Point] = []

            self._length = self._calc_length()

            position = self._p1

            scale = _point.Point(diameter, diameter, self._length)

            # Track wires in this bundle using weak references
            # Wires hold strong references to bundles; bundles use weak refs to wires
            self._wires = []  # List of weak references to Wire objects

            self._p2.bind(self._update_position)

            vbo = _cylinder.create_vbo()
            angle = _angle.Angle.from_points(self._p1, self._p2)

            # Built before the stripe -- WireStripe's own OBB/AABB are copied
            # from this wire's, so the wire must already have real _obb/_aabb
            # attributes (set by Base3D.__init__) before WireStripe.__init__
            # (itself calling Base3D.__init__, which calls _compute_obb/_aabb)
            # can safely read them. Binding position/angle/scale here first also
            # means this wire's own _update_* callbacks (which recompute its
            # _obb/_aabb) fire before the stripe's on any later shared change.
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

            if stripe_color is not None:
                self._stripe = WireStripe(parent, self, stripe_color.ui, scale, angle, position)
                # WireStripe's db_obj is always None (it's not its own DB row --
                # see WireStripe.__init__), so Base3D.__init__ hits the
                # `except AttributeError: self._is_visible = False` branch and
                # the stripe is built permanently invisible. Sync it to the
                # wire's own just-computed visibility here.
                self._stripe.is_visible = self._is_visible

                self.pegboard.Refresh()

            # _update_angle just calls _update_position(None) — redundant since
            # both endpoints already drive recalculation via their point bindings.
            self._angle.unbind(self._update_angle)

            # self.db_obj is only valid from here on (set by Base3D.__init__
            # above) -- this is the first point waypoints3d/for_wire can be
            # queried, so the initial waypoint bind and the real (possibly
            # multi-segment) geometry recompute both happen here, not earlier.
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

    @property
    @_check_types.do
    def length(self) -> float:
        return self._length

    @_check_types.do
    def _calc_length(self):
        """Straight-line seed length used only to size this wire's
        initial scale before Base3D.__init__ runs (self.db_obj isn't
        valid yet, so this can't query waypoints3d) -- a brand new wire
        row never has any waypoints yet anyway. _recalculate_geometry
        (called at the end of __init__, and on every subsequent endpoint/
        waypoint move) replaces this with the true, possibly multi-segment
        polyline length via WireTypeMixin._segments().
        """
        x1, y1, z1 = self._p1.as_numpy.tolist()
        x2, y2, z2 = self._p2.as_numpy.tolist()

        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @_check_types.do
    def _bind_waypoints(self) -> None:
        """(Re-)bind this wire's own _update_position callback to every
        current interior waypoint's live Point, unbinding it from whatever
        set was bound before.

        Called once at construction and again (as refresh_waypoints) by
        any handler that adds/removes/reorders this wire's own waypoints,
        so live position-change callbacks always match the current set.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        self._waypoint_points = [wp.point for wp in self.db_obj.waypoints_pegboard]

        for point in self._waypoint_points:
            point.bind(self._update_position)

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this wire's own
        waypoint rows change (added, removed, or reordered) so live
        callbacks, cached length, and geometry all catch up."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.pegboard.Refresh()

    @property
    @_check_types.do
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    @_check_types.do
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2

    @_check_types.do
    def is_housing_attached(self) -> bool:
        """True if either endpoint shares a db_id with any cavity's or
        terminal's housing-derived wire-routing point (cavity.
        wire_position_pegboard, terminal.wire_position_pegboard,
        terminal.attach_position_pegboard) anywhere in the project.
        Such a wire's position is derived from its housing --
        it must not be independently draggable; the user has to move the
        housing or drag the wire's own layout instead.

        Checks the *_raw properties (no lazy point creation) so this never
        forces a wire-routing point into existence for a cavity/terminal
        that has never had one, just by asking.
        """
        start_id = self._p1.db_id[:-2]
        stop_id = self._p2.db_id[:-2]
        ids = {start_id, stop_id}

        project = self.parent.mainframe.project

        for cavity in project.cavities:
            if cavity.db_obj.wire_position_pegboard_id_raw in ids:
                return True

        for terminal in project.terminals:
            if terminal.db_obj.wire_position_pegboard_id_raw in ids:
                return True
            if terminal.db_obj.attach_position_pegboard_id_raw in ids:
                return True

        return False

    @_check_types.do
    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this wire's own start end to *point* entirely.

        Not a merge/delegation (see Point.attach for that) -- the old
        start point is left alone as an independent point (e.g. becoming
        a permanent interior waypoint the instant before this is called;
        see handlers.wire_handler.AddWireHandler._commit_waypoint, the
        only caller today), and *point* must already be exactly where
        this wire's start should be -- nothing here moves it.
        """
        self._p1.unbind(self._update_position)
        self._p1 = point
        self._p1.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def set_stop_position(self, point: _point.Point) -> None:
        """See set_start_position."""
        self._p2.unbind(self._update_position)
        self._p2 = point
        self._p2.bind(self._update_position)
        self._recalculate_geometry()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    @_check_types.do
    def _recalculate_geometry(self):
        """Compute total length, an aggregate angle, and OBB/AABB from
        the wire's current start/interior-waypoints/stop path.

        Per-segment position/angle/scale for actual drawing and hit-
        testing are computed fresh in render()/hit_test_step3 from
        WireTypeMixin._segments() -- this only maintains the aggregate
        values anything outside this class still reads (.length, .scale,
        .angle, .obb, .aabb).
        """
        segments = self._segments()

        total_length = 0.0
        for seg_p1, seg_p2 in segments:
            total_length += float(np.linalg.norm(seg_p2 - seg_p1))

        if total_length < 0.001:
            return

        self._length = total_length
        self._scale.z = total_length

        if self._stripe is not None:
            self._stripe._ensure_stripe_capacity(self.parent.mainframe, total_length)  # NOQA

        # Aggregate angle: the overall start->stop chord direction. Not
        # used for drawing (each segment computes its own), kept only for
        # any other code reading .angle on a wire.
        a = self._p1.as_numpy
        b = self._p2.as_numpy
        chord = b - a
        chord_length = float(np.linalg.norm(chord))
        if chord_length >= 0.001:
            angle = self._rotation_from_direction(chord / chord_length)
            self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _update_position(self, _: _point.Point):
        """Recompute geometry immediately, not deferred to the next
        render pass -- bound to the start/stop endpoints and every
        interior waypoint (see _bind_waypoints), so any of them moving
        keeps the wire's aggregate length/OBB/AABB and the stripe's
        mesh capacity current before the next repaint.
        """

        self._recalculate_geometry()

    @_check_types.do
    def _segment_transforms(self):
        """Yield (position, angle, scale, length) for every sub-segment
        of this wire's current path -- the values render()/hit_test_step3
        both draw/test against, computed fresh each call since a wire's
        waypoints can change at any time."""
        diameter = self._scale.x

        for seg_p1, seg_p2 in self._segments():
            seg_vec = seg_p2 - seg_p1
            seg_len = float(np.linalg.norm(seg_vec))
            if seg_len < 1e-6:
                continue

            direction = seg_vec / seg_len
            seg_angle = self._rotation_from_direction(direction)
            seg_position = _point.Point(*seg_p1)
            seg_scale = _point.Point(diameter, diameter, seg_len)

            yield seg_position, seg_angle, seg_scale, seg_len

    @_check_types.do
    def _compute_obb(self):
        """Union AABB across every sub-segment, expressed as an 8-corner
        box (same shape find_object/_ray_intersect_obb expects) -- a
        single rigid OBB has no meaningful orientation for a wire with
        more than one bend, so this degenerates to the same envelope as
        _compute_aabb rather than a tight rotated box. Conservative (a
        click near an elbow but off the actual tube can still register a
        hit) but always correct; see hit_test_step3 for the precise,
        per-segment mesh test."""
        if self._vbo is None:
            return

        corners = self._segment_world_corners()
        if corners is None:
            return

        mins = corners.min(axis=0)
        maxs = corners.max(axis=0)

        # Pool corner order (utils.bounding_boxes.compute_obb): 1 toggles x,
        # 3 toggles y, 4 toggles z -- see objects_schematic.wire.Wire.
        # _store_obb for what the AABB corner order did to picking.
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
    def _segment_world_corners(self):
        """World-space AABB corners (8 per segment) for every sub-segment,
        stacked into one array -- the shared building block for both
        _compute_obb and _compute_aabb's union-of-segments envelope."""
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
            # Every sub-segment is degenerate (start and stop, and any
            # waypoints between them, all coincide) -- a real state a
            # wire can transiently be in (e.g. a wire service loop's own
            # placeholder "gap" wire, deleted a moment after construction
            # -- see handlers.wire_service_loop_handler._split_wire_for_
            # loop). A point-sized box at the wire's own position is
            # still a valid, if trivial, bound -- returning None left obb/
            # aabb permanently unset (None) instead.
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    @_check_types.do
    def hit_test_step3(self, ray_origin, ray_dir):
        """Precise per-segment mesh hit test (see BaseVar.hit_test_step3):
        tests every sub-segment's own transformed triangles individually
        instead of assuming one rigid transform for the whole wire."""
        if self._vbo is None:
            return False

        vertices_local = self._vbo.vertices.reshape(-1, 3)
        if len(vertices_local) % 3:
            return False

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            ray_object = ray_origin - seg_position.as_numpy

            vertices = (vertices_local * seg_scale.as_numpy) @ seg_angle
            verts = vertices.reshape(-1, 3, 3)

            if self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts):
                return True

        return False

    @_check_types.do
    def _conductor_segment_ends(self) -> tuple[bool, bool]:
        """Return (start_is_conductor, stop_is_conductor) -- whether the
        first/last sub-segment crimps directly into a Terminal and should
        render bare-conductor-sized/colored instead of at the wire's own
        insulation diameter/material (see render()).

        Checked via the sibling graph (parent.start_sibling/stop_sibling,
        a cheap weakref lookup already maintained by Terminal.add_wire/
        AddWireHandler) rather than the raw db_obj point ids -- a splice
        or wire-service-loop sibling never gets the conductor treatment,
        only an actual Terminal.
        """
        from .. import terminal as _terminal

        return (isinstance(self.parent.start_sibling, _terminal.Terminal),
                isinstance(self.parent.stop_sibling, _terminal.Terminal))

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        """Render every sub-segment of the wire's current path.

        Geometry is always current by the time this runs --
        _update_position recomputes it synchronously the moment any
        endpoint or waypoint moves, so there is nothing to catch up on
        here. Each sub-segment is drawn as its own straight cylinder by
        temporarily pointing this object's (and the stripe's) position/
        angle/scale at that segment before delegating to Base3D.render()
        -- reuses its existing faces/edges/normals/vertices debug-config
        gating and material handling unchanged, once per segment.

        The one segment nearest each end that crimps into a Terminal
        (see _conductor_segment_ends) renders at the conductor's own
        diameter/material instead -- a short bare-conductor look at the
        crimp, matching real hardware, rather than full insulation OD
        running straight into the terminal. Suppressed while selected,
        same as the stripe overlay below, so the selection highlight
        stays a single uniform color across the whole wire.
        """
        real_position, real_angle, real_scale, real_material = (
            self._position, self._angle, self._scale, self._material)

        draw_stripe = self._stripe is not None and not self.is_selected

        if self.is_selected:
            conductor_start = conductor_stop = False
        else:
            conductor_start, conductor_stop = self._conductor_segment_ends()

        if draw_stripe:
            stripe_position = self._stripe._position  # NOQA
            stripe_angle = self._stripe._angle  # NOQA

        stripe_offset = 0.0
        segments = list(self._segment_transforms())
        last_idx = len(segments) - 1

        for i, (seg_position, seg_angle, seg_scale, seg_len) in enumerate(segments):
            is_conductor = (
                (i == 0 and conductor_start) or
                (i == last_idx and conductor_stop))

            self._position, self._angle = seg_position, seg_angle

            if is_conductor:
                self._scale = _point.Point(self._conductor_dia, self._conductor_dia, seg_len)
                self._material = self._conductor_material
            else:
                self._scale = seg_scale
                self._material = real_material

            super().render(shaders)

            if draw_stripe and not is_conductor:
                # Stripe geometry ignores scale.z entirely (see
                # gl.shaders.faces' vertex shader) -- only x/y (bumped past
                # the wire's own radius) matter, so its own scale.z value
                # is irrelevant; position/angle must match this segment.
                self._stripe._position = seg_position  # NOQA
                self._stripe._angle = seg_angle  # NOQA
                self._stripe.render_segment(shaders, stripe_offset, stripe_offset + seg_len)

            stripe_offset += seg_len

        self._position, self._angle, self._scale, self._material = (
            real_position, real_angle, real_scale, real_material)

        if draw_stripe:
            self._stripe._position = stripe_position  # NOQA
            self._stripe._angle = stripe_angle  # NOQA

    @_check_types.do
    def set_selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        super().set_selected(flag)
        if self._stripe is not None:
            self._stripe.set_selected(flag)

    @staticmethod
    @_check_types.do
    def _rotation_from_direction(direction):
        """Create quaternion to rotate +Z axis to align with direction"""
        # Unit cylinder points along +Z, rotate it to point along 'direction'
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z (tight
        # epsilon -- this only exists to dodge the near-zero-length cross
        # product below, not to treat "close to vertical" as "vertical")
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 1e-6:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity

        if abs(dot + 1.0) < 1e-6:
            # 180 degree rotation around X axis
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    @property
    @_check_types.do
    def bundle(self):
        """Return the bundle this wire belongs to, if any."""
        return self._bundle

    @bundle.setter
    @_check_types.do
    def bundle(self, value):
        """Set the bundle this wire belongs to.

        Wires hold strong references to bundles as a sanity check.
        """
        self._bundle = value

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
        self.db_obj.is_visible = value

        if self._stripe is not None:
            self._stripe.is_visible = value

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", terminal=None, splice=None,
        extend_wire: tuple = None, add_to_wire: tuple = None, preset_part_id: bytes = None,
        mouse_pos: _point.Point | None = None
    ) -> Union["_wire.Wire", None]:
        """Entry point for every way a peg-board wire-placement session
        can start -- toolbar mode-select (all args None: free-space) or a
        context-menu action (exactly one of the others). Resolves the
        part (and, for a terminal/splice start, checks compatibility) up
        front, builds the real facade object (or grabs the existing wire
        being extended/continued -- see add_handlers.editor_pegboard.
        wire.Wire's own module docstring for why those two never create a
        fresh preview), arms its add-session, and arms the canvas's own
        active_handler_obj pointer -- so callers just need this return
        value to know whether anything actually started (None means the
        part-search dialog was cancelled, or an incompatible-part
        confirmation was declined).

        :param preset_part_id: Skip GetSelection()/the part-search dialog
            entirely and start a free-space placement with this part --
            "Add Wire" from an existing wire's own context menu (same
            part, no re-pick).
        """
        canvas = mainframe.editor_pegboard.editor

        if preset_part_id is not None:
            return cls._start_free_space(mainframe, canvas, preset_part_id)

        from ...handlers import wire_handler as _wire_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from PySide6.QtWidgets import QDialog

        if terminal is not None:
            initial_params = _wire_handler.terminal_wire_search_params(terminal)
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

            return cls._start_from_terminal(mainframe, canvas, terminal, part_id)

        if splice is not None:
            initial_params = _wire_handler.splice_wire_search_params(splice)
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

            return cls._start_from_splice(mainframe, canvas, splice, part_id)

        if extend_wire is not None:
            wire_obj, end = extend_wire
            return cls._start_extend_from_wire(mainframe, canvas, wire_obj, end)

        if add_to_wire is not None:
            wire_obj, end = add_to_wire
            return cls._start_add_to_wire(mainframe, canvas, wire_obj, end)

        part_id = mainframe.editor_db.editor.wires.GetSelection()
        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.WiresPage, mainframe.global_db.wires_table, 'Add Wire')

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        facade = cls._start_free_space(mainframe, canvas, part_id)

        # Free-space start only: *mouse_pos* (the empty-space context menu's
        # own click) is where the wire's first point is dropped; the session
        # is then left armed for its second click as usual.
        if facade is not None and mouse_pos is not None:
            from ...add_handlers import base as _add_base

            _add_base.click_at(canvas, facade.objpegboard, mouse_pos)

        return facade

    @classmethod
    @_check_types.do
    def _start_from_terminal(cls, mainframe, canvas, terminal, part_id: bytes) -> Union["_wire.Wire", None]:
        """Pin the preview wire's start to *terminal* and enter phase 1
        directly -- see handlers.wire_handler.AddWireHandler.
        _start_from_terminal, the original of this method.
        """
        from ...handlers import wire_snap as _wire_snap
        from .. import wire as _wire_facade
        from PySide6.QtWidgets import QMessageBox

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        ok, block_msg, _warning_msg = _wire_snap.check_terminal_compat(terminal, wire_part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(mainframe, 'Incompatible Wire', block_msg)
            if button == QMessageBox.StandardButton.No:
                return None

        start_circuit_id = terminal.db_obj.circuit_id

        placeholder_id = ptables.pjt_points_pegboard_table.insert(0.0, 0.0, 0.0).db_id

        initial_pos = terminal.db_obj.attach_position_pegboard
        stop_db = ptables.pjt_points_pegboard_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        # TODO: fix this so the start and stop points get properly set for the pegboard view
        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, start_circuit_id,
            placeholder_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        terminal.add_wire(facade, 'start')
        ptables.pjt_points_pegboard_table[placeholder_id].delete()

        return cls._arm(canvas, facade, part_id, phase=1, growing_end='stop',
                        start_circuit_id=start_circuit_id)

    @classmethod
    @_check_types.do
    def _start_from_splice(cls, mainframe, canvas, splice, part_id: bytes) -> Union["_wire.Wire", None]:
        from ...handlers import wire_snap as _wire_snap
        from .. import wire as _wire_facade
        from PySide6.QtWidgets import QMessageBox

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        ok, block_msg, _warning_msg = _wire_snap.check_splice_compat(splice, wire_part)
        if not ok:
            block_msg += '\n\nDo you want to use this wire?'
            button = QMessageBox.question(mainframe, 'Incompatible Wire', block_msg)
            if button == QMessageBox.StandardButton.No:
                return None

        start_point_id = splice.db_obj.branch_position_pegboard_id
        initial_pos = splice.objpegboard.wire_position

        stop_db = ptables.pjt_points_pegboard_table.insert(
            float(initial_pos.x), float(initial_pos.y), float(initial_pos.z))

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        # TODO: fix this so the start and stop points get properly set for the pegboard view
        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, None,
            start_point_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        splice.add_wire(facade)
        facade.set_sibling(splice, 'start')

        return cls._arm(canvas, facade, part_id, phase=1, growing_end='stop', start_circuit_id=None)

    @classmethod
    @_check_types.do
    def _start_extend_from_wire(cls, mainframe, canvas, wire_obj, end: str) -> Union["_wire.Wire", None]:
        """Extension mode: live-move *wire_obj*'s own dangling *end*
        directly, never creating a fresh preview -- see
        add_handlers.editor_3d.wire.Wire's own module docstring.
        """

        objpegboard = wire_obj.objpegboard
        start_np = objpegboard.start_position.as_numpy
        stop_np = objpegboard.stop_position.as_numpy

        if end == 'stop':
            source_endpoint = 'stop'
            endpoint_np = stop_np
            seg = stop_np - start_np
        else:
            source_endpoint = 'start'
            endpoint_np = start_np
            seg = start_np - stop_np

        seg_len = float(np.linalg.norm(seg))
        if seg_len < 1e-8:
            return None

        from ...add_handlers.editor_pegboard import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, wire_obj, wire_obj.db_obj.part_id, phase=1,
            start_circuit_id=wire_obj.db_obj.circuit_id,
            extension_mode=True, source_wire=wire_obj, source_endpoint=source_endpoint)

        handler._extension_dir = seg / seg_len  # NOQA
        handler._extension_origin = endpoint_np.copy()  # NOQA
        handler._extension_original_pos = endpoint_np.copy()  # NOQA

        wire_obj.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = wire_obj.objpegboard

        return wire_obj

    @classmethod
    @_check_types.do
    def _start_add_to_wire(cls, mainframe, canvas, wire_obj, end: str) -> Union["_wire.Wire", None]:
        """Continue *wire_obj* from its own free *end* -- tags that end
        as a permanent interior waypoint, then continues the live
        preview from a fresh point there. Unlike every other entry
        point, *wire_obj* is a real, already-placed, already-registered
        wire the whole time (see add_handlers.editor_3d.wire.Wire's own
        ``_preexisting_wire``/``_growing_end`` handling).
        """
        from ...add_handlers.editor_pegboard import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, wire_obj, wire_obj.db_obj.part_id, phase=1, growing_end=end,
            preexisting_wire=True, start_circuit_id=wire_obj.db_obj.circuit_id)

        wire_obj.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = wire_obj.objpegboard

        handler._commit_growing_point_as_waypoint()  # NOQA

        return wire_obj

    @classmethod
    @_check_types.do
    def _start_free_space(cls, mainframe, canvas, part_id: bytes) -> Union["_wire.Wire", None]:
        """Build the preview wire eagerly, at a placeholder start point
        the very first hover call immediately relocates to the cursor --
        see the module-level docstring on add_handlers.editor_3d.wire.Wire
        for why this differs from the old deferred-until-first-click
        behavior.
        """
        from .. import wire as _wire_facade

        ptables = mainframe.project.ptables
        wire_part = mainframe.global_db.wires_table[part_id]

        start_db = ptables.pjt_points_pegboard_table.insert(0.0, 0.0, 0.0)
        stop_db = ptables.pjt_points_pegboard_table.insert(0.0, 0.0, 0.0)

        name = f'{wire_part.manufacturer.name} {wire_part.part_number}'

        # TODO: fix this so the start and stop points get properly set for the pegboard vi
        wire_db = ptables.pjt_wires_table.insert(
            part_id, name, None,
            start_db.db_id, stop_db.db_id,
            None, None, True, False, None, None, False)

        facade = _wire_facade.Wire(mainframe, wire_db)

        return cls._arm(canvas, facade, part_id, phase=0, growing_end='start', start_circuit_id=None)

    @classmethod
    @_check_types.do
    def _arm(cls, canvas, facade, part_id: bytes, phase: int, growing_end: str,
             start_circuit_id) -> "_wire.Wire":
        from ...add_handlers.editor_pegboard import wire as _add_wire

        handler = _add_wire.Wire(
            canvas, facade, part_id, phase=phase, growing_end=growing_end,
            start_circuit_id=start_circuit_id)

        facade.objpegboard._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objpegboard

        return facade

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMenu(self.pegboard.editor, self)

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object
    ) -> bool:
        """Segment-local wire drag -- overrides BasePegboard's generic
        single-position drag outright: what a click on the wire's body
        actually moves (a free end, a waypoint pair, or nothing
        draggable at all) is computed by
        handlers.wire_drag_base.WireDragBase.plan_wire_drag (shared with
        the 3D editor); see that module's own docstring for the full
        rule. A snap committed mid-drag (WireDragBase.snapped_kind/
        snapped_target) is only made real here, on release -- mirroring
        exactly what the two-click placement flow's own inline commits do
        (see handlers.wire_snap.commit_snap's own docstring -- though see
        handlers.wire_drag_base's own "known gap" note: that commit path
        is still 3D-only).

        Also forwards to an active add-session (see
        add_handlers.editor_pegboard.wire.Wire) -- both this object's own
        drag and its own placement session use the same
        self._active_handler slot (never simultaneously), told apart by
        which kind is actually armed since their call shapes differ
        (add takes the full event tuple this method itself received;
        drag takes just a screen delta + position).
        """
        from ...add_handlers.editor_pegboard import wire as _add_wire  # NOQA -- avoid a cycle at import time

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
                handler = self._active_handler

                if handler.end is not None and handler.snapped_kind is not None:
                    # KNOWN GAP (see handlers.wire_drag_base's own module
                    # docstring): commit_snap/Terminal.add_wire/Splice.
                    # add_wire are still 3D-only -- this writes the
                    # connection via *_position3d columns regardless of
                    # which view's drag produced the snap. The live
                    # in-drag teleport-onto-a-probe already works
                    # correctly for peg-board; only this final commit
                    # step doesn't yet.
                    from ...handlers import wire_snap as _wire_snap  # NOQA -- avoid a cycle at import time
                    _wire_snap.commit_snap(
                        self.parent.mainframe, self.parent, handler.end,
                        handler.snapped_kind, handler.snapped_target)

                handler.delete()
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

        from ...drag_handlers.editor_pegboard import wire as _wire_drag_handler

        plan = _wire_drag_handler.Wire.plan_wire_drag(self.parent.mainframe.project, self.parent, current_pos)
        if plan is None:
            return False

        self._active_handler = _wire_drag_handler.Wire(self.pegboard.editor, self.parent, plan)
        return True


class WireStripe(_base_pegboard.BasePegboard):
    """Represent a wire stripe in :mod:`harness_designer.objects.objects_pegboard.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "_wire.Wire", wire: Wire, color: _color.Color, scale: _point.Point,
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

        # wire.length isn't trustworthy yet at this point in Wire.__init__
        # -- it's still the plain straight-line p1/p2 seed from
        # Wire._calc_length, computed before _recalculate_geometry ever
        # runs (see Wire.__init__'s ordering). wire.db_obj/start_position/
        # stop_position are already valid by now though (set by
        # Base3D.__init__, just above), so the true, possibly multi-
        # segment polyline length -- what this stripe actually needs
        # capacity for, e.g. reloading an already-bent wire -- can be
        # computed directly here via the same WireTypeMixin._segments()
        # walk Wire itself uses.
        required = sum(
            float(np.linalg.norm(seg_p2 - seg_p1))
            for seg_p1, seg_p2 in wire._segments())  # NOQA
        self._ensure_stripe_capacity(parent.mainframe, required)

        # Already big enough after _ensure_stripe_capacity -- this just
        # fetches the resulting handle (a cheap no-op fast path, see
        # create_vbo).
        vbo = _helix.create_vbo(required)
        material = _materials.Plastic(color)
        self._wire = wire

        # Deliberately NOT the same scale Point instance the wire uses (only
        # position/angle are shared -- the stripe has no independent extent
        # of its own there; see the _obb/_aabb properties below). The
        # stripe's x/y are bumped past the wire's own radius so it always
        # renders genuinely outside the wire's surface instead of coincident
        # with it -- two coincident opaque surfaces z-fight per-pixel no
        # matter how that's biased, so the fix is to not be coincident in
        # the first place. z is irrelevant here: faces.py's vertex shader
        # skips z-scaling entirely for stripe geometry (stripeClipStop >
        # 0), so it doesn't need to track any segment's live length -- see
        # the clip_start/clip_stop args Wire.render() passes into
        # render_segment below, computed fresh per segment as it walks
        # the wire's own waypoints.
        stripe_scale = _point.Point(scale.x + 0.1, scale.y + 0.1, scale.z)
        super().__init__(parent, None, vbo, angle, position, stripe_scale, material)

    @staticmethod
    @_check_types.do
    def _ensure_stripe_capacity(mainframe, required: float) -> None:
        """Grow the shared wire-stripe helix mesh -- and persist the new
        true-required max back onto the project row -- if `required`
        (a wire's own total length, the furthest any of its segments'
        clip windows will ever reach into the shared mesh) exceeds what's
        currently stored.

        Takes `mainframe` explicitly rather than reading self.mainframe:
        called from __init__ before Base3D.__init__ has set it (the vbo
        it builds here is itself an argument to that call), and later
        from Wire._recalculate_geometry against the *wire's* mainframe,
        not this stripe's own (identical, but the wire is what changed).

        The actual VBO build is padded by _HELIX_OVERSHOOT_MM so a live
        drag/preview has headroom to grow without forcing a GPU
        reallocation on every frame -- the persisted max itself stays
        the true, unpadded requirement. No-op (no create_vbo call at
        all) in the common case where the stored max already covers
        this wire.
        """
        project_db_obj = mainframe.project.db_obj

        if required > project_db_obj.wire_stripe_max_length:
            project_db_obj.wire_stripe_max_length = required
            _helix.create_vbo(required + _HELIX_OVERSHOOT_MM)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        """Always smooth-shaded -- the helix is a swept curved surface with
        no flat faces, so there's no reason for this to ever be flat (see
        Base3D._render_geometry, which defaults to flat shading when a
        subclass doesn't define this)."""
        return True

    @_check_types.do
    def render_segment(self, shaders: "_shaders.ShaderProgram", clip_start: float, clip_stop: float):
        """Draw this stripe windowed to [clip_start, clip_stop] -- one
        call per wire sub-segment, made by Wire.render() with this
        stripe's own _position/_angle already pointed at that segment.

        clip_start/clip_stop are now computed fresh by the caller (a
        running total of preceding segment lengths) rather than read from
        a persisted, cross-row-cascaded value -- see gl.shaders.faces'
        stripeClipStart/stripeClipStop uniforms for what they mean to the
        shader; nothing else about the windowing mechanism changes.

        Set on all three programs (faces/edges/vertices), not just
        faces_program -- edges.py/vertices.py declare and honor the exact
        same uniforms now, specifically so debug edge/vertex rendering
        (Base3D.render()'s _debug_config.draw_edges/draw_vertices passes,
        both reachable from the single super().render() call below) windows
        to this segment too instead of drawing the whole shared helix
        mesh with a naive, non-rebased transform -- confirmed 2026-08-05 as
        the actual source of stray/misplaced vertices and edges showing up
        under debug rendering.

        Resets every uniform to 0.0 right after, same as the single-shot
        render() this replaces -- only WireStripe ever touches them, and
        GL uniform state persists on each program across draw calls, so a
        nonzero value left behind would otherwise leak into whatever
        renders next on that program.
        """
        if not self.is_visible:
            return

        programs = (shaders.faces, shaders.edges, shaders.vertices)

        for program in programs:
            with program:
                program.stripe_clip_start = clip_start
                program.stripe_clip_stop = clip_stop

        super().render(shaders)

        for program in programs:
            with program:
                program.stripe_clip_start = 0.0
                program.stripe_clip_stop = 0.0

    @_check_types.do
    def _compute_obb(self):
        """No-op: the stripe has no independent geometry of its own. See
        the _obb property below."""
        pass

    @_check_types.do
    def _compute_aabb(self):
        """See _compute_obb."""
        pass

    @property
    @_check_types.do
    def _obb(self):
        """Always the wire's current OBB array -- read-only everywhere
        obb/aabb are used (hit-testing, debug overlay boxes), so there's
        never a need for the stripe to hold its own copy."""
        return self._wire._obb

    @_obb.setter
    @_check_types.do
    def _obb(self, value):
        # Base3D.__init__ assigns this once before calling _compute_obb();
        # the wire is the source of truth, so the write is discarded.
        pass

    @property
    @_check_types.do
    def _aabb(self):
        """See _obb."""
        return self._wire._aabb

    @_aabb.setter
    @_check_types.do
    def _aabb(self, value):
        pass

    @_check_types.do
    def _update_position(self, position: _point.Point):
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
    def _update_angle(self, angle: _angle.Angle):
        """See _update_position.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        # self._compute_obb()
        # self._compute_aabb()

        pass

    @_check_types.do
    def _update_scale(self, scale: _point.Point):
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
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects_pegboard.wire`.

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

        # 'Add Splice'/'Add Wire Service Loop' deliberately omitted here --
        # objects_pegboard.splice.Splice/objects_pegboard.wire_service_loop.
        # WireServiceLoop have no start_add of their own yet (unlike their
        # objects_3d counterparts), so offering these actions in the
        # peg-board view would crash immediately on click. Add them back
        # once those classes gain a peg-board placement flow.

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        self.addSeparator()

        from ...drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA -- avoid a cycle at import time

        wire = selected.parent
        click_pos = selected._context_menu_click_pos  # NOQA
        free_end = _wire_pegboard.Wire.pick_free_end(wire.mainframe, wire, click_pos)

        action = self.addAction('Extend Wire')
        action.setEnabled(free_end is not None)
        action.triggered.connect(self.on_extend_wire)

        action = self.addAction('Add to Wire')
        action.setEnabled(free_end is not None)
        action.triggered.connect(self.on_add_to_wire)

        can_add_terminal = False
        if free_end == 'start':
            can_add_terminal = wire.start_sibling is None
        elif free_end == 'stop':
            can_add_terminal = wire.stop_sibling is None

        action = self.addAction('Add Terminal')
        action.setEnabled(can_add_terminal)
        action.triggered.connect(self.on_add_terminal)

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
    def _midpoint(self) -> _point.Point:
        """Return the world space midpoint of the wire."""
        line = _line.Line(self.selected.start_position,
                          self.selected.stop_position)

        return line.point_from_start(line.length() / 2.0)

    @_check_types.do
    def on_add_handle(self):
        """Start the interactive waypoint-placement flow (see
        add_handlers.editor_3d.wire_layout), seeded at the point on the
        wire that was right-clicked to open this menu (falls back to the
        wire's own midpoint if no click point was captured -- e.g. the
        menu was opened some other way). A live preview follows the
        cursor from there (snapping onto the wire's own true start/stop
        when close enough) until the next click commits it.
        """
        from PySide6.QtCore import QTimer
        from . import wire_layout as _wire_layout_3d

        mainframe = self.selected.parent.mainframe
        wire = self.selected.parent

        click_pos = self.selected._context_menu_click_pos  # NOQA
        initial_pos = None
        if click_pos is not None:
            initial_pos, _angle, _insert_idx = self.selected.get_closest_point(click_pos)

        if initial_pos is None:
            # No click captured -- fall back to the wire's own midpoint.
            initial_pos = self._midpoint()

        @_check_types.do
        def _do():
            _wire_layout_3d.WireLayout.start_add(mainframe, wire, initial_pos)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_marker(self):
        """Add a wire marker at the point on the wire that was
        right-clicked to open this menu (falls back to the wire's
        midpoint if no click point was captured -- e.g. the menu was
        opened some other way)."""
        @_check_types.do
        def _do():
            from .. import wire_marker as _wire_marker_obj

            mainframe = self.selected.parent.mainframe

            part_id = _menu_ops.get_part_id(
                mainframe, 'wire_markers',
                mainframe.global_db.wire_markers_table, 'Add Wire Marker')

            if part_id is None:
                return

            click_pos = self.selected._context_menu_click_pos  # NOQA
            position = None
            if click_pos is not None:
                position, _angle, _idx = self.selected.get_closest_point(click_pos)

            if position is None:
                position = self._midpoint()

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(*position.as_float)

            db_obj = ptables.pjt_wire_markers_table.insert(
                None, p3d.db_id, self.selected.db_obj.db_id, part_id, '')

            marker = _wire_marker_obj.WireMarker(mainframe, db_obj)
            mainframe.project.add_wire_marker(marker)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_wire(self):
        """Start placing another wire of the same part type."""
        mainframe = self.selected.parent.mainframe
        part_id = self.selected.db_obj.part_id

        @_check_types.do
        def _do():
            Wire.start_add(mainframe, preset_part_id=part_id)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_extend_wire(self):
        """Grow this wire's free end in its current direction, with no
        waypoint/layout added -- see Wire.start_add's own
        extend_wire branch / add_handlers.editor_3d.wire's module
        docstring."""
        from ...drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA -- avoid a cycle at import time

        mainframe = self.selected.parent.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end = _wire_pegboard.Wire.pick_free_end(mainframe, wire, click_pos)
        if end is None:
            return

        @_check_types.do
        def _do():
            Wire.start_add(mainframe, extend_wire=(wire, end))

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_terminal(self):
        """Crimp a new terminal (not in a cavity) onto this wire's free
        end -- see objects_3d.terminal.Terminal.add_at_wire_end."""
        from ...drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA -- avoid a cycle at import time
        from ..objects_3d import terminal as _terminal_3d

        mainframe = self.selected.parent.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end = _wire_pegboard.Wire.pick_free_end(mainframe, wire, click_pos)
        if end is None:
            return

        @_check_types.do
        def _do():
            _terminal_3d.Terminal.add_at_wire_end(mainframe, wire, end)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_to_wire(self):
        """Drop a waypoint + layout at this wire's free end and continue
        it from there, freely -- see Wire.start_add's own add_to_wire
        branch / add_handlers.editor_3d.wire's module docstring."""
        from ...drag_handlers.editor_pegboard import wire as _wire_pegboard  # NOQA -- avoid a cycle at import time

        mainframe = self.selected.parent.mainframe
        wire = self.selected.parent
        click_pos = self.selected._context_menu_click_pos  # NOQA

        end = _wire_pegboard.Wire.pick_free_end(mainframe, wire, click_pos)
        if end is None:
            return

        @_check_types.do
        def _do():
            Wire.start_add(mainframe, add_to_wire=(wire, end))

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_add_to_bundle(self):
        """Add this wire to the closest bundle in the project.

        Bundle membership only exists on a wire's 3D wrapper --
        ``objects_pegboard.bundle.Bundle`` has no ``add_wire`` of its
        own (bundling is a 3D-mesh-space concept the peg-board view has
        no equivalent of yet), so this reaches through to
        ``self.selected.parent.obj3d`` (the same wire's 3D wrapper)
        rather than assigning onto this peg-board wrapper's own
        (copied-but-unused) ``_bundle`` attribute.
        """
        mainframe = self.selected.parent.mainframe
        midpoint = self._midpoint()
        wire_obj3d = self.selected.parent.obj3d

        closest = None
        closest_distance = None

        for bundle in mainframe.project.bundles:
            b_line = _line.Line(bundle.obj3d.start_position,
                                bundle.obj3d.stop_position)
            b_mid = b_line.point_from_start(b_line.length() / 2.0)

            distance = _line.Line(midpoint, b_mid).length()

            if closest_distance is None or distance < closest_distance:
                closest_distance = distance
                closest = bundle

        if closest is None:
            return

        closest.obj3d.add_wire(wire_obj3d)
        wire_obj3d.bundle = closest.obj3d

        mainframe.editor3d.Refresh()

    @_check_types.do
    def on_trace_circuit(self):
        """Highlight every object on this wire's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self):
        """Make this wire the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this wire from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this wire's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
