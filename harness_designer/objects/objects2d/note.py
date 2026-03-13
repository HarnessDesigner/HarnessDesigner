
from typing import TYPE_CHECKING

import wx

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus



if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


class Note(_base2d.Base2D):
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        _base2d.Base2D.__init__(self, parent, db_obj)

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle2d

        self._color = db_obj.color.ui

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)


class NoteMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

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