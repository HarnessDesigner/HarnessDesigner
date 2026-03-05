from typing import TYPE_CHECKING

import wx

from wx import aui

from .. import config as _config
from . import dialogs as _dialogs
from ..gl import canvas3d as _canvas3d


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

        splash.SetText('Startup logging ...')

        from .. import logger
        self.logger = logger.Log()

        splash.SetLogger(self.logger)

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

        splash.SetText('Creating object browser...')
        from . import object_browser

        self.object_browser = object_browser.ObjectBrowser(self)

        splash.SetText('Creating log viewer...')
        from . import log_viewer

        self.log_viewer = log_viewer.LogViewer(self)

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
        #
        # self.editor3d.Bind(_canvas3d.EVT_GL_LEFT_DOWN, self._on_left_down_3d)
        # self.editor3d.Bind(_canvas3d.EVT_GL_LEFT_UP, self._on_left_up_3d)
        #
        # self.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_SELECTED, self._on_object_selected_3d)
        # self.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_UNSELECTED, self._on_object_unselected_3d)
        #
        # self.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_DRAG, self._on_object_drag_3d)
        #
        # self.editor3d.Bind(_canvas3d.EVT_GL_OBJECT_ACTIVATED, self._on_object_activated_3d)

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

    def add_object(self, obj):
        self.editor2d.add_object(obj)
        self.editor3d.add_object(obj)

    def remove_object(self, obj):
        self.editor2d.remove_object(obj)
        self.editor3d.remove_object(obj)

    def _set_selected(self, obj: "_objects.ObjectBase"):
        self._selected_obj = obj
        self.editor3d.set_selected(obj)
        self.editor2d.set_selected(obj)

    def set_selected(self, obj: "_objects.ObjectBase"):
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self) -> "_objects.ObjectBase":
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
        print('Harness Designer shutting down')

        print('Saving UI layout...')
        Config.ui_perspective = self.manager.SavePerspective()

        print('Closing 2D Editor....')
        self.editor2d.Destroy()

        print('Closing 3D Editor....')
        self.editor3d.Destroy()

        print('Closing Database Editor....')
        self.editor_db.Destroy()

        print('Closing Object Editor....')
        self.editor_obj.Destroy()

        print('Closing Assembly Editor....')
        self.editor_assembly.Destroy()

        print('Closing Log Viewer....')
        self.log_viewer.Destroy()

        print('Uninitizing UI Manager...')
        self.manager.UnInit()

        print('Closing UI')
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

    def _on_left_down_3d(self, evt: _canvas3d.GLEvent):
        mode = self.editor_toolbar.get_mode()

        if self._mode == self.ID_CONNECTOR:
            evt.StopPropagation()
            self.add_housing(evt.GetWorldPosition())
        elif self._mode == self.ID_TERMINAL:
            evt.StopPropagation()
            self.mainframe.add_terminal(evt.GetWorldPosition())
        elif self._mode == self.ID_WIRE:
            evt.StopPropagation()
            self.mainframe.add_wire(evt.GetWorldPosition())
        elif self._mode == self.ID_SPLICE:
            evt.StopPropagation()
            self.mainframe.add_splice(evt.GetWorldPosition())
        elif self._mode == self.ID_NOTE:
            evt.StopPropagation()
            self.mainframe.add_note(evt.GetWorldPosition())
        elif self._mode == self.ID_CIRCLE:
            evt.StopPropagation()
            self.mainframe.add_circle(evt.GetWorldPosition())
        elif self._mode == self.ID_SQUARE:
            evt.StopPropagation()
            self.mainframe.add_square(evt.GetWorldPosition())
        elif self._mode == self.ID_TRANSITION:
            evt.StopPropagation()
            self.mainframe.add_transition(evt.GetWorldPosition())
        elif self._mode == self.ID_SEAL:
            evt.StopPropagation()
            self.mainframe.add_seal(evt.GetWorldPosition())
        elif self._mode == self.ID_BUNDLE_COVER:
            evt.StopPropagation()
            self.mainframe.add_bundle(evt.GetWorldPosition())
        elif self._mode == self.ID_TPA_LOCK:
            evt.StopPropagation()
            self.mainframe.add_tpa_lock(evt.GetWorldPosition())
        elif self._mode == self.ID_CPA_LOCK:
            evt.StopPropagation()
            self.mainframe.add_cpa_lock(evt.GetWorldPosition())
        elif self._mode == self.ID_ZOOM_IN:
            evt.StopPropagation()
            self.mainframe.editor3d.Zoom(1.0)
        elif self._mode == self.ID_ZOOM_OUT:
            evt.StopPropagation()
            self.mainframe.editor3d.Zoom(-1.0)

        evt.Skip()

    def _on_left_up_3d(self, evt: _canvas3d.GLEvent):
        if self._mode in (self.ID_ZOOM_IN, self.ID_ZOOM_OUT):
            evt.StopPropagation()

        evt.Skip()

