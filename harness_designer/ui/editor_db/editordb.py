# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget, QWidget
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

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


class EditorDB:
    """Wrapper that creates the dock widget and owns the EditorDBPanel.

    In the wx version this subclassed aui.AuiPaneInfo and registered
    itself with the AuiManager directly. In Qt, dock management belongs
    to QMainWindow (Phase 2). EditorDB now acts as a thin coordinator
    that holds the panel and exposes the same public surface.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe
        self.editor = EditorDBPanel(mainframe)

        # The dock widget itself is created and registered by mainframe
        # via mainframe._make_dock('Database Editor', 'editor_db', self.editor, Bottom).
        # EditorDB just stores the reference so callers can reach the panel.

        self._dock = mainframe._make_dock(
            title='Database Editor',
            name='editor_db',
            widget=self.editor,
            area=Qt.DockWidgetArea.BottomDockWidgetArea,
        )
        # self._dock.visibilityChanged.connect(self._on_visibility_changed)
        self._dock.show()

    def Show(self, show=True):
        self.editor.setVisible(show)

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.deleteLater()

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


class EditorDBPanel(QTabWidget):
    """The notebook panel that contains one tab per component type.

    Replaces aui.AuiNotebook. QTabWidget provides the same tab strip,
    tab splitting is not reproduced (AUI_NB_TAB_SPLIT has no Qt
    equivalent and was rarely used interactively).
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        super().__init__(parent)

        self.g_db: "_global_db.GLBTables" = None
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

        # Tab bar scrolls when there are many tabs (matches AUI_NB_SCROLL_BUTTONS)
        self.setUsesScrollButtons(True)
        self.setMovable(True)  # matches AUI_NB_TAB_MOVE

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.g_db = g_db

        self.accessories = _accessory.AccessoriesPage(
            self, self.mainframe, 'Accessory', g_db.accessories_table)
        self.addTab(self.accessories, 'Accessories')

        self.boots = _boot.BootsPage(
            self, self.mainframe, 'Boots', g_db.boots_table)
        self.addTab(self.boots, 'Boots')

        self.bundle_covers = _bundle_cover.BundleCoversPage(
            self, self.mainframe, 'Bundle Cover', g_db.bundle_covers_table)
        self.addTab(self.bundle_covers, 'Bundle Covers')

        self.covers = _cover.CoversPage(
            self, self.mainframe, 'Cover', g_db.covers_table)
        self.addTab(self.covers, 'Covers')

        self.cpa_locks = _cpa_lock.CPALocksPage(
            self, self.mainframe, 'CPA Lock', g_db.cpa_locks_table)
        self.addTab(self.cpa_locks, 'CPA Locks')

        self.housings = _housing.HousingsPage(
            self, self.mainframe, 'Housing', g_db.housings_table)
        self.addTab(self.housings, 'Housings')

        self.seals = _seal.SealsPage(
            self, self.mainframe, 'Seal', g_db.seals_table)
        self.addTab(self.seals, 'Seals')

        self.splices = _splice.SplicesPage(
            self, self.mainframe, 'Splice', g_db.splices_table)
        self.addTab(self.splices, 'Splices')

        self.terminals = _terminal.TerminalsPage(
            self, self.mainframe, 'Terminal', g_db.terminals_table)
        self.addTab(self.terminals, 'Terminals')

        self.tpa_locks = _tpa_lock.TPALocksPage(
            self, self.mainframe, 'TPA Lock', g_db.tpa_locks_table)
        self.addTab(self.tpa_locks, 'TPA Locks')

        self.transitions = _transition.TransitionsPage(
            self, self.mainframe, 'Transition', g_db.transitions_table)
        self.addTab(self.transitions, 'Transitions')

        self.wires = _wire.WiresPage(
            self, self.mainframe, 'Wire', g_db.wires_table)
        self.addTab(self.wires, 'Wires')

        self.wire_markers = _wire_marker.WireMarkersPage(
            self, self.mainframe, 'Wire Marker', g_db.wire_markers_table)
        self.addTab(self.wire_markers, 'Wire Markers')

    def Refresh(self, *args, **kwargs):
        current = self.currentWidget()
        if current is not None:
            current.Refresh()
