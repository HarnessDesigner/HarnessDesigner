from typing import TYPE_CHECKING

import wx
import time

from wx.lib.agw import aui
from ..widgets import aui_toolbar

from .. import config as _config
from ..objects import project as _project

if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db


class Config(metaclass=_config.Config):
    position = ()
    size = ()

    ui_perspective = (
        'layout2|'
        'name=editor3d_toolbar;caption=;minimode=1;state=67382012;dir=1;layer=10;row=0;pos=0;prop=100000;bestw=568;besth=58;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|'
        'name=editors;caption=;minimode=1;state=2944;dir=5;layer=0;row=0;pos=0;prop=100000;bestw=200;besth=200;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|'
        'name=db_editor;caption=DB Editor;minimode=1;state=402919420;dir=3;layer=0;row=0;pos=0;prop=100000;bestw=0;besth=0;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|'
        'name=obj_selected;caption=Selected Object;minimode=1;state=402919420;dir=2;layer=0;row=0;pos=0;prop=100000;bestw=20;besth=20;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|'
        'name=editor2d_toolbar;caption=;minimode=1;state=67382012;dir=3;layer=10;row=0;pos=0;prop=100000;bestw=568;besth=58;minw=-1;minh=-1;maxw=-1;maxh=-1;floatx=-1;floaty=-1;floatw=-1;floath=-1;notebookid=-1;transparent=255|'
        'dock_size(1,10,0)=60|'
        'dock_size(5,0,0)=202|'
        'dock_size(3,0,0)=265|'
        'dock_size(2,0,0)=251|'
        'dock_size(3,10,0)=10|'
    )


_mainframe: "MainFrame" = None


class MainFrame(wx.Frame):
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GLBTables" = None
    project_db: "_project_db.PJTTables" = None
    project: _project.Project = None

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

        self.db_connector = None
        self.global_db = None
        self.project = None

        splash.SetText('Starting UI manager...')
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
        self.editor3d = editor_3d.Editor3D(self.editor_notebook)

        splash.SetText('Creating 2D editor...')
        self.editor2d = editor_2d.Editor2D(self.editor_notebook)

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

        from .. import image as _image
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


        for boot in self._boots:
            boot.close()

        for bundle in self._bundles:
            bundle.close()

        for bundle_layout in self._bundle_layouts:
            bundle_layout.close()

        for cover in self._covers:
            cover.close()

        for cpa_lock in self._cpa_locks:
            cpa_lock.close()

        for housing in self._housings:
            housing.close()

        for note in self._notes:
            note.close()

        for seal in self._seals:
            seal.close()

        for splice in self._splices:
            splice.close()

        for terminal in self._terminals:
            terminal.close()

        for tpa_lock in self._tpa_locks:
            tpa_lock.close()

        for transition in self._transitions:
            transition.close()

        for wire in self._wires:
            wire.close()

        for wire_marker in self._wire_markers:
            wire_marker.close()

        for wire_service_loop in self._wire_service_locps:
            wire_service_loop.close()

        for wire2d_layout in self._wire2d_layouts:
            wire2d_layout.close()

        for wire3d_layout in self._wire3d_layouts:
            wire3d_layout.close()

        self._wire2d_layouts = [_wire2d_layout.Wire2DLayout(self, db) for db in self.project.wire2d_layouts]
        self._wire3d_layouts = [_wire3d_layout.Wire3DLayout(self, db) for db in self.project.wire3d_layouts]
        self._splices = [_splice.Splice(self, db) for db in self.project.splices]
        self._wires = [_wire.Wire(self, db) for db in self.project.wire_markers]
        self._wire_service_locps = [_wire_service_loop.WireServiceLoop(self, db) for db in self.project.wire_service_loops]
        self._wire_markers = [_wire_marker.WireMarker(self, db) for db in self.project.wires]
        self._bundle_layouts = [_bundle_layout.BundleLayout(self, db) for db in self.project.bundle_layouts]
        self._bundles = [_bundle.Bundle(self, db) for db in self.project.bundles]
        self._transitions = [_transition.Transition(self, db) for db in self.project.transitions]
        self._seals = [_seal.Seal(self, db) for db in self.project.seals]
        self._cpa_locks = [_cpa_lock.CPALock(self, db) for db in self.project.cpa_locks]
        self._tpa_locks = [_tpa_lock.TPALock(self, db) for db in self.project.tpa_locks]
        self._covers = [_cover.Covers(self, db) for db in self.project.covers]
        self._terminals = [_terminal.Terminal(self, db) for db in self.project.terminals]
        self._housings = [_housing.Housing(self, db) for db in self.project.housings]
        self._boots = [_boot.Boot(self, db) for db in self.project.boots]
        self._notes = [_note.Note(self, db) for db in self.project.notes]

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
            self.db_editor.load_db(self.global_db)
            self.project = _project.Project(self)
            self.project.select_project()

        wx.CallAfter(_do)
