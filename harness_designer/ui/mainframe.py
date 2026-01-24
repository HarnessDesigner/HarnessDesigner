from typing import TYPE_CHECKING

import wx

from wx import aui
from ..widgets import aui_toolbar

from .. import Config

if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db
    from ..objects import project as _project
    from .. import objects as _objects


_mainframe: "MainFrame" = None

Config = Config.mainframe


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

        # self.manager.AddPane
        # self.manager.LoadPaneInfo
        # self.manager.LoadPerspective
        #
        # self.manager.SavePaneInfo
        # self.manager.SavePerspective
        #
        # self.manager.Update

        splash.SetText('Creating statusbar...')
        self.status_bar = status_bar = self.CreateStatusBar(6, id=wx.ID_ANY)
        status_bar.SetStatusText('X: 0.0000', 0)
        status_bar.SetStatusText('Y: 0.0000', 1)
        status_bar.SetStatusText('Z: 0.0000', 2)
        status_bar.SetStatusText('Loading....', 4)

        w, h = self.GetTextExtent(status_bar.GetStatusText(0))
        status_bar.SetStatusWidths([w + 4, w + 4, w + 4, -1, -2, -3])
        status_bar.SetMinHeight(h)
        # status_bar_pane = status_bar.GetField(6)

        self.progress_ctrl = wx.Gauge(self.status_bar, wx.ID_ANY, range=100, size=(100, h), pos=((w + 4) * 3 + 150, 0), style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.progress_ctrl.Show(False)

        self.progress_ctrl.SetRange(100)
        self.progress_ctrl.SetValue(0)

        splash.SetText('Creating editor notebook...')
        self.editor_notebook = aui.AuiNotebook(self, wx.ID_ANY, style=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TOP)

        from .. import editor_3d
        from .. import editor_2d
        from . import object_panel
        from ..database import editor as db_editor

        splash.SetText('Creating 3D editor...')
        self.editor3d: editor_3d.Editor3D = editor_3d.Editor3D(self.editor_notebook, self)

        splash.SetText('Creating 2D editor...')
        self.editor2d: editor_2d.Editor2D = editor_2d.Editor2D(self.editor_notebook)

        splash.SetText('Creating database editor...')
        self.db_editor = db_editor.DBEditorPanel(self)

        splash.SetText('Creating attribute editor...')
        self.obj_selected = object_panel.ObjectSelectedPanel(self)

        splash.SetText('Creating toolbars...')
        self.toolbar = aui_toolbar.AuiToolBar(self, style=aui.AUI_TB_GRIPPER | aui.AUI_TB_TEXT)

        self.editor_notebook.AddPage(self.editor3d, '3D View')
        self.editor_notebook.AddPage(self.editor2d, 'Schematic View')

        splash.SetText('Creating editor panes...')
        self.editor_pane = (
            aui.AuiPaneInfo()
            .CenterPane()
            .Floatable(False)
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editors')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
        )

        splash.SetText('Creating database editor pane...')
        self.db_editor_pane = (
            aui.AuiPaneInfo()
            .Floatable(True)
            .Bottom()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('db_editor')
            .CaptionVisible(True)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(True)
            .MinimizeButton(True)
            .PinButton(False)
            .DestroyOnClose(False)
            .Caption('DB Editor')
            .Show()
        )

        splash.SetText('Creating attributes editor pane...')
        self.obj_selected_pane = (
            aui.AuiPaneInfo()
            .Floatable(True)
            .Right()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('obj_selected')
            .CaptionVisible(True)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(True)
            .MinimizeButton(True)
            .PinButton(False)
            .DestroyOnClose(False)
            .Caption('Selected Object')
            .Show()
        )

        splash.SetText('Creating toolbar panes...')
        self.toolbar_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor2d_toolbar')
            .CaptionVisible(False)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Show()
            .ToolbarPane()
        )

        self.toolbar.Realize()

        self.manager.AddPane(self.editor_notebook, self.editor_pane)
        self.manager.AddPane(self.db_editor, self.db_editor_pane)
        self.manager.AddPane(self.obj_selected, self.obj_selected_pane)
        self.manager.AddPane(self.toolbar, self.toolbar_pane)
        self.manager.Update()

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

    def set_selected_object(self, obj: "_objects.ObjectBase"):
        if self._selected_obj is not None:
            self._selected_obj.set_selected(False)

        if obj is not None:
            obj.set_selected(True)

        self._selected_obj = obj
        self.editor3d.set_selected_object(obj)
        self.editor2d.set_selected_object(obj)

    def get_selected_object(self) -> "_objects.ObjectBase":
        return self._selected_obj

    def on_erase_background(self, _):
        pass

    def ShowProgress(self, obj_count):
        self.progress_ctrl.SetRange(obj_count)
        self.progress_ctrl.SetValue(0)
        x = self.GetTextExtent(f'{obj_count} of {obj_count}')[0]
        self.status_bar.Move((x, 0))
        self.progress_ctrl.Show(True)
        self.status_bar.SetStatusText(f'0 of {obj_count}', 4)

    def IncrementProgress(self):
        value = self.progress_ctrl.GetValue() + 1

        if value > self.progress_ctrl.GetRange():
            self.progress_ctrl.Show(False)
            self.status_bar.SetStatusText(f'Ready', 4)
        else:
            self.progress_ctrl.SetValue(value)
            self.status_bar.SetStatusText(f'{value} of {self.progress_ctrl.GetRange()}', 4)

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
        self.editor3d.Destroy()
        self.editor2d.Destroy()

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

            self.db_editor.load_db(self.global_db)
            self.project = _proj.Project.select_project(self)

        wx.CallAfter(_do)
