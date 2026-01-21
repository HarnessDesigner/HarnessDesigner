from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase

from .objects3d import wire_marker as _wire_marker3d
from .objects2d import wire_marker as _wire_marker2d

if TYPE_CHECKING:
    from ..database.project_db import pjt_wire_marker as _wire_marker
    from ..ui import mainframe as _mainframe


class WireMarker(_ObjectBase):

    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_wire_marker.PJTWireMarker"):

        super().__init__(mainframe)

        self.obj2d = _wire_marker2d.WireMarker(mainframe.editor2d, db_obj)
        self.obj3d = _wire_marker3d.WireMarker(mainframe.editor3d, db_obj)

    def select2d(self, evt):
        pass

    def select3d(self, evt):
        pass


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
