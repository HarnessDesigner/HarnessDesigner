from typing import TYPE_CHECKING

import wx
from wx.lib.agw import aui
from ..widgets import aui_toolbar

from .. import config as _config
from ..objects import project as _project

if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db


class Config(metaclass=_config.Config):
    position = (0, 0)
    size = (1024, 768)


class MainFrame(wx.Frame):
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GLBTables" = None
    project: _project.Project = None

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, title='Harness Designer',
                          size=Config.size, pos=Config.position, style=wx.CLIP_CHILDREN | wx.CAPTION | wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.RESIZE_BORDER)

        self.Bind(wx.EVT_MOVE, self.on_move)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.db_connector = None
        self.global_db = None
        self.project = None

        print('starting manager')
        self.manager = aui.AuiManager(agwFlags=aui.AUI_MGR_ALLOW_FLOATING |
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
        self.status_bar = status_bar = self.CreateStatusBar(6, id=wx.ID_ANY)
        status_bar.SetStatusText('X: 0.0000', 0)
        status_bar.SetStatusText('Y: 0.0000', 1)
        status_bar.SetStatusText('Z: 0.0000', 2)
        status_bar.SetStatusText('Loading....', 4)

        w, h = self.GetTextExtent(status_bar.GetStatusText(0))
        status_bar.SetStatusWidths([w + 4, w + 4, w + 4, -1, -2, -3])
        status_bar.SetMinHeight(h)
        # status_bar_pane = status_bar.GetField(6)

        self.progress_ctrl = wx.Gauge(self.status_bar, wx.ID_ANY, range=100, size=(-1, h), style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.progress_ctrl.Show(False)

        self.progress_ctrl.SetRange(100)
        self.progress_ctrl.SetValue(0)

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
            .Floatable(True)
            .Bottom()
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

        from .. import image as _image

        self.editor2d_toolbar = aui_toolbar.AuiToolBar(self, style=aui.AUI_TB_GRIPPER | aui.AUI_TB_TEXT)
        self.editor2d_toolbar.Realize()
        self.editor2d_toolbar_pane = (
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
        self.manager.AddPane(self.editor2d_toolbar, self.editor2d_toolbar_pane)

        self.manager.Update()

        self._object_count = 0

        self._wires = []
        self._bundles = []
        self._bundle_layouts = []
        self._housings = []
        self._splices = []
        self._transitions = []
        self._wire_2d_layouts = []
        self._wire_3d_layouts = []

    @property
    def object_count(self):
        return self._object_count

    @object_count.setter
    def object_count(self, value: int):
        self._object_count = value
        self.progress_ctrl.Show(True)
        self.progress_ctrl.SetRange(value)
        self.progress_ctrl.SetValue(0)
        self.status_bar.SetStatusText(f'0 of {value}', 4)

    def SetProgress(self, value):
        if value > self._object_count:
            self.progress_ctrl.Show(False)
            self.status_bar.SetStatusText(f'Ready', 4)

        else:
            self.progress_ctrl.SetValue(value)
            self.status_bar.SetStatusText(f'{value} of {self._object_count}', 4)

    def SetStatusText(self, text, _=None):
        self.status_bar.PushStatusText(text, 4)

    def RevertStatusText(self):
        self.status_bar.PopStatusText(4)

    def Set2DCoordinates(self, x, y):
        self.status_bar.SetStatusText(f'X: {round(float(x), 4)}')
        self.status_bar.SetStatusText(f'Y: {round(float(y), 4)}')
        self.status_bar.SetStatusText(f'')

    def Set3DCoordinates(self, x, y, z):
        self.status_bar.SetStatusText(f'X: {round(float(x), 4)}')
        self.status_bar.SetStatusText(f'Y: {round(float(y), 4)}')
        self.status_bar.SetStatusText(f'Z: {round(float(z), 4)}')

    def on_close(self, _):
        self.manager.UnInit()
        self.editor3d.Destroy()
        self.editor2d.Destroy()
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

    def add_bundle(self, bundle):
        self._bundles.append(bundle)

    def add_bundle_layout(self, bundle_layout):
        self._bundle_layouts.append(bundle_layout)

    def load(self):
        from ..objects import (
            bundle,
            bundle_layout,
            housing,
            splice,
            terminal,
            seal,
            transition,
            wire_2d_layout,
            wire_3d_layout,
            wire
        )

        self._wires = [wire.Wire(db, self.editor3d, self.editor2d) for db in self.project.wires]
        self._bundles = [bundle.Bundle(db, self.editor3d, self.editor2d) for db in self.project.bundles]
        self._bundle_layouts = [bundle_layout.BundleLayout(db, self.editor3d, self.editor2d) for db in self.project.bundle_layouts]
        self._housings = [housing.Housing(db, self.editor3d, self.editor2d) for db in self.project.housings]
        self._splices = [splice.Splice(db, self.editor3d, self.editor2d) for db in self.project.splices]
        self._transitions = [transition.Transition(db, self.editor3d, self.editor2d) for db in self.project.transitions]
        self._wire_2d_layouts = [wire_2d_layout.Wire2DLayout(db, self.editor3d, self.editor2d) for db in self.project.wire_2d_layouts]
        self._wire_3d_layouts = [wire_3d_layout.Wire3DLayout(db, self.editor3d, self.editor2d) for db in self.project.wire_3d_layouts]

    def Show(self, flag=True):
        wx.Frame.Show(self, flag)

        def _do():
            from ..database.db_connectors import SQLConnector
            self.db_connector = SQLConnector(self)
            self.db_connector.connect()

            from ..database import global_db

            self.global_db = global_db.GLBTables(self)
            self.project = _project.Project(self)
            self.project.select_project()

        wx.CallAfter(_do)

    #
    #
    # CavityViewPanel
    # SchematicViewPanel
    # HTMLViewPanel
    # PythonViewPanel
