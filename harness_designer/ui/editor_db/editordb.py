# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget
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
from .. import dock_base as _dock_base


if TYPE_CHECKING:
    from ...database import global_db as _global_db
    from .. import mainframe as _mainframe


class EditorDB(_dock_base.DockBase):
    """
    Wrapper that creates the dock widget and owns the EditorDBPanel.

    In the wx version this subclassed aui.AuiPaneInfo and registered
    itself with the AuiManager directly. In Qt, dock management belongs
    to QMainWindow (Phase 2). EditorDB now acts as a thin coordinator
    that holds the panel and exposes the same public surface.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorDB` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = EditorDBPanel(mainframe)
        super().__init__(mainframe, 'Database Editor', 'editor_db',
                         Qt.DockWidgetArea.BottomDockWidgetArea)

    @property
    def editor(self) -> "EditorDBPanel":
        return self._ui_obj

    def load_db(self, g_db: "_global_db.GLBTables") -> None:
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param g_db: Value for ``g_db``.
        :type g_db: :class:`_global_db.GLBTables`
        """
        self._ui_obj.load_db(g_db)

    @property
    def accessories(self) -> _accessory.AccessoriesPage:
        """Return the accessories.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.accessories

    @property
    def boots(self) -> _boot.BootsPage:
        """Return the boots.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.boots

    @property
    def bundle_covers(self) -> _bundle_cover.BundleCoversPage:
        """Return the bundle covers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.bundle_covers

    @property
    def covers(self) -> _cover.CoversPage:
        """Return the covers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.covers

    @property
    def cpa_locks(self) -> _cpa_lock.CPALocksPage:
        """Return the CPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.cpa_locks

    @property
    def housings(self) -> _housing.HousingsPage:
        """Return the housings.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.housings

    @property
    def seals(self) -> _seal.SealsPage:
        """Return the seals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.seals

    @property
    def splices(self) -> _splice.SplicesPage:
        """Return the splices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.splices

    @property
    def terminals(self) -> _terminal.TerminalsPage:
        """Return the terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.terminals

    @property
    def tpa_locks(self) -> _tpa_lock.TPALocksPage:
        """Return the TPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.tpa_locks

    @property
    def transitions(self) -> _transition.TransitionsPage:
        """Return the transitions.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.transitions

    @property
    def wires(self) -> _wire.WiresPage:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.wires

    @property
    def wire_markers(self) -> _wire_marker.WireMarkersPage:
        """Return the wire markers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ui_obj.wire_markers


class EditorDBPanel(QTabWidget):
    """The notebook panel that contains one tab per component type.

    Replaces aui.AuiNotebook. QTabWidget provides the same tab strip,
    tab splitting is not reproduced (AUI_NB_TAB_SPLIT has no Qt
    equivalent and was rarely used interactively).
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorDBPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """
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
        """Load the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param g_db: Value for ``g_db``.
        :type g_db: :class:`_global_db.GLBTables`
        """
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

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.update()
