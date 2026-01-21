from typing import TYPE_CHECKING

import wx

from . import ObjectBase as _ObjectBase
from .objects3d import bundle_layout as _bundle_layout


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout


class BundleLayout(_ObjectBase):
    obj3d: _bundle_layout.BundleLayout = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):
        super().__init__(mainframe)

        self.db_obj = db_obj
        self.obj3d = _bundle_layout.BundleLayout(mainframe.editor3d, db_obj)


class BundleLayoutMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Transition')
        canvas.Bind(wx.EVT_MENU, self.on_add_transition, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

    def on_add_transition(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()
