# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


Config = _config.Config.editor3d


class WireLayout(_base3d.Base3D):
    """Represent a wire layout in :mod:`harness_designer.objects.objects3d.wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout" = None

    # Sits on the wire's centerline, inside its OBB by design -- see
    # Base3D._pick_priority.
    _pick_priority = 1

    @_check_types.do
    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """

        with parent.mainframe.editor3d.context:
            self._bundle_layout_point_id = None

            wires = db_obj.attached_wires
            if wires:
                diameter = wires[0].part.od_mm
                color = wires[0].part.color.ui
            else:
                diameter = 3.0
                color = _color.Color(0.5, 0.5, 0.5, 1.0)

            material = _materials.Plastic(color)

            scale = _point.Point(diameter, diameter, diameter)
            vbo = _sphere.create_vbo()
            angle = _angle.Angle()
            position = db_obj.position3d
            _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

    @property
    @_check_types.do
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.position

    @_check_types.do
    def _sync_from_bundle_layout_point(self, point: _point.Point):
        """Callback to sync wire layout point position from bundle layout point.

        This is called when the bundle layout point moves. Wire layout points
        share coordinates with bundle layout points but do NOT share the same
        Point instances.
        """
        if self._is_deleted:
            return

        # Update our center to match the bundle layout point
        delta = point - self._position
        self._position += delta

    @_check_types.do
    def bind_to_bundle_layout_point(self, bundle_layout_point: _point.Point):
        """Register callback to bundle layout point for synchronization.

        When a wire is bundled, wire layouts register callbacks to the relevant
        bundle layout Points so wires follow bundle movement.
        """
        if self._bundle_layout_point_id is not None:
            # Already bound, unbind first
            self.unbind_from_bundle_layout_point()

        # Store the db_id for tracking (not a strong reference)
        self._bundle_layout_point_id = bundle_layout_point.db_id

        # Bind our sync callback to the bundle layout point
        bundle_layout_point.bind(self._sync_from_bundle_layout_point)

        # Initial sync
        self._sync_from_bundle_layout_point(bundle_layout_point)

    @_check_types.do
    def unbind_from_bundle_layout_point(self):
        """Unbind from bundle layout point.

        When a wire is unbundled, wire layouts unbind themselves from the
        bundle layout Points.
        """
        if self._bundle_layout_point_id is None:
            return

        # Use db_id-based lookup to get the point without holding strong reference
        # The PointMeta cache will return the same instance if it still exists
        try:
            bundle_layout_point = _point.Point(0.0, 0.0, 0.0,
                                               db_id=self._bundle_layout_point_id)

            bundle_layout_point.unbind(self._sync_from_bundle_layout_point)

        except:  # NOQA
            # Point may have been garbage collected
            pass

        self._bundle_layout_point_id = None

    @_check_types.do
    def _delete(self):
        """Clean up bundle bindings and reconnect split wires before deleting."""
        self.unbind_from_bundle_layout_point()
        self._reconnect_wires()
        super()._delete()

    @_check_types.do
    def _reconnect_wires(self):
        """Remove this layout's own bend from whatever wire(s) it sits on.

        Two cases, by how many distinct wire rows attach here (see
        PJTWireLayout.attached_wires): exactly one -- the common case now,
        an ordinary bend is just a waypoint on a single wire -- simply
        drops that waypoint (renumbering every later one down by one) and
        deletes its point row, leaving the wire a straight line between
        its remaining neighbors; exactly two -- a genuine seam between
        separate rows (a splice/service-loop's own cut point, or a wire-
        to-wire join's seam -- see handlers.wire_handler._merge_wire_into)
        -- merges them back into one via handlers.wire_topology.
        merge_wires, mirroring handlers.wire_topology.split_wire_at_point
        in reverse. A layout with zero here sits at an actual endpoint
        (handlers.wire_layout_handler._create_wire_layout_at_endpoint),
        never tagged as anyone's waypoint -- nothing to reconnect.
        """
        pjt_wires = self.db_obj.attached_wires
        point_id = self.db_obj.position3d_id

        if len(pjt_wires) == 2:
            objs = [pjt_wire.get_object() for pjt_wire in pjt_wires]
            if None in objs:
                return

            wire_a, wire_b = objs
            if wire_a.db_obj.stop_position3d_id == point_id:
                upstream, downstream = wire_a, wire_b
            else:
                upstream, downstream = wire_b, wire_a

            from ..handlers import wire_topology as _wire_topology

            _wire_topology.merge_wires(self.mainframe.project, upstream, downstream)
            return

        if len(pjt_wires) != 1:
            return

        ptables = self.mainframe.project.ptables
        point = ptables.pjt_points3d_table[point_id]

        if point.wire_id is None:
            return

        removed_idx = point.idx
        wire_db = pjt_wires[0]
        for waypoint in wire_db.waypoints3d:
            if waypoint.idx > removed_idx:
                waypoint.idx = waypoint.idx - 1

        wire_obj = wire_db.get_object()
        point.delete()

        if wire_obj is not None:
            wire_obj.obj3d.refresh_waypoints()

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireLayoutMenu(self.mainframe.editor3d.editor, self)


class WireLayoutMenu(QMenu):
    """Represent a wire layout menu in :mod:`harness_designer.objects.objects3d.wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`WireLayoutMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

    @_check_types.do
    def on_add_splice(self):
        """Start the interactive splice placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddSpliceHandler(mainframe))

    @_check_types.do
    def on_trace_circuit(self):
        """Highlight every object on the circuit of an attached wire."""
        wires = self.selected.db_obj.attached_wires

        if wires:
            _menu_ops.trace_circuit(self.selected, wires[0])

    @_check_types.do
    def on_select(self):
        """Make this wire layout the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this wire layout from the project."""
        _menu_ops.delete_object(self.selected)
