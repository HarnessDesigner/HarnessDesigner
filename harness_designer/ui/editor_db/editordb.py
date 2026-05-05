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
    from ...database import global_db as _global_db
    from .. import mainframe as _mainframe


class EditorDB(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = EditorDBPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('editor_db')
        self.CaptionVisible(True)
        self.Floatable(True)
        self.MinimizeButton(True)
        self.MaximizeButton(True)
        self.Dockable(True)
        self.CloseButton(True)
        self.PaneBorder(True)
        self.Caption('Database Editor')
        self.DestroyOnClose(False)
        self.Gripper(True)
        self.Bottom()
        self.Resizable(True)
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        aui.AuiPaneInfo.Show(self)
        self.manager.Update()

    def Show(self, show=True):
        aui.AuiPaneInfo.Show(self, show)
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.editor.load_db(g_db)

    @property
    def accessories(self):
        return self.editor.accessories

    @property
    def boots(self):
        return self.editor.boots

    @property
    def bundle_covers(self):
        return self.editor.bundle_covers

    @property
    def covers(self):
        return self.editor.covers

    @property
    def cpa_locks(self):
        return self.editor.cpa_locks

    @property
    def housings(self):
        return self.editor.housings

    @property
    def seals(self):
        return self.editor.seals

    @property
    def splices(self):
        return self.editor.splices

    @property
    def terminals(self):
        return self.editor.terminals

    @property
    def tpa_locks(self):
        return self.editor.tpa_locks

    @property
    def transitions(self):
        return self.editor.transitions

    @property
    def wires(self):
        return self.editor.wires

    @property
    def wire_markers(self):
        return self.editor.wire_markers


class EditorDBPanel(aui.AuiNotebook):

    def __init__(self, parent: "_mainframe.MainFrame"):
        self.g_db: "_global_db.GLBTables" = None

        aui.AuiNotebook.__init__(self, parent, wx.ID_ANY,
                                 style=(aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT |
                                        aui.AUI_NB_TAB_MOVE | aui.AUI_NB_SCROLL_BUTTONS))

        self.mainframe = parent

        self.accessories: _accessory.AccessoriesPage = None
        self.boots: _boot.BootsPage = None
        self.bundle_covers: _bundle_cover.BundleCoversPage = None
        self.covers: _cover.CoversPage = None
        self.cpa_locks: _cpa_lock.CPALocksPage = None
        self.housings: _housing.HousingsPage = None
        self.seals: _seal.SealsPage = None
        self.splices: _splice.SplicesPage = None
        self.terminals: _terminal.TerminalsPage = None
        self.tpa_locks: _tpa_lock.TPALocksPage = None
        self.transitions: _transition.TransitionsPage = None
        self.wires: _wire.WiresPage = None
        self.wire_markers: _wire_marker.WireMarkersPage = None

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.g_db = g_db

        self.accessories = _accessory.AccessoriesPage(self, self.mainframe, 'Accessory', g_db.accessories_table)
        self.AddPage(self.accessories, 'Accessories')

        self.boots = _boot.BootsPage(self, self.mainframe, 'Boots', g_db.boots_table)
        self.AddPage(self.boots, 'Boots')

        self.bundle_covers = _bundle_cover.BundleCoversPage(self, self.mainframe, 'Bundle Cover', g_db.bundle_covers_table)
        self.AddPage(self.bundle_covers, 'Bundle Covers')

        self.covers = _cover.CoversPage(self, self.mainframe, 'Cover', g_db.covers_table)
        self.AddPage(self.covers, 'Covers')

        self.cpa_locks = _cpa_lock.CPALocksPage(self, self.mainframe, 'CPA Lock', g_db.cpa_locks_table)
        self.AddPage(self.cpa_locks, 'CPA Locks')

        self.housings = _housing.HousingsPage(self, self.mainframe, 'Housing', g_db.housings_table)
        self.AddPage(self.housings, 'Housings')

        self.seals = _seal.SealsPage(self, self.mainframe, 'Seal', g_db.seals_table)
        self.AddPage(self.seals, 'Seals')

        self.splices = _splice.SplicesPage(self, self.mainframe, 'Splice', g_db.splices_table)
        self.AddPage(self.splices, 'Splices')

        self.terminals = _terminal.TerminalsPage(self, self.mainframe, 'Terminal', g_db.terminals_table)
        self.AddPage(self.terminals, 'Terminals')

        self.tpa_locks = _tpa_lock.TPALocksPage(self, self.mainframe, 'TPA Lock', g_db.tpa_locks_table)
        self.AddPage(self.tpa_locks, 'TPA Locks')

        self.transitions = _transition.TransitionsPage(self, self.mainframe, 'Transition', g_db.transitions_table)
        self.AddPage(self.transitions, 'Transitions')

        self.wires = _wire.WiresPage(self, self.mainframe, 'Wire', g_db.wires_table)
        self.AddPage(self.wires, 'Wires')

        self.wire_markers = _wire_marker.WireMarkersPage(self, self.mainframe, 'Wire Marker', g_db.wire_markers_table)
        self.AddPage(self.wire_markers, 'Wire Markers')
