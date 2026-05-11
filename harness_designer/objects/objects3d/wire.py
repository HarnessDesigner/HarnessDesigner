# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
import numpy as np
import math

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
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
    parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
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

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        self._update_position(None)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2

    def _update_angle(self, angle: _angle.Angle):
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
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
        self.db_obj.is_visible = value

        if self._stripe is not None:
            self._stripe.is_visible = value

    def get_context_menu(self):
        return WireMenu(self.mainframe.editor3d.editor, self)


class WireStripe(_base3d.Base3D):

    def __init__(self, parent: "_wire.Wire", wire: "Wire", color: _color.Color, scale: _point.Point,
                 angle: _angle.Angle, position: _point.Point):

        vbo = _helix.create_vbo()
        material = _materials.Plastic(color)
        self._wire = wire

        _base3d.Base3D.__init__(self, parent, None, vbo, angle, position, scale, material)

        p1 = _point.Point(0.0, 0.0, 0.0)
        p2 = _point.Point(0.0, 0.0, 0.0)

        self._obb = _utils.compute_obb(p1, p2)
        self._aabb = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])

    def _update_position(self, position: _point.Point):
        pass

    def _update_angle(self, angle: _angle.Angle):
        pass

    def _update_scale(self, scale: _point.Point):
        pass

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        self._is_visible = value


class WireMenu(QMenu):

    def __init__(self, canvas, selected):
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

    def on_add_handle(self):
        pass

    def on_add_marker(self):
        pass

    def on_add_splice(self):
        pass

    def on_add_wire(self):
        pass

    def on_add_wire_service_loop(self):
        pass

    def on_add_to_bundle(self):
        pass

    def on_trace_circuit(self):
        pass

    def on_select(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
