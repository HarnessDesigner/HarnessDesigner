from typing import TYPE_CHECKING

import wx

from . import ObjectBase as _ObjectBase
from .objects3d import tpa_lock as _tpa_lock
from ..widgets.context_menus import RotateMenu, MirrorMenu


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_tpa_lock as _pjt_tpa_lock


class TPALock(_ObjectBase):
    obj3d: _tpa_lock.TPALock = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_tpa_lock.PJTTPALock"):

        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj3d = _tpa_lock.TPALock(mainframe.editor3d, db_obj)



class TPALockMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = RotateMenu(canvas, selected)

        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = MirrorMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

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

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()

