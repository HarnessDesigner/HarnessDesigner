# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


Config = _config.Config.editor3d


class WireMarker(_base3d.Base3D):
    parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker" = None

    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part
        position = db_obj.position3d
        wire = db_obj.wire
        wire_p1 = wire.start_position3d
        wire_p2 = wire.stop_position3d

        p1_distance = _line.Line(wire_p1, position).length()
        p2_distance = _line.Line(wire_p2, position).length()

        if p1_distance > p2_distance:
            self._distance = p1_distance
        else:
            self._distance = p2_distance
            wire_p1, wire_p2 = wire_p2, wire_p1

        angle = _angle.Angle.from_points(wire_p1, wire_p2)

        color = db_obj.part.color.ui
        material = _materials.Plastic(color)

        color = _color.Color(0.05, 0.05, 0.05, 1.0)

        length = 5.0
        diameter = wire.part.od_mm + 0.05
        scale = _point.Point(diameter, diameter, length)
        vbo = _cylinder.create_vbo()

        label_material = _materials.Plastic(color)
        self._p1 = wire_p1
        self._p2 = wire_p2

        wire_p1.bind(self._update_position)
        wire_p2.bind(self._update_position)

        vbo.acquire()
        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

        parent.mainframe.editor3d.context.release()


    def _update_position(self, position: _point.Point):
        if position.db_id == self._position.db_id:
            line = _line.Line(self._p1, self._p2)

            new_position = line.project_to_line(position)

            delta = new_position - position
            with position:
                position += delta

            self._o_position = position.copy()

        else:
            inverse_angle = -self._angle
            position = self._position.copy()

            position -= self._p1
            position @= inverse_angle

            angle = _angle.Angle.from_points(self._p1, self._p2)
            self._angle._q = angle._q  # NOQA

            position @= self._angle
            position += self._p1

            delta = position - self._position
            with self._position:
                self._position += delta

            self._o_position = self._position.copy()

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.update()

    def get_context_menu(self):
        return WireMarkerMenu(self.mainframe.editor3d.editor, self)


class WireMarkerMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Set Label')
        action.triggered.connect(self.on_set_label)

        action = self.addAction('Flip Label')
        action.triggered.connect(self.on_flip_label)

        self.addSeparator()

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

    def on_set_label(self):
        pass

    def on_flip_label(self):
        pass

    def on_select(self):
        pass

    def on_clone(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
