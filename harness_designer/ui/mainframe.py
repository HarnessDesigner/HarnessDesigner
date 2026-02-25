from typing import TYPE_CHECKING

import wx

from wx import aui

from .. import config as _config
from . import dialogs as _dialogs

if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db
    from ..objects import project as _project
    from .. import objects as _objects


_mainframe: "MainFrame" = None

Config = _config.Config.mainframe


class MainFrame(wx.Frame):
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GLBTables" = None
    project_db: "_project_db.PJTTables" = None
    project: "_project.Project" = None

    def __init__(self, splash):
        if not Config.size:
            w, h = wx.GetDisplaySize()

            w //= 3
            w *= 2

            h //= 3
            h *= 2

            Config.size = (w, h)

        if not Config.position:
            w, h = wx.GetDisplaySize()
            w -= Config.size[0]
            h -= Config.size[1]

            x = w // 2
            y = h // 2
            Config.position = (x, y)

        wx.Frame.__init__(self, None, wx.ID_ANY, title='Harness Designer',
                          size=Config.size, pos=Config.position,
                          style=wx.CLIP_CHILDREN | wx.CAPTION | wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.RESIZE_BORDER)

        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self.db_connector = None
        self.global_db = None
        self.project = None
        self._selected_obj: "_objects.ObjectBase" = None

        splash.SetText('Starting UI manager...')
        self.manager = aui.AuiManager(flags=aui.AUI_MGR_ALLOW_FLOATING |
                                      aui.AUI_MGR_ALLOW_ACTIVE_PANE |
                                      aui.AUI_MGR_TRANSPARENT_DRAG |
                                      aui.AUI_MGR_TRANSPARENT_HINT |
                                      aui.AUI_MGR_HINT_FADE |
                                      aui.AUI_MGR_LIVE_RESIZE)
        self.manager.SetManagedWindow(self)

        self.manager.Bind(aui.EVT_AUI_PANE_ACTIVATED, self._on_pane_activated)

        splash.SetText('Creating statusbar...')
        self.status_bar = status_bar = self.CreateStatusBar(3, id=wx.ID_ANY)
        status_bar.SetStatusText('X: 0.000000', 0)
        status_bar.SetStatusText('Y: 0.000000', 1)
        status_bar.SetStatusText('Z: 0.000000', 2)

        w, h = self.GetTextExtent(status_bar.GetStatusText(0))
        status_bar.SetStatusWidths([w + 4, w + 4, w + 4])
        status_bar.SetMinHeight(h)
        # status_bar_pane = status_bar.GetField(6)

        splash.SetText('Creating 3D editor...')
        from . import editor_3d

        self.editor3d = editor_3d.Editor3D(self)

        splash.SetText('Creating 2D editor...')
        from . import editor_2d

        self.editor2d = editor_2d.Editor2D(self)

        splash.SetText('Creating database editor...')
        from . import editor_db

        self.editor_db = editor_db.EditorDB(self)

        splash.SetText('Creating attribute editor...')
        from . import editor_obj

        self.editor_obj = editor_obj.EditorObj(self)

        splash.SetText('Creating assembly editor...')
        from . import editor_assembly

        self.editor_assembly = editor_assembly.EditorAssembly(self)

        splash.SetText('Creating toolbars...')
        from . import toolbar as _toolbar

        self.general_toolbar = _toolbar.GeneralToolbar(self)
        self.editor_toolbar = _toolbar.EditorToolbar(self)
        self.note_toolbar = _toolbar.NoteToolbar(self)
        self.object_toolbar = _toolbar.EditorObjectToolbar(self)
        self.settings3d_toolbar = _toolbar.Setting3DToolbar(self)

        splash.SetText('Loading UI perspective...')
        if Config.ui_perspective:
            print(repr(Config.ui_perspective))
            self.manager.LoadPerspective(Config.ui_perspective)

        if Config.position:
            def _do():
                self.Move(Config.position)

            wx.CallAfter(_do)
        else:
            self.CenterOnScreen()

        self.manager.Update()

        # from ..menus import menubar as _menubar
        #
        # self.menubar = _menubar.Menubar
        #
        # self.SetMenuBar(self.menubar)

    def add_housing(self, position):
        dialog = _dialogs.AddHousingDialog(self, self.global_db.housings_table)

        if dialog.ShowModal() == wx.ID_OK:
            db_id = dialog.GetValue()

            self.project.add_housing(position, db_id)

        dialog.Destroy()

    def _on_pane_activated(self, evt: aui.AuiManagerEvent):
        pane = evt.GetPane()

        if pane == self.editor2d:
            pass

        if pane == self.editor3d:
            pass

        if pane == self.editor_db:
            pass

        if pane == self.editor_obj:
            pass

        if pane == self.editor_assembly:
            pass

        evt.Skip()

    def set_selected_object(self, obj: "_objects.ObjectBase"):
        if self._selected_obj is not None:
            self._selected_obj.set_selected(False)

        if obj is not None:
            obj.set_selected(True)

        self._selected_obj = obj
        self.editor3d.set_selected_object(obj)
        self.editor2d.set_selected_object(obj)

    def add_object(self, obj):
        self.editor2d.add_object(obj)
        self.editor3d.add_object(obj)

    def get_selected_object(self) -> "_objects.ObjectBase":
        return self._selected_obj

    def on_erase_background(self, _):
        pass

    def SetStatusText(self, text, _=None):
        self.status_bar.PushStatusText(text, 4)

    def RevertStatusText(self):
        self.status_bar.PopStatusText(4)

    def Set2DCoordinates(self, x, y):
        self.status_bar.SetStatusText(f'X: {round(float(x), 4)}', 0)
        self.status_bar.SetStatusText(f'Y: {round(float(y), 4)}', 1)
        self.status_bar.SetStatusText(f'', 2)

    def Set3DCoordinates(self, x, y, z):
        self.status_bar.SetStatusText(f'X: {round(float(x), 4)}', 0)
        self.status_bar.SetStatusText(f'Y: {round(float(y), 4)}', 1)
        self.status_bar.SetStatusText(f'Z: {round(float(z), 4)}', 2)

    def on_close(self, _):
        Config.ui_perspective = self.manager.SavePerspective()

        self.editor2d.Destroy()
        self.editor3d.Destroy()
        self.editor_db.Destroy()
        self.editor_obj.Destroy()
        self.editor_assembly.Destroy()

        self.manager.UnInit()
        self.Destroy()

    def on_size(self, evt: wx.SizeEvent):
        w, h = evt.GetSize()
        Config.size = (w, h)
        evt.Skip()

    def on_move(self, evt):
        x, y = evt.GetPosition()
        Config.position = (x, y)
        evt.Skip()

    def unload(self):
        pass

    def open_database(self, splash):
        from ..database.db_connectors import SQLConnector

        self.db_connector = SQLConnector(self)
        self.db_connector.connect()

        from ..database import global_db
        from ..database import project_db

        self.global_db = global_db.GLBTables(splash, self)
        self.project_db = project_db.PJTTables(splash, self)

    def Show(self, flag=True):
        wx.Frame.Show(self, flag)

        def _do():
            from ..objects import project as _proj

            self.editor_db.load_db(self.global_db)
            self.project = _proj.Project.select_project(self)

        wx.CallAfter(_do)
