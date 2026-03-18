from typing import TYPE_CHECKING

import wx

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
    _parent: "_wire_service_loop.WireServiceLoop" = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"

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

    def get_context_menu(self):
        return WireServiceLoopMenu(self.mainframe.editor3d.editor, self)


class WireServiceLoopMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

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

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()





