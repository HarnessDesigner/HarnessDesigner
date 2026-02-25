from typing import TYPE_CHECKING

import wx

# from ...widgets.context_menus import RotateMenu, MirrorMenu
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
    _parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker"

    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):

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

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

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

        self.editor3d.Refresh(False)


class WireMarkerMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Set Label')
        canvas.Bind(wx.EVT_MENU, self.on_set_label, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Flip Label')
        canvas.Bind(wx.EVT_MENU, self.on_flip_label, id=item.GetId())

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_set_label(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_flip_label(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
