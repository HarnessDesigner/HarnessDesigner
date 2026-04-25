from typing import TYPE_CHECKING

import wx


if TYPE_CHECKING:
    from ... import ui as _ui


class ViewMenu(wx.Menu):

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe
        wx.Menu.__init__(self)

        menu_item = self.Append(wx.ID_ANY, 'Schematic Editor')
        mainframe.Bind(wx.EVT_MENU, self.on_show_editor2d, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'Object Editor')
        mainframe.Bind(wx.EVT_MENU, self.on_show_editor_obj, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'Log Viewer')
        mainframe.Bind(wx.EVT_MENU, self.on_show_log_viewer, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'Database Editor')
        mainframe.Bind(wx.EVT_MENU, self.on_show_editor_db, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'Assembly Editor')
        mainframe.Bind(wx.EVT_MENU, self.on_show_editor_assembly, id=menu_item.GetId())

        menu_item = self.Append(wx.ID_ANY, 'Script Editor')
        mainframe.Bind(wx.EVT_MENU, self.on_show_editor_script, id=menu_item.GetId())

    def on_show_editor2d(self, _):
        self.mainframe.editor2d.Show()

    def on_show_editor_obj(self, _):
        self.mainframe.editor_obj.Show()

    def on_show_log_viewer(self, _):
        self.mainframe.log_viewer.Show()

    def on_show_editor_db(self, _):
        self.mainframe.editor_db.Show()

    def on_show_editor_assembly(self, _):
        self.mainframe.editor_assembly.Show()

    def on_show_editor_script(self, _):
        # self.mainframe.editor_script.Show()
        pass
