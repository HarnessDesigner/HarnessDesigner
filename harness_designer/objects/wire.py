from typing import TYPE_CHECKING

import wx

from . import ObjectBase as _ObjectBase
from .objects2d import wire as _wire2d
from .objects3d import wire as _wire3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire


class Wire(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire.PJTWire"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _wire2d.Wire(mainframe.editor2d, db_obj)
        self.obj3d = _wire3d.Wire(mainframe.editor3d, db_obj)

    @staticmethod
    def get_wire_triangles(model):
        if Config.modeling.smooth_wires:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)


class WireMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Handle')
        canvas.Bind(wx.EVT_MENU, self.on_add_handle, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Marker')
        canvas.Bind(wx.EVT_MENU, self.on_add_marker, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Splice')
        canvas.Bind(wx.EVT_MENU, self.on_add_splice, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire Service Loop')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire_service_loop, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Add to Bundle')
        canvas.Bind(wx.EVT_MENU, self.on_add_to_bundle, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_add_handle(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_marker(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_splice(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire_service_loop(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_to_bundle(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()

