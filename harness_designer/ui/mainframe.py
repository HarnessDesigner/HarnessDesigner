from typing import TYPE_CHECKING

import wx
from wx import aui

from .. import config as _config


class Config(_config.Config):
    position = (0, 0)
    size = (1024, 768)


if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db


class MainFrame(wx.Frame):
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GlobalDB" = None
    project: "_project_db.Project" = None

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, title='Harness Designer',
                          size=Config.size, pos=Config.position)

        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SIZE, self.on_size)

        self.db_connector = None
        self.global_db = None
        self.project = None

        # aui.AUI_MGR_ALLOW_FLOATING
        # aui.AUI_MGR_ALLOW_ACTIVE_PANE
        # aui.AUI_MGR_TRANSPARENT_DRAG
        # aui.AUI_MGR_TRANSPARENT_HINT
        # aui.AUI_MGR_HINT_FADE
        # aui.AUI_MGR_LIVE_RESIZE

        self.manager = aui.AuiManager()
        self.manager.SetManagedWindow(self)

        # self.manager.AddPane
        # self.manager.LoadPaneInfo
        # self.manager.LoadPerspective
        #
        # self.manager.SavePaneInfo
        # self.manager.SavePerspective
        #
        # self.manager.Update

        self.editor_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                               style=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TOP)

        from .. import editor_3d
        from .. import editor_2d

        self.editor3d = editor_3d.Editor3D(self.editor_notebook)

        self.editor_notebook.AddPage(self.editor3d, '3D View')

        self.editor2d = editor_2d.Editor2D(self.editor_notebook)
        self.editor_notebook.AddPage(self.editor2d, 'Schematic View')

        self.attribute_notebook = aui.AuiNotebook(self, wx.ID_ANY,
                                                  style=aui.AUI_NB_TAB_MOVE | aui.AUI_NB_BOTTOM)

        self.editor_pane = (
            aui.AuiPaneInfo()
            .CenterPane()
            .Floatable(False)
            .Center()
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

        self.manager.AddPane(self.editor_notebook, self.editor_pane)
        self.attribute_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Center()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('attributes')
            .CaptionVisible(True)
            .PaneBorder(True)
            .CloseButton(False)
            .MaximizeButton(False)
            .MinimizeButton(False)
            .PinButton(False)
            .DestroyOnClose(False)
            .Caption('Part Attributes')
            .Show()
        )

        self.manager.AddPane(self.attribute_notebook, self.attribute_pane)

        self.editor2d_toolbar = aui.AuiToolBar(self)

        self.editor2d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Center()
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

        self.editor3d_toolbar = aui.AuiToolBar(self)

        self.editor3d_toolbar_pane = (
            aui.AuiPaneInfo()
            .Bottom()
            .Floatable(True)
            .Top()
            .Gripper(True)
            .Resizable(True)
            .Movable(True)
            .Name('editor3d_toolbar')
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

    def on_size(self, evt: wx.SizeEvent):
        w, h = evt.GetSize()
        Config.size = (w, h)
        evt.Skip()

    def on_move(self, evt):
        x, y = evt.GetPosition()
        Config.position = (x, y)
        evt.Skip()



    def Show(self, flag=True):
        wx.Frame.Show(self, flag)

        def _do():
            from ..database.db_connectors import SQLConnector
            self.db_connector = SQLConnector(self)
            self.db_connector.connect()

            from ..database import global_db
            from ..database import project_db

            self.global_db = global_db.GlobalDB(self)
            self.project = project_db.Project(self)

            self.project.select_project()

        wx.CallAfter(_do)

    #
    #
    # CavityViewPanel
    # SchematicViewPanel
    # HTMLViewPanel
    # PythonViewPanel
