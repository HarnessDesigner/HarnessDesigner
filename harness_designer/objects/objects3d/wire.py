# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer
import numpy as np
import math

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import helix as _helix
from ...gl import materials as _materials
from ... import color as _color
from ... import utils as _utils
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


Config = _config.Config.editor3d


class Wire(_base3d.Base3D):
    """Represent a wire in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire.Wire`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """
        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part
        color = self._part.color.ui
        stripe_color = self._part.stripe_color
        diameter = self._part.od_mm

        # Wires hold strong references to bundles as a sanity check
        self._bundle = None

        material = _materials.Plastic(color)

        self._p1 = db_obj.start_position3d
        self._p2 = db_obj.stop_position3d

        position = self._p1

        scale = _point.Point(diameter, diameter, 1.0)

        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p2.bind(self._update_position)

        vbo = _cylinder.create_vbo()
        angle = _angle.Angle()

        if stripe_color is None:
            self._stripe = None
        else:
            self._stripe = WireStripe(parent, self, stripe_color.ui, scale, angle, position)

        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        self._update_position(None)
        parent.mainframe.editor3d.context.release()

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    def _update_position(self, _: _point.Point):
        """Calculate position, rotation, and scale from endpoints"""

        # Calculate wire vector
        wire_vector = (self._p1 - self._p2).as_numpy
        length = np.linalg.norm(wire_vector)

        if length < 0.001:
            length = 0.001  # Prevent zero length

        self._scale.z = length

        direction = wire_vector / length

        # Rotation: align +Z axis with wire direction
        angle = self._rotation_from_direction(direction)
        self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

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
    def _rotation_from_direction(direction):
        """Create quaternion to rotate +Z axis to align with direction"""
        # Unit cylinder points along +Z, rotate it to point along 'direction'
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 0.0001:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity
        if abs(dot + 1.0) < 0.0001:
            # 180 degree rotation around X axis
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    @property
    def bundle(self):
        """Return the bundle this wire belongs to, if any."""
        return self._bundle

    @bundle.setter
    def bundle(self, value):
        """Set the bundle this wire belongs to.

        Wires hold strong references to bundles as a sanity check.
        """
        self._bundle = value

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
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

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMenu(self.mainframe.editor3d.editor, self)


class WireStripe(_base3d.Base3D):
    """Represent a wire stripe in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_wire.Wire", wire: "Wire", color: _color.Color, scale: _point.Point,
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

        vbo = _helix.create_vbo()
        material = _materials.Plastic(color)
        self._wire = wire

        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material)

        p1 = _point.Point(0.0, 0.0, 0.0)
        p2 = _point.Point(0.0, 0.0, 0.0)

        self._obb = _utils.compute_obb(p1, p2)
        self._aabb = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])

    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        pass

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        pass

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        pass

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value


class WireMenu(QMenu):
    """Represent a wire menu in :mod:`harness_designer.objects.objects3d.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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

    def _midpoint(self) -> _point.Point:
        """Return the world space midpoint of the wire."""
        line = _line.Line(self.selected.start_position,
                          self.selected.stop_position)

        return line.point_from_start(line.length() / 2.0)

    def on_add_handle(self):
        """Insert a wire layout (drag handle) at the middle of the wire.

        The wire is split into two segments that share the layout point.
        """
        from ...handlers import wire_layout_handler as _wire_layout_handler

        wire = self.selected.parent
        project = self.selected.mainframe.project
        midpoint = self._midpoint()

        _wire_layout_handler._create_wire_layout_on_wire(  # NOQA
            project, wire, midpoint)

        self.selected.editor3d.Refresh()

    def on_add_marker(self):
        """Add a wire marker at the middle of the wire."""
        def _do():
            from .. import wire_marker as _wire_marker_obj

            mainframe = self.selected.mainframe

            part_id = _menu_ops.get_part_id(
                mainframe, 'wire_markers',
                mainframe.global_db.wire_markers_table, 'Add Wire Marker')

            if part_id is None:
                return

            midpoint = self._midpoint()

            ptables = mainframe.project.ptables
            p3d = ptables.pjt_points3d_table.insert(*midpoint.as_float)

            db_obj = ptables.pjt_wire_markers_table.insert(
                None, p3d.db_id, self.selected.db_obj.db_id, part_id, '')

            marker = _wire_marker_obj.WireMarker(mainframe, db_obj)
            mainframe.project.add_wire_marker(marker)

        QTimer.singleShot(0, _do)

    def on_add_splice(self):
        """Start the interactive splice placement flow on this wire."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        wire = self.selected.parent

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddSpliceHandler(mainframe, wire))

    def on_add_wire(self):
        """Start placing another wire of the same part type."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddWireHandler(mainframe, part_id))

    def on_add_wire_service_loop(self):
        """Start placing a service loop using this wire's part type."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        part_id = self.selected.db_obj.part_id

        _menu_ops.start_handler(
            mainframe,
            lambda: _handlers.AddWireServiceLoopHandler(mainframe, part_id))

    def on_add_to_bundle(self):
        """Add this wire to the closest bundle in the project."""
        mainframe = self.selected.mainframe
        midpoint = self._midpoint()

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

        closest.obj3d.add_wire(self.selected)
        self.selected.bundle = closest.obj3d

        mainframe.editor3d.Refresh()

    def on_trace_circuit(self):
        """Highlight every object on this wire's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this wire the active selection."""
        _menu_ops.select_object(self.selected)

    def on_delete(self):
        """Delete this wire from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_wire)

    def on_properties(self):
        """Show this wire's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
