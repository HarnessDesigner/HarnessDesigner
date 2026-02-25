from typing import TYPE_CHECKING

import wx
from wx import aui


from . import accessory as _accessory
from . import boot as _boot
from . import bundle_cover as _bundle_cover
from . import cover as _cover
from . import cpa_lock as _cpa_lock
from . import housing as _housing
from . import seal as _seal
from . import splice as _splice
from . import terminal as _terminal
from . import tpa_lock as _tpa_lock
from . import transition as _transition
from . import wire as _wire
from . import wire_marker as _wire_marker


if TYPE_CHECKING:
    from .. import global_db as _global_db
    from .. import mainframe as _mainframe



class EditorDB(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = EditorDBPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('editor_db')
        self.CaptionVisible()
        self.Floatable()
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CloseButton(False)
        self.PaneBorder()
        self.Caption('Database Editor')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        self.Show()
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.editor.load_db(g_db)


class EditorDBPanel(aui.AuiNotebook):

    def __init__(self, parent: "_mainframe.MainFrame"):
        self.g_db: "_global_db.GLBTables" = None

        aui.AuiNotebook.__init__(self, parent, wx.ID_ANY,
                                 style=(aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT |
                                        aui.AUI_NB_TAB_MOVE | aui.AUI_NB_SCROLL_BUTTONS))

        self.mainframe = parent

        self.accessories: _accessory.AccessoriesPanel = None
        self.boots: _boot.BootsPanel = None
        self.bundle_covers: _bundle_cover.BundleCoversPanel = None
        self.covers: _cover.CoversPanel = None
        self.cpa_locks: _cpa_lock.CPALocksPanel = None
        self.housings: _housing.HousingsPanel = None
        self.seals: _seal.SealsPanel = None
        self.splices: _splice.SplicesPanel = None
        self.terminals: _terminal.TerminalsPanel = None
        self.tpa_locks: _tpa_lock.TPALocksPanel = None
        self.transitions: _transition.TransitionsPanel = None
        self.wires: _wire.WiresPanel = None
        self.wire_markers: _wire_marker.WireMarkerPanel = None

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.g_db = g_db

        self.accessories = _accessory.AccessoriesPanel(self, g_db.accessories_table)
        self.AddPage(self.accessories, 'Accessories')

        self.boots = _boot.BootsPanel(self, g_db.boots_table)
        self.AddPage(self.boots, 'Boots')

        self.bundle_covers = _bundle_cover.BundleCoversPanel(self, g_db.bundle_covers_table)
        self.AddPage(self.bundle_covers, 'Bundle Covers')

        self.covers = _cover.CoversPanel(self, g_db.covers_table)
        self.AddPage(self.covers, 'Covers')

        self.cpa_locks = _cpa_lock.CPALocksPanel(self, g_db.cpa_locks_table)
        self.AddPage(self.cpa_locks, 'CPA Locks')

        self.housings = _housing.HousingsPanel(self, g_db.housings_table)
        self.AddPage(self.housings, 'Housings')

        self.seals = _seal.SealsPanel(self, g_db.seals_table)
        self.AddPage(self.seals, 'Seals')

        self.splices = _splice.SplicesPanel(self, g_db.splices_table)
        self.AddPage(self.splices, 'Splices')

        self.terminals = _terminal.TerminalsPanel(self, g_db.terminals_table)
        self.AddPage(self.terminals, 'Terminals')

        self.tpa_locks = _tpa_lock.TPALocksPanel(self, g_db.tpa_locks_table)
        self.AddPage(self.tpa_locks, 'TPA Locks')

        self.transitions = _transition.TransitionsPanel(self, g_db.transitions_table)
        self.AddPage(self.transitions, 'Transitions')

        self.wires = _wire.WiresPanel(self, g_db.wires_table)
        self.AddPage(self.wires, 'Wires')

        self.wire_markers = _wire_marker.WireMarkerPanel(self, g_db.wire_markers_table)
        self.AddPage(self.wire_markers, 'Wire Markers')
