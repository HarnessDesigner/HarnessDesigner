# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QMenu
import math
import numpy as np

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ... import config as _config
from ...gl import materials as _materials
from . import mixins as _mixins
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


Config = _config.Config.editor_3d


class Bundle(_base_3d.Base3D, _mixins.WireTypeMixin):
    """Represent a bundle in :mod:`harness_designer.objects.objects_3d.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_bundle.Bundle" = None
    db_obj: "_pjt_bundle.PJTBundle" = None

    @_check_types.do
    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle.Bundle`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part

            layers = db_obj.concentric.layers
            if layers:
                self._diameter = layers[-1].diameter
            else:
                self._diameter = self._part.min_dia

            color = self._part.color.ui
            material = _materials.Rubber(color)

            start_layout = db_obj.start_layout
            stop_layout = db_obj.stop_layout

            self._is_start_clickable = start_layout is None
            self._is_stop_clickable = stop_layout is None

            self._p1 = db_obj.start_position3d
            self._p2 = db_obj.stop_position3d

            # Live Point objects for every interior waypoint (idx order), kept
            # in sync with the DB via refresh_waypoints() -- called by whichever
            # handler adds/removes/reorders this bundle's own waypoints
            # (handlers.bundle_layout_handler, handlers.bundle_topology).
            self._waypoint_points: list[_point.Point] = []

            position = self._p1
            angle = _angle.Angle()
            scale = _point.Point(self._diameter, self._diameter, 0.0)
            vbo = _cylinder.create_vbo()

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

            # Track wires grouped inside this bundle using weak references --
            # unrelated to the waypoint/sibling-graph work above; see
            # objects.bundle.Bundle.set_sibling for this bundle's own trunk-end
            # sibling (a Transition), which is a separate mechanism entirely.
            self._wires = []  # List of weak references to Wire objects

            self._p2.bind(self._update_position)

            # self.db_obj is only valid from here on (set by Base3D.__init__
            # above) -- this is the first point waypoints3d/for_bundle can be
            # queried, so the initial waypoint bind and the real (possibly
            # multi-segment) geometry recompute both happen here, not earlier.
            self._bind_waypoints()
            self._recalculate_geometry()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_bundles

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
    def diameter(self) -> float:
        return self._diameter

    @diameter.setter
    @_check_types.do
    def diameter(self, value: float):
        self._diameter = value
        radius = value / 2
        self._scale.x = radius
        self._scale.y = radius

    @_check_types.do
    def _bind_waypoints(self) -> None:
        """(Re-)bind this bundle's own _update_position callback to every
        current interior waypoint's live Point, unbinding it from whatever
        set was bound before.

        Called once at construction and again (as refresh_waypoints) by
        any handler that adds/removes/reorders this bundle's own
        waypoints, so live position-change callbacks always match the
        current set.
        """
        for point in self._waypoint_points:
            point.unbind(self._update_position)

        self._waypoint_points = [wp.point for wp in self.db_obj.waypoints3d]

        for point in self._waypoint_points:
            point.bind(self._update_position)

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Public entry point for handlers: call after this bundle's own
        waypoint rows change (added, removed, or reordered) so live
        callbacks, cached length, and geometry all catch up."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.editor3d.Refresh()

    @_check_types.do
    def set_start_position(self, point: _point.Point) -> None:
        """Repoint this bundle's own start end to *point* entirely.

        Not a merge/delegation (see Point.attach for that) -- the old
        start point is left alone as an independent point, and *point*
        must already be exactly where this bundle's start should be --
        nothing here moves it.
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
    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        pass

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
        """Compute total length, an aggregate angle, and OBB/AABB from the
        bundle's current start/interior-waypoints/stop path.

        Per-segment position/angle/scale for actual drawing and hit-
        testing are computed fresh in render()/hit_test_step3 from
        WireTypeMixin._segments() -- this only maintains the aggregate
        values anything outside this class still reads (.scale, .angle,
        .obb, .aabb).
        """
        segments = self._segments()

        total_length = 0.0
        for seg_p1, seg_p2 in segments:
            total_length += float(np.linalg.norm(seg_p2 - seg_p1))

        if total_length < 0.001:
            total_length = 0.001  # Prevent zero length

        self._scale.z = total_length

        # Aggregate angle: the overall start->stop chord direction. Not
        # used for drawing (each segment computes its own), kept only for
        # any other code reading .angle on a bundle.
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
        """Recompute geometry immediately, not deferred to the next render
        pass -- bound to the start/stop endpoints and every interior
        waypoint (see _bind_waypoints), so any of them moving keeps the
        bundle's aggregate scale/OBB/AABB current before the next repaint.
        """
        self._recalculate_geometry()

    @_check_types.do
    def _segment_transforms(self):
        """Yield (position, angle, scale, length) for every sub-segment of
        this bundle's current path -- the values render()/hit_test_step3
        both draw/test against, computed fresh each call since a bundle's
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
        single rigid OBB has no meaningful orientation for a bundle with
        more than one bend, so this degenerates to the same envelope as
        _compute_aabb rather than a tight rotated box. Conservative but
        always correct; see hit_test_step3 for the precise, per-segment
        mesh test."""
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
            # waypoints between them, all coincide) -- a point-sized box
            # at the bundle's own position is still a valid, if trivial,
            # bound (see objects.objects_3d.wire's identical fallback).
            point = self._p1.as_numpy
            return np.tile(point, (8, 1)).astype(np.float32)

        return np.concatenate(all_corners, axis=0)

    @_check_types.do
    def hit_test_step3(self, ray_origin, ray_dir):
        """Precise per-segment mesh hit test (see BaseVar.hit_test_step3):
        tests every sub-segment's own transformed triangles individually
        instead of assuming one rigid transform for the whole bundle."""
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
    def render(self, faces_program, edges_program, vertices_program):
        """Render every sub-segment of the bundle's current path.

        Geometry is always current by the time this runs --
        _update_position recomputes it synchronously the moment any
        endpoint or waypoint moves, so there is nothing to catch up on
        here. Each sub-segment is drawn as its own straight cylinder by
        temporarily pointing this object's position/angle/scale at that
        segment before delegating to Base3D.render() -- reuses its
        existing faces/edges/normals/vertices debug-config gating and
        material handling unchanged, once per segment.
        """
        real_position, real_angle, real_scale = self._position, self._angle, self._scale

        for seg_position, seg_angle, seg_scale, _seg_len in self._segment_transforms():
            self._position, self._angle, self._scale = seg_position, seg_angle, seg_scale
            super().render(faces_program, edges_program, vertices_program)

        self._position, self._angle, self._scale = real_position, real_angle, real_scale

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

    @_check_types.do
    def set_diameter(self, value: float):
        """Set this bundle's own diameter, and -- if either end is
        attached to a Transition (see objects.bundle.Bundle.set_sibling)
        -- that branch's own diameter to match, so the fitting's opening
        always reflects whatever bundle currently plugs into it.

        There is nothing further to cascade into past a Transition: under
        the waypoint model, two bundle rows never share an endpoint with
        each other directly any more (ordinary bends are same-row
        waypoints; a bundle's own end can only ever attach to a
        Transition; two bundles touching merge into one row instead of
        staying two, see handlers.bundle_topology.merge_bundles) -- so
        the old cross-row cascade through BundleLayout.set_diameter this
        replaces no longer has any boundary to walk across.
        """
        self._diameter = value
        self._scale.x = value
        self._scale.y = value

        bundle_obj = self.parent

        for transition in (bundle_obj.start_sibling, bundle_obj.stop_sibling):
            if transition is None:
                continue

            branch_id = transition.branch_id_of(bundle_obj)
            if branch_id is None:
                continue

            branch = getattr(transition.db_obj, f'branch{branch_id}')
            if branch is not None:
                branch.diameter = value

    @_check_types.do
    def add_wire(self, wire):
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param wire: Value for ``wire``.
        :type wire: UNKNOWN
        """
        # Store weak reference to the wire
        wire_ref = weakref.ref(wire, self._on_wire_deleted)
        self._wires.append(wire_ref)

        # Hide the wire when it's bundled
        if wire.is_visible:
            wire.is_visible = False

    @_check_types.do
    def remove_wire(self, wire):
        """Remove the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param wire: Value for ``wire``.
        :type wire: UNKNOWN
        """
        # Remove the weak reference
        for ref in self._wires[:]:
            w = ref()
            if w is None:
                self._wires.remove(ref)
            elif w == wire:
                self._wires.remove(ref)
                # Make the wire visible again
                wire.is_visible = True
                break

    @_check_types.do
    def _on_wire_deleted(self, ref):
        """Callback when a wire is garbage collected."""
        if ref in self._wires:
            self._wires.remove(ref)

    @property
    @_check_types.do
    def wires(self):
        """Get all wires in this bundle (that still exist)."""
        for ref in self._wires[:]:
            wire = ref()
            if wire is None:
                self._wires.remove(ref)
            else:
                yield wire

    @property
    @_check_types.do
    def wire_count(self) -> int:
        """Return the number of wires in this bundle."""
        count = 0
        for ref in self._wires[:]:
            if ref() is None:
                self._wires.remove(ref)
            else:
                count += 1

        return count

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return BundleMenu(self.mainframe.editor3d.editor, self)

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


class BundleMenu(QMenu):
    """Represent a bundle menu in :mod:`harness_designer.objects.objects_3d.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`BundleMenu` instance.

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

        action = self.addAction('Add Transition')
        action.triggered.connect(self.on_add_transition)

        action = self.addAction('Wire Contents')
        action.triggered.connect(self.on_wire_contents)

        self.addSeparator()
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
        """Insert a bundle layout (drag handle) at the point on the bundle
        that was right-clicked to open this menu (falls back to the
        bundle's midpoint if no click point was captured -- e.g. the menu
        was opened some other way).

        No row split -- the new waypoint is inserted into the bundle's
        own ordered path at whichever position the click actually
        projects onto (see _create_bundle_layout_on_bundle), mirroring
        objects.objects_3d.wire.WireMenu.on_add_handle.
        """
        from ...handlers import bundle_layout_handler as _bundle_layout_handler

        bundle = self.selected.parent
        project = self.selected.mainframe.project

        click_pos = self.selected._context_menu_click_pos  # NOQA
        position = insert_idx = None
        if click_pos is not None:
            position, _angle, insert_idx = self.selected.get_closest_point(click_pos)

        if position is None:
            line = _line.Line(self.selected.start_position,
                              self.selected.stop_position)
            position = line.point_from_start(line.length() / 2.0)

        _bundle_layout_handler._create_bundle_layout_on_bundle(  # NOQA
            project, bundle, position, self.selected.diameter, insert_idx)

        self.selected.editor3d.Refresh()

    @_check_types.do
    def on_add_transition(self):
        """Start the interactive transition placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        @_check_types.do
        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'transitions',
                mainframe.global_db.transitions_table, 'Add Transition')

            if part_id is None:
                return None

            return _handlers.AddTransitionHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    @_check_types.do
    def on_wire_contents(self):
        """Open the read-only wire-contents dialog for this bundle."""
        from ...ui.dialogs import bundle_wires_dialog as _dlg

        mainframe = self.selected.mainframe
        dlg = _dlg.BundleWiresDialog(mainframe, self.selected)
        dlg.exec()
        dlg.deleteLater()

    @_check_types.do
    def on_select(self):
        """Make this bundle the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this bundle from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this bundle's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
