from typing import TYPE_CHECKING

import wx

from . import ObjectBase as _ObjectBase


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_note as _pjt_note

    from .objects2d import note as _note2d
    from .objects3d import note as _note3d


class Note(_ObjectBase):
    obj2d: "_note2d.Note" = None
    obj3d: "_note3d.Note" = None

    def __init__(
        self, mainframe: "_ui.MainFrame",
        db_obj: "_pjt_note.PJTNote"
    ):
        super().__init__(mainframe)

        self.db_obj = db_obj

        self.obj2d = _note2d.Note(mainframe.editor2d, db_obj)
        self.obj3d = _note3d.Note(mainframe.editor3d, db_obj)


class NoteMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Set Text')
        canvas.Bind(wx.EVT_MENU, self.on_set_text, id=item.GetId())

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_set_text(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
