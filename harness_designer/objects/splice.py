from typing import TYPE_CHECKING

import wx

from . import ObjectBase as _ObjectBase
from .objects3d import splice as _splice3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_splice as _pjt_splice

    from .objects2d import splice as _splice2d


class Splice(_ObjectBase):
    obj2d: "_splice2d.Splice" = None
    obj3d: _splice3d.Splice = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_splice.PJTSplice"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj2d = _splice2d.Splice(mainframe.editor2d, db_obj)
        self.obj3d = _splice3d.Splice(mainframe.editor3d, db_obj)



class SpliceMenu(wx.Menu):

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