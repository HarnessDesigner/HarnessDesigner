# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...gl import materials as _materials
from ... import config as _config
from ...shapes import cylinder_helix as _cylinder_helix


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from .. import wire_service_loop as _wire_service_loop


Config = _config.Config.editor3d


class WireServiceLoop(_base3d.Base3D):
    parent: "_wire_service_loop.WireServiceLoop" = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = None

    def __init__(self, parent: "_wire_service_loop.WireServiceLoop",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):

        self._part = db_obj.part
        color = self._part.color.ui
        material = _materials.Plastic(color)

        position = db_obj.start_position3d
        position2 = db_obj.stop_position3d

        vbo = _cylinder_helix.create_vbo()
        diameter = self._part.od_mm
        scale = _point.Point(diameter, diameter, diameter)
        angle = db_obj.angle3d

        if position2.as_float == (0.0, 0.0, 0.0):
            tmp_position = vbo.endpoint.copy()
            tmp_position *= scale
            tmp_position @= angle
            tmp_position += position

            with position2:
                position2.x = tmp_position.x
                position2.y = tmp_position.y

            position2.z = tmp_position.z

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        self._p1 = position
        self._p2 = position2

    def get_context_menu(self):
        return WireServiceLoopMenu(self.mainframe.editor3d.editor, self)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class WireServiceLoopMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

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

    def on_add_wire(self):
        pass

    def on_trace_circuit(self):
        pass

    def on_select(self):
        pass

    def on_clone(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
