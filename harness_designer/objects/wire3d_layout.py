from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects3d import wire_layout as _wire3d_layout

import wx

if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


class Wire3DLayout(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire3d_layout.PJTWire3DLayout"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj3d = _wire3d_layout.WireLayout(mainframe.editor3d, db_obj)


class Wire3DLayoutMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Splice')
        canvas.Bind(wx.EVT_MENU, self.on_add_splice, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

    def on_add_splice(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

