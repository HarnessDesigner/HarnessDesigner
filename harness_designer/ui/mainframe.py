# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

from PySide6 import QtWidgets
from PySide6 import QtCore

from .. import config as _config
from .dialogs import closing_dialog as _closing_dialog
from . import toolbar as _toolbar
from .. import gl as _gl
from .. import handlers as _handlers
from .. import app as _app


if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db
    from ..objects import project as _project
    from .. import objects as _objects
    from .. import logger as _logger


_mainframe: "MainFrame" = None

Config = _config.Config.mainframe

# ---------------------------------------------------------------------------
# EVT_GL_* constants are plain strings equal to the signal names,
# so pass them directly to editor.connect() — no mapping table needed.


class MainFrame(QtWidgets.QMainWindow):
    """Represent a main frame in :mod:`harness_designer.ui.mainframe`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GLBTables" = None
    project_db: "_project_db.PJTTables" = None
    _project: "_project.Project" = None

    @property
    def project(self) -> "_project.Project":

        while self._project is None:
            self._open_project()

        return self._project

    @project.setter
    def project(self, value: Union["_project.Project", None]):
        self._project = value

    def __init__(self, splash, logger: "_logger.Log"):
        """Initialise the :class:`MainFrame` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        :param logger: Value for ``logger``.
        :type logger: :class:`_logger.Log`
        """
        QtWidgets.QMainWindow.__init__(self)

        self.config = _config.Config
        self._is_closing = False

        splash.SetText('Startup logging ...')
        splash.flush()

        self.logger = logger
        self._clone_obj = None

        if Config.size is None:
            screen = self.screen()
            geo = screen.availableGeometry()
            w = int(geo.width() * 0.95)
            h = int(geo.height() * 0.95)
            Config.size = (w, h)

        if Config.position is None:
            screen = self.screen()
            geo = screen.availableGeometry()
            x = (geo.width() - Config.size[0]) // 2
            y = (geo.height() - Config.size[1]) // 2
            Config.position = (x, y)

        self.setWindowTitle('Harness Designer')
        self.resize(*Config.size)
        self.move(*Config.position)

        self.db_connector = None
        self.global_db = None
        self.project = None
        self._selected_obj: "_objects.ObjectBase" = None
        self._obj_handler: _handlers.HandlerBase = None

        # Set by a mouse handler immediately before it triggers selection,
        # so _set_selected knows which viewer the click originated in and
        # can skip re-centering that one -- the user just clicked the
        # object, it's already exactly where they want it on screen.
        # Programmatic selection (tree view, "Select" menu action, etc.)
        # leaves this None, so all three viewers still center on it as
        # before.
        self._selection_source_editor: str = None

        # ------------------------------------------------------------------
        # Docking setup
        # Qt QMainWindow has built-in dock support. For full AUI-equivalent
        # floating/tabbing behaviour (Phase 17 note: PySide6-QtAds was
        # considered but QMainWindow dock widgets faithfully reproduce the
        # pane layout needed here; QtAds would be needed only if free-
        # floating drag-and-tab between arbitrary positions is required).
        # ------------------------------------------------------------------
        self.setDockOptions(
            QtWidgets.QMainWindow.DockOption.AnimatedDocks |
            QtWidgets.QMainWindow.DockOption.AllowNestedDocks |
            QtWidgets.QMainWindow.DockOption.AllowTabbedDocks
        )

        splash.SetText('Creating statusbar...')
        splash.flush()

        # ------------------------------------------------------------------
        # Status bar — 3 permanent QLabel widgets replace CreateStatusBar(3).
        # showMessage() is for transient notifications; coordinates use
        # permanent widgets so they are never overwritten by transient text.
        # ------------------------------------------------------------------
        status_bar = QtWidgets.QStatusBar(self)
        self.setStatusBar(status_bar)
        self.status_bar = status_bar

        fm = self.fontMetrics()
        coord_text = 'X: 0.000000'
        label_width = fm.horizontalAdvance(coord_text) + 8

        self._status_x = QtWidgets.QLabel('X: 0.000000')
        self._status_x.setFixedWidth(label_width)
        self._status_y = QtWidgets.QLabel('Y: 0.000000')
        self._status_y.setFixedWidth(label_width)
        self._status_z = QtWidgets.QLabel('Z: 0.000000')
        self._status_z.setFixedWidth(label_width)

        status_bar.addPermanentWidget(self._status_x)
        status_bar.addPermanentWidget(self._status_y)
        status_bar.addPermanentWidget(self._status_z)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)  # Set your known max here
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(300)
        self.progress_bar.setTextVisible(True)  # Shows "X%" label inside bar
        self.progress_bar.hide()

        status_bar.addPermanentWidget(self.progress_bar)
        status_bar.showMessage("Ready")

        splash.SetText('Creating 3D editor...')
        splash.flush()

        from . import editor_3d

        self.editor3d = editor_3d.Editor3D(self)

        splash.SetText('Creating 2D editor...')
        splash.flush()

        from . import editor_2d

        self.editor2d = editor_2d.Editor2D(self)

        splash.SetText('Creating peg board editor...')
        splash.flush()

        from . import editor_pegboard

        self.editor_pegboard = editor_pegboard.EditorPegBoard(self)

        splash.SetText('Creating database editor...')
        splash.flush()

        from . import editor_db

        self.editor_db = editor_db.EditorDB(self)

        splash.SetText('Creating circuit editor...')
        splash.flush()

        from . import editor_ciruit

        self.editor_circuit = editor_ciruit.EditorCircuit(self)

        splash.SetText('Creating object editor...')
        splash.flush()

        from . import editor_obj

        self.editor_obj = editor_obj.EditorObj(self)

        splash.SetText('Creating assembly editor...')
        splash.flush()

        from . import editor_assembly

        self.editor_assembly = editor_assembly.EditorAssembly(self)

        splash.SetText('Creating object browser...')
        splash.flush()

        from . import object_browser

        self.object_browser = object_browser.ObjectBrowser(self)

        splash.SetText('Creating log viewer...')
        splash.flush()

        from . import log_viewer

        self.log_viewer = log_viewer.LogViewer(self)

        splash.SetText('Creating toolbars...')
        splash.flush()

        self.general_toolbar = _toolbar.GeneralToolbar(self)
        self.editor_toolbar = _toolbar.EditorToolbar(self)
        self.note_toolbar = _toolbar.NoteToolbar(self)
        self.object_toolbar = _toolbar.EditorObjectToolbar(self)
        self.settings3d_toolbar = _toolbar.Setting3DToolbar(self)
        self.pegboard_toolbar = _toolbar.PegBoardToolbar(self)

        splash.SetText('Loading system menu...')
        splash.flush()

        # Group the 3D, schematic, and peg board editors into one tabbed
        # notebook by default. Each dock keeps its normal Qt drag behavior
        # (AllowTabbedDocks is set above), so the user can still drag any
        # tab out into its own floating/docked window and drag it back onto
        # the tab bar to re-join the notebook — this is standard QDockWidget
        # tabbing, not custom UI. editor3d's dock is deliberately not
        # DockWidgetClosable (see editor_3d.py), so it can be floated out but
        # not closed.
        self.tabifyDockWidget(self.editor3d.dock, self.editor2d.dock)
        self.tabifyDockWidget(self.editor3d.dock, self.editor_pegboard.dock)
        self.editor3d.dock.raise_()  # 3D editor is the initially active tab

        self.setDockOptions(
            QtWidgets.QMainWindow.DockOption.GroupedDragging |
            QtWidgets.QMainWindow.DockOption.AnimatedDocks |
            QtWidgets.QMainWindow.DockOption.AllowTabbedDocks |
            QtWidgets.QMainWindow.DockOption.AllowNestedDocks)
        # QtWidgets.QMainWindow.DockOption.VerticalTabs

        self.setTabShape(QtWidgets.QTabWidget.TabShape(Config.tab_shape))

        # Tab bar on the right edge (vertical tabs) instead of Qt's default
        # bottom placement, for the dock area these three editors share.
        self.setTabPosition(
            QtCore.Qt.DockWidgetArea.AllDockWidgetAreas,
            QtWidgets.QTabWidget.TabPosition(Config.tab_location)
        )

        self.tabifyDockWidget(self.editor_obj.dock, self.object_browser.dock)
        self.tabifyDockWidget(self.editor_obj.dock, self.editor_circuit.dock)
        self.tabifyDockWidget(self.editor_obj.dock, self.editor_assembly.dock)
        self.tabifyDockWidget(self.editor_obj.dock, self.log_viewer.dock)

        self.editor3d.dock.raise_()  # 3D editor is the initially active tab

        # Tab bar on the right edge (vertical tabs) instead of Qt's default
        # bottom placement, for the dock area these three editors share.
        self.setTabPosition(
            QtCore.Qt.DockWidgetArea.AllDockWidgetAreas,
            QtWidgets.QTabWidget.TabPosition(Config.tab_location)
        )

        from . import system_menu
        self.system_menu = system_menu.SystemMenu(self)
        self.setMenuBar(self.system_menu)

        splash.SetText('Starting boot editor...')
        splash.flush()
        from ..database.project_db import pjt_boot

        pjt_boot.PJTBootsTable.start_control(self)

        splash.SetText('Starting bundle cover editor...')
        splash.flush()
        from ..database.project_db import pjt_bundle

        pjt_bundle.PJTBundlesTable.start_control(self)

        splash.SetText('Starting bundle layout editor...')
        splash.flush()
        from ..database.project_db import pjt_bundle_layout

        pjt_bundle_layout.PJTBundleLayoutsTable.start_control(self)

        splash.SetText('Starting cavity editor...')
        splash.flush()
        from ..database.project_db import pjt_cavity

        pjt_cavity.PJTCavitiesTable.start_control(self)

        splash.SetText('Starting cover editor...')
        splash.flush()
        from ..database.project_db import pjt_cover

        pjt_cover.PJTCoversTable.start_control(self)

        splash.SetText('Starting cpa lock editor...')
        splash.flush()
        from ..database.project_db import pjt_cpa_lock

        pjt_cpa_lock.PJTCPALocksTable.start_control(self)

        splash.SetText('Starting housing editor...')
        splash.flush()
        from ..database.project_db import pjt_housing

        pjt_housing.PJTHousingsTable.start_control(self)

        splash.SetText('Starting note editor...')
        splash.flush()
        from ..database.project_db import pjt_note

        pjt_note.PJTNotesTable.start_control(self)

        splash.SetText('Starting seal editor...')
        splash.flush()
        from ..database.project_db import pjt_seal

        pjt_seal.PJTSealsTable.start_control(self)

        splash.SetText('Starting splice editor...')
        splash.flush()
        from ..database.project_db import pjt_splice

        pjt_splice.PJTSplicesTable.start_control(self)

        splash.SetText('Starting terminal editor...')
        splash.flush()
        from ..database.project_db import pjt_terminal

        pjt_terminal.PJTTerminalsTable.start_control(self)

        splash.SetText('Starting tpa lock editor...')
        splash.flush()
        from ..database.project_db import pjt_tpa_lock

        pjt_tpa_lock.PJTTPALocksTable.start_control(self)

        splash.SetText('Starting transition editor...')
        splash.flush()
        from ..database.project_db import pjt_transition

        pjt_transition.PJTTransitionsTable.start_control(self)

        splash.SetText('Starting wire editor...')
        splash.flush()
        from ..database.project_db import pjt_wire

        pjt_wire.PJTWiresTable.start_control(self)

        splash.SetText('Starting wire layout editor...')
        splash.flush()
        from ..database.project_db import pjt_wire_layout

        pjt_wire_layout.PJTWireLayoutsTable.start_control(self)

        splash.SetText('Starting wire marker editor...')
        splash.flush()
        from ..database.project_db import pjt_wire_marker

        pjt_wire_marker.PJTWireMarkersTable.start_control(self)

        splash.SetText('Starting wire service loop editor...')
        splash.flush()
        from ..database.project_db import pjt_wire_service_loop

        pjt_wire_service_loop.PJTWireServiceLoopsTable.start_control(self)

        splash.SetText('Loading UI perspective...')
        splash.flush()

        # Restore saved dock layout.  saveState() returns QByteArray; we store
        # it in Config as bytes.  restoreState() accepts both QByteArray and
        # bytes directly.
        if Config.ui_perspective:
            logger.debug('SAVED UI:', repr(Config.ui_perspective))
            state = Config.ui_perspective
            self.restoreState(QtCore.QByteArray(state))

        if Config.position:
            QtCore.QTimer.singleShot(0, lambda: self.move(*Config.position))
        else:
            QtCore.QTimer.singleShot(0, self._center_on_screen)

        # ------------------------------------------------------------------
        # Connect GL canvas signals using editor3d.connect() shim.
        # editor3d.connect(signal_name, handler) calls
        # getattr(self.editor, signal_name).connect(handler) on the inner
        # QOpenGLWidget.  We derive the snake_case signal name from the
        # EVT_GL_* constants are plain strings equal to the signal names.
        # ------------------------------------------------------------------
        self._connect_editor3d_signals()
        self._connect_editor2d_signals()
        self._connect_editor_pegboard_signals()

        self.editor_toolbar.modeChanged.connect(self._on_tool_mode_change)

        # ------------------------------------------------------------------
        # Idle processing — replaces wx.EVT_IDLE.
        # A zero-interval QTimer fires as fast as the event loop allows when
        # no other events are pending, giving the same semantics as wx idle.
        # The timer is started lazily (after initializeGL) to avoid GL calls
        # before the context is ready; we use a 0ms single-shot here which
        # chains itself only when there is remaining work, matching the
        # original event.RequestMore() pattern.
        # ------------------------------------------------------------------
        self._idle_timer = QtCore.QTimer(self)
        self._idle_timer.setInterval(0)
        self._idle_timer.timeout.connect(self._on_idle)  # NOQA
        self._idle_timer.start()
        self._splash = splash

        splash.SetText('Loading Process Manager...')
        from .. import process as _process

        self.process_manager: _process.ProcessManager = _process.ProcessManager(self)

    # ------------------------------------------------------------------
    # Dock widget factory
    # ------------------------------------------------------------------

    def end_progress_bar(self):
        self.progress_bar.hide()

    def set_progress(self, value: int, label: str = None):
        """Set the progress.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        :param label: Value for ``label``.
        :type label: str | None
        """
        if label is not None:
            self.status_bar.showMessage(label)

        self.progress_bar.setValue(value)

        if value == self.progress_bar.maximum():
            self.status_bar.showMessage("Ready")
            self.progress_bar.hide()

        # Pumps the event queue so the bar/label actually repaint and
        # Windows doesn't flag the window "Not Responding" during a long
        # synchronous loop (e.g. Project.__init__'s object-loading loop) --
        # same pattern the shutdown sequence already uses (see MainFrame's
        # close handler).
        QtWidgets.QApplication.processEvents()

    def start_progress(self, label: str, max_value: int):
        """Start the progress.

        UNKNOWN details are inferred from the callable name and signature.

        :param label: Value for ``label``.
        :type label: str
        :param max_value: Value for ``max_value``.
        :type max_value: int
        """
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage(label)
        self.progress_bar.show()

    def _center_on_screen(self):
        """Execute the center on screen operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        screen = self.screen()
        geo = screen.availableGeometry()
        x = (geo.width() - self.width()) // 2
        y = (geo.height() - self.height()) // 2
        self.move(x, y)

    # ------------------------------------------------------------------
    # GL signal wiring
    # ------------------------------------------------------------------

    def _connect_editor3d_signals(self):
        """Wire all EVT_GL_* signal sentinels to their mainframe handlers."""

        self.editor3d.bind(_gl.EVT_GL_OBJECT_SELECTED, self._on_obj_selected_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_ACTIVATED, self._on_obj_activated_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_RIGHT_CLICK, self._on_obj_right_click_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_RIGHT_DCLICK, self._on_obj_right_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_MIDDLE_CLICK, self._on_obj_middle_click_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_MIDDLE_DCLICK, self._on_obj_middle_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_AUX1_CLICK, self._on_obj_aux1_click_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_AUX1_DCLICK, self._on_obj_aux1_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_AUX2_CLICK, self._on_obj_aux2_click_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_AUX2_DCLICK, self._on_obj_aux2_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_OBJECT_DRAG, self._on_obj_drag_3d)
        self.editor3d.bind(_gl.EVT_GL_KEY_DOWN, self._on_key_down_3d)
        self.editor3d.bind(_gl.EVT_GL_KEY_UP, self._on_key_up_3d)
        self.editor3d.bind(_gl.EVT_GL_MOUSE_MOVE, self._on_mouse_move_3d)
        self.editor3d.bind(_gl.EVT_GL_CAPTURE_LOST, self._on_capture_lost_3d)
        self.editor3d.bind(_gl.EVT_GL_LEFT_DOWN, self._on_left_down_3d)
        self.editor3d.bind(_gl.EVT_GL_LEFT_UP, self._on_left_up_3d)
        self.editor3d.bind(_gl.EVT_GL_LEFT_DCLICK, self._on_left_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_RIGHT_DOWN, self._on_right_down_3d)
        self.editor3d.bind(_gl.EVT_GL_RIGHT_UP, self._on_right_up_3d)
        self.editor3d.bind(_gl.EVT_GL_RIGHT_DCLICK, self._on_right_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_MIDDLE_DOWN, self._on_middle_down_3d)
        self.editor3d.bind(_gl.EVT_GL_MIDDLE_UP, self._on_middle_up_3d)
        self.editor3d.bind(_gl.EVT_GL_MIDDLE_DCLICK, self._on_middle_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX1_DOWN, self._on_aux1_down_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX1_UP, self._on_aux1_up_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX1_DCLICK, self._on_aux1_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX2_DOWN, self._on_aux2_down_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX2_UP, self._on_aux2_up_3d)
        self.editor3d.bind(_gl.EVT_GL_AUX2_DCLICK, self._on_aux2_dclick_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_ZOOM, self._on_camera_zoom_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_ORBIT, self._on_camera_orbit_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_WALK, self._on_camera_walk_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_TRUCKPEDISTAL, self._on_camera_truckpedistal_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_ROTATE, self._on_camera_rotate_3d)
        self.editor3d.bind(_gl.EVT_GL_CAMERA_RESET, self._on_camera_reset_3d)

    def _on_camera_zoom_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _on_camera_orbit_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _on_camera_walk_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _on_camera_truckpedistal_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _on_camera_rotate_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _on_camera_reset_3d(self, evt: _gl.GLCameraEvent):
        self.Set3DCoordinates(evt)

    def _connect_editor2d_signals(self):
        self.editor2d.bind(_gl.EVT_GL_OBJECT_SELECTED,      self._on_obj_selected_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_ACTIVATED, self._on_obj_activated_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_RIGHT_CLICK, self._on_obj_right_click_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_MIDDLE_CLICK, self._on_obj_middle_click_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_MIDDLE_DCLICK, self._on_obj_middle_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_AUX1_CLICK, self._on_obj_aux1_click_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_AUX1_DCLICK, self._on_obj_aux1_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_AUX2_CLICK, self._on_obj_aux2_click_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_AUX2_DCLICK, self._on_obj_aux2_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_OBJECT_DRAG, self._on_obj_drag_2d)
        self.editor2d.bind(_gl.EVT_GL_KEY_DOWN, self._on_key_down_2d)
        self.editor2d.bind(_gl.EVT_GL_KEY_UP, self._on_key_up_2d)
        self.editor2d.bind(_gl.EVT_GL_MOUSE_MOVE, self._on_mouse_move_2d)
        self.editor2d.bind(_gl.EVT_GL_CAPTURE_LOST, self._on_capture_lost_2d)
        self.editor2d.bind(_gl.EVT_GL_LEFT_DOWN, self._on_left_down_2d)
        self.editor2d.bind(_gl.EVT_GL_LEFT_UP, self._on_left_up_2d)
        self.editor2d.bind(_gl.EVT_GL_LEFT_DCLICK, self._on_left_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_RIGHT_DOWN, self._on_right_down_2d)
        self.editor2d.bind(_gl.EVT_GL_RIGHT_UP, self._on_right_up_2d)
        self.editor2d.bind(_gl.EVT_GL_RIGHT_DCLICK, self._on_right_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_MIDDLE_DOWN, self._on_middle_down_2d)
        self.editor2d.bind(_gl.EVT_GL_MIDDLE_UP, self._on_middle_up_2d)
        self.editor2d.bind(_gl.EVT_GL_MIDDLE_DCLICK, self._on_middle_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX1_DOWN, self._on_aux1_down_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX1_UP, self._on_aux1_up_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX1_DCLICK, self._on_aux1_dclick_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX2_DOWN, self._on_aux2_down_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX2_UP, self._on_aux2_up_2d)
        self.editor2d.bind(_gl.EVT_GL_AUX2_DCLICK, self._on_aux2_dclick_2d)

    def _connect_editor_pegboard_signals(self):
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_SELECTED,      self._on_obj_selected_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_ACTIVATED, self._on_obj_activated_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_RIGHT_CLICK, self._on_obj_right_click_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_MIDDLE_CLICK, self._on_obj_middle_click_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_MIDDLE_DCLICK, self._on_obj_middle_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_AUX1_CLICK, self._on_obj_aux1_click_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_AUX1_DCLICK, self._on_obj_aux1_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_AUX2_CLICK, self._on_obj_aux2_click_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_AUX2_DCLICK, self._on_obj_aux2_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_OBJECT_DRAG, self._on_obj_drag_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_KEY_DOWN, self._on_key_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_KEY_UP, self._on_key_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_MOUSE_MOVE, self._on_mouse_move_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_CAPTURE_LOST, self._on_capture_lost_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_LEFT_DOWN, self._on_left_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_LEFT_UP, self._on_left_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_LEFT_DCLICK, self._on_left_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_RIGHT_DOWN, self._on_right_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_RIGHT_UP, self._on_right_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_RIGHT_DCLICK, self._on_right_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_MIDDLE_DOWN, self._on_middle_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_MIDDLE_UP, self._on_middle_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_MIDDLE_DCLICK, self._on_middle_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX1_DOWN, self._on_aux1_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX1_UP, self._on_aux1_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX1_DCLICK, self._on_aux1_dclick_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX2_DOWN, self._on_aux2_down_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX2_UP, self._on_aux2_up_pegboard)
        self.editor_pegboard.bind(_gl.EVT_GL_AUX2_DCLICK, self._on_aux2_dclick_pegboard)

    # ------------------------------------------------------------------
    # QMainWindow event overrides (replace wx.EVT_* bindings)
    # ------------------------------------------------------------------

    def moveEvent(self, event):
        """Execute the move event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        QtWidgets.QMainWindow.moveEvent(self, event)
        QtCore.QTimer.singleShot(0, self._save_position)

    def resizeEvent(self, event):
        """Execute the resize event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        QtWidgets.QMainWindow.resizeEvent(self, event)
        QtCore.QTimer.singleShot(0, self._save_size)

    def closeEvent(self, event):
        """Execute the close event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """

        # small splash dialog appears letting the user know that the
        # application is closing. This dialog has a progress bar and a message
        # that gets set which will appear directly below the bar centered.
        # this dialog should remain on top of the application centered and have
        # no buttons to close the dialog. The dialog will close right before
        # the main application completely shuts down.

        # I would like to have a type of modal functionality where all user
        # input to the main application is no longer allowed. However, I cannot
        # use the modal of the dialog because it would take control of the main
        # thread which is something we do not want to have happen.

        # I also need to know how to exit the application gracefully once all
        # of the shutdown tasks have been completed.

        if self._is_closing:
            event.accept()
            return

        self._is_closing = True

        close_dlg = _closing_dialog.ClosingDialog(self, total_steps=10)
        close_dlg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        close_dlg.show()

        self.logger.info('Harness Designer shutting down')
        self.logger.info('Stopping Process Manager...')
        close_dlg.set_message('Stopping Process Manager...')

        self.process_manager.stop()

        def _finished():
            close_dlg.close()
            QtWidgets.QApplication.instance().quit()

        def _do():
            count = 0
            import time

            while not self.process_manager.is_stopped:
                if count == 30:
                    break

                count += 1
                time.sleep(1)

            if count == 30:
                self.logger.error('Process manager did not shut down properly...')

            close_dlg.set_step(1)
            QtWidgets.QApplication.processEvents()

            self.logger.info('Saving UI layout...')
            close_dlg.set_message('Saving UI layout...')
            QtWidgets.QApplication.processEvents()

            # saveState() returns QByteArray; store as bytes for Config
            Config.ui_perspective = bytes(self.saveState())
            close_dlg.set_step(2)
            QtWidgets.QApplication.processEvents()

            def _run(label, func, step):
                time.sleep(0.250)
                self.logger.info(label)
                close_dlg.set_message(label)
                QtWidgets.QApplication.processEvents()
                func()
                close_dlg.set_step(step)
                QtWidgets.QApplication.processEvents()

            _run('Closing 2D Editor....', self.editor2d.Destroy, 3)
            _run('Closing Peg Board Editor....', self.editor_pegboard.Destroy, 4)
            _run('Closing 3D Editor....', self.editor3d.Destroy, 5)
            _run('Closing Database Editor....', self.editor_db.Destroy, 6)
            _run('Closing Object Editor....', self.editor_obj.Destroy, 7)
            _run('Closing Assembly Editor....', self.editor_assembly.Destroy, 8)
            _run('Closing Log Viewer....', self.log_viewer.Destroy, 9)
            _run('Closing Database Connection....', self.db_connector.close, 10)

            _app.CallLater(_finished)

        _app.CallLater(_do)

        event.ignore()

    def _save_position(self):
        """Save the position.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pos = self.pos()
        Config.position = (pos.x(), pos.y())

    def _save_size(self):
        """Save the size.

        UNKNOWN details are inferred from the callable name and signature.
        """
        sz = self.size()
        Config.size = (sz.width(), sz.height())

    # ------------------------------------------------------------------
    # Idle processing (replaces wx.EVT_IDLE / event.RequestMore)
    # ------------------------------------------------------------------

    def _on_idle(self):
        """
        Called by the zero-interval QTimer whenever the event loop is idle.

        Delegates one chunk of orphan-point cleanup to the project's
        ProjectCleanup instance.  Stops the timer when there is no more
        work so the loop is not spinning while the application is truly
        idle.  The timer restarts itself the next time it runs — because
        it fires continuously while running — so there is no explicit
        restart needed when new work arrives.
        """

        return

        # if self.project is None:
        #     return
        #
        # if not self.project.cleanup.process_chunk():
        #     # No remaining work; pause idle processing.  The timer will
        #     # still fire on the next Qt event-loop pass and re-check, which
        #     # is effectively the same cost as the original wx idle pattern.
        #     pass

    # ------------------------------------------------------------------
    # Status bar helpers (public API used by canvas handlers)
    # ------------------------------------------------------------------

    def SetStatusText(self, text, _=None):
        """Execute the set status text operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: UNKNOWN
        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self.status_bar.showMessage(text)

    def RevertStatusText(self):
        """Execute the revert status text operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.status_bar.clearMessage()

    def Set3DCoordinates(self, evt: _gl.GLEvent | _gl.GLCameraEvent):
        """Execute the set 3dcoordinates operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: event.
        :type evt: UNKNOWN
        """
        if isinstance(evt, _gl.GLObjectEvent):
            obj = evt.GetEventObject()
            position = obj.position
        else:
            mouse_pos = evt.GetPosition()
            position = self.editor3d.camera.get_position_on_focal_plane(mouse_pos)

        x, y, z = position.as_float
        self._status_x.setText(f'X: {round(float(x), 4)}')
        self._status_y.setText(f'Y: {round(float(y), 4)}')
        self._status_z.setText(f'Z: {round(float(z), 4)}')

    def Set2DCoordinates(self, evt: _gl.GLEvent | _gl.GLCameraEvent):
        """Execute the set 3dcoordinates operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: event.
        :type evt: UNKNOWN
        """
        # if isinstance(evt, _gl.GLObjectEvent):
        position = evt.GetWorldPosition()
        # else:
        #     mouse_pos = evt.GetPosition()
        #     position = self.editor_pegboard.camera.get_position_on_focal_plane(mouse_pos)

        x, y, _ = position.as_float
        self._status_x.setText(f'X: {round(float(x), 4)}')
        self._status_y.setText(f'Y: {round(float(y), 4)}')
        self._status_z.setText('')

    def showEvent(self, event):
        """Execute the show event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        super().showEvent(event)

        if self._splash is not None:
            self._splash.Destroy()
            self._splash = None

        QtCore.QTimer.singleShot(0, self._open_project)

    def _open_project(self):
        from ..objects import project as _proj

        self.editor_db.load_db(self.global_db)

        self.project = _proj.Project.select_project(self)

        # Every housing/splice/transition/terminal wrapper constructed while
        # building the Project above already called add_object(), but
        # self._project was still None at that point (it isn't assigned
        # until the line above returns) — so the load_project() rebuild
        # guarded on self._project inside add_object()/remove_object() never
        # fired for any of them. Trigger it once now that a project (or
        # None, if the user canceled the open dialog) is actually assigned.
        if self._project is not None:
            self.editor_pegboard.load_project(self._project)

    # ------------------------------------------------------------------
    # GL object event handlers (3D canvas)
    # ------------------------------------------------------------------

    def _on_obj_selected_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj selected 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_unselected_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj unselected 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_activated_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj activated 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_right_click_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right click 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()
            obj = evt.GetGLObject()

            obj.obj3d._context_menu_click_pos = evt.GetPosition()  # NOQA
            context_menu = obj.obj3d.get_context_menu()
            if context_menu is not None:
                # QMenu.exec() takes a global screen position.
                # evt.GetPosition() returns a Point in _canvas local coords
                # (the inner QOpenGLWidget, not the Canvas3D container).
                x, y, _ = evt.GetPosition().as_int
                gl_widget = self.editor3d.editor._canvas  # NOQA
                global_pos = gl_widget.mapToGlobal(
                    gl_widget.rect().topLeft().__class__(x, y)
                )
                context_menu.exec(global_pos)

    def _on_obj_right_dclick_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_click_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle click 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_dclick_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_click_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 click 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_dclick_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_click_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 click 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_dclick_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_drag_3d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj drag 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_key_down_3d(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            keycode = evt.GetKeyCode()
            if keycode == QtCore.Qt.Key.Key_Escape:
                mouse_event = evt.GetMouseEvent()

                if (
                    mouse_event.Aux1IsDown() or
                    mouse_event.Aux2IsDown() or
                    mouse_event.RightIsDown() or
                    mouse_event.MiddleIsDown() or
                    mouse_event.LeftIsDown()
                ):
                    self._obj_handler.ignore_next_input()
                else:
                    self._obj_handler.cancel()
                    self._obj_handler = None

                evt.StopPropagation()
                return

        evt.Skip()

    def _on_key_up_3d(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_mouse_move_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the mouse move 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            self._obj_handler.hover(evt.GetPosition())
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_capture_lost_3d(self, evt: _gl.GLCaptureLostEvent) -> None:
        """Handle the capture lost 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLCaptureLostEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the left down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            position = evt.GetPosition()
            self._obj_handler.capture_position(position)
            # grabMouse() replaces wx CaptureMouse() on the canvas widget
            self.editor3d.editor.grabMouse()
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_up_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the left up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            self._obj_handler.release_capture()

            if self._obj_handler.is_finalized:
                self._obj_handler = None

            evt.StopPropagation()
            return
        else:
            evt.Skip()

        mode = self.editor_toolbar.get_mode()

        if mode == _toolbar.ID_ZOOM_IN:
            evt.StopPropagation()
            self.editor3d.editor.Zoom(1.0)
        elif mode == _toolbar.ID_ZOOM_OUT:
            evt.StopPropagation()
            self.editor3d.editor.Zoom(-1.0)

    def _on_left_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the left dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the right down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_up_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the right up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            self._obj_handler.finalize_at_last_point()
            if self._obj_handler.is_finalized:
                self._obj_handler = None
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the right dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_up_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_up_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_up_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 up 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set3DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    # ------------------------------------------------------------------
    # 2D canvas GL event handlers
    # Mirror of the _3d handlers above; the 2D editor uses the same
    # EVT_GL_* signal protocol, routed through editor2d.connect().
    # ------------------------------------------------------------------

    def _on_obj_selected_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj selected 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_unselected_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj unselected 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_activated_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj activated 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_right_click_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right click 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()
            # obj = evt.GetGLObject()

            # context_menu = obj.obj2d.get_context_menu()
            # if context_menu is not None:
            #     x, y, _ = evt.GetPosition().as_int
            #     canvas_widget = self.editor2d.editor
            #     global_pos = canvas_widget.mapToGlobal(
            #         canvas_widget.rect().topLeft().__class__(x, y)
            #     )
            #     context_menu.exec(global_pos)

    def _on_obj_right_dclick_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_click_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle click 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_dclick_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_click_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 click 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_dclick_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_click_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 click 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_dclick_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_drag_2d(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj drag 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_key_down_2d(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            keycode = evt.GetKeyCode()
            if keycode == QtCore.Qt.Key.Key_Escape:
                mouse_event = evt.GetMouseEvent()

                if (
                    mouse_event is not None and (
                        mouse_event.Aux1IsDown() or
                        mouse_event.Aux2IsDown() or
                        mouse_event.RightIsDown() or
                        mouse_event.MiddleIsDown() or
                        mouse_event.LeftIsDown()
                    )
                ):
                    self._obj_handler.ignore_next_input()
                else:
                    self._obj_handler.cancel()
                    self._obj_handler = None

                evt.StopPropagation()
                return

        evt.Skip()

    def _on_key_up_2d(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_mouse_move_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the mouse move 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

        # mouse_pos = evt.GetPosition()

        # if self._add_handler is not None:
        #     self._add_handler.hover(mouse_pos)
        #     evt.StopPropagation()
        # else:
        #     evt.Skip()

    def _on_capture_lost_2d(self, evt: _gl.GLCaptureLostEvent) -> None:
        """Handle the capture lost 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLCaptureLostEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_down_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the left down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._obj_handler is not None:
            position = evt.GetPosition()
            self._obj_handler.capture_position(position)
            self.editor2d.editor.grabMouse()
            evt.StopPropagation()
        else:
            evt.Skip()
        #
        # mode = self.editor_toolbar.get_mode()
        #
        # if mode == _toolbar.ID_SELECT:
        #     return
        # elif mode == _toolbar.ID_CONNECTOR:
        #     evt.StopPropagation()
        #
        #     if (
        #         self._housing_handler is not None and
        #         not self._housing_handler.is_finalized
        #     ):
        #         raise RuntimeError('sanity check')
        #
        #     self.add_housing(position2d=evt.GetPosition())
        #
        # elif mode == _toolbar.ID_TERMINAL:
        #     evt.StopPropagation()
        #     self.add_terminal(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_WIRE:
        #     evt.StopPropagation()
        #     self.add_wire(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_WIRE_SERVICE_LOOP:
        #     evt.StopPropagation()
        #     self.add_wire_service_loop(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_SPLICE:
        #     evt.StopPropagation()
        #     self.add_splice(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_NOTE:
        #     evt.StopPropagation()
        #     self.add_note(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_CIRCLE:
        #     evt.StopPropagation()
        #     self.add_circle(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_SQUARE:
        #     evt.StopPropagation()
        #     self.add_square(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_TRANSITION:
        #     evt.StopPropagation()
        #     self.add_transition(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_SEAL:
        #     evt.StopPropagation()
        #     self.add_seal(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_BUNDLE_COVER:
        #     evt.StopPropagation()
        #     self.add_bundle(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_TPA_LOCK:
        #     evt.StopPropagation()
        #     self.add_tpa_lock(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_CPA_LOCK:
        #     evt.StopPropagation()
        #     self.add_cpa_lock(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_COVER:
        #     evt.StopPropagation()
        #     self.add_cover(position2d=evt.GetWorldPosition())
        # elif mode == _toolbar.ID_ZOOM_IN:
        #     evt.StopPropagation()
        #     self.editor2d.editor.camera.zoom_at_point(evt.GetPosition(), 1.0)
        # elif mode == _toolbar.ID_ZOOM_OUT:
        #     evt.StopPropagation()
        #     self.editor2d.editor.camera.zoom_at_point(evt.GetPosition(), -1.0)

        evt.Skip()

    def _on_left_up_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the left up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            self._obj_handler.release_capture()

            if self._obj_handler.is_finalized:
                self._obj_handler = None

            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_dclick_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the left dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_down_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the right down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_up_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the right up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_dclick_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the right dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_down_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_up_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_dclick_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the middle dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_down_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_up_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_dclick_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_down_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 down 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_up_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 up 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_dclick_2d(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 dclick 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    # ------------------------------------------------------------------
    # Peg board canvas GL event handlers
    # Mirror of the _2d handlers above; the peg board editor uses the same
    # EVT_GL_* signal protocol, routed through editor_pegboard.bind().
    # Phase 1 has no peg-board object-picking/dragging model yet, so these
    # only need to exist and behave generically (same _obj_handler gate as
    # every other editor) -- no new logic beyond that gate.
    # ------------------------------------------------------------------

    def _on_obj_selected_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj selected peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_unselected_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj unselected peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_activated_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj activated peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_right_click_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right click peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_right_dclick_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj right dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_click_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle click peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_middle_dclick_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj middle dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_click_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 click peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux1_dclick_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 1 dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_click_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 click peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_aux2_dclick_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj aux 2 dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_obj_drag_pegboard(self, evt: _gl.GLObjectEvent) -> None:
        """Handle the obj drag peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_key_down_pegboard(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            keycode = evt.GetKeyCode()
            if keycode == QtCore.Qt.Key.Key_Escape:
                mouse_event = evt.GetMouseEvent()

                if (
                    mouse_event is not None and (
                        mouse_event.Aux1IsDown() or
                        mouse_event.Aux2IsDown() or
                        mouse_event.RightIsDown() or
                        mouse_event.MiddleIsDown() or
                        mouse_event.LeftIsDown()
                    )
                ):
                    self._obj_handler.ignore_next_input()
                else:
                    self._obj_handler.cancel()
                    self._obj_handler = None

                evt.StopPropagation()
                return

        evt.Skip()

    def _on_key_up_pegboard(self, evt: _gl.GLKeyEvent) -> None:
        """Handle the key up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLKeyEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_mouse_move_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the mouse move peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            self._obj_handler.hover(evt.GetPosition())
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_capture_lost_pegboard(self, evt: _gl.GLCaptureLostEvent) -> None:
        """Handle the capture lost peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLCaptureLostEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_down_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the left down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            position = evt.GetPosition()
            self._obj_handler.capture_position(position)
            self.editor_pegboard.editor.grabMouse()
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_up_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the left up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            self._obj_handler.release_capture()

            if self._obj_handler.is_finalized:
                self._obj_handler = None

            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_dclick_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the left dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_down_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the right down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_up_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the right up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_dclick_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the right dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_down_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the middle down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_up_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the middle up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_middle_dclick_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the middle dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_down_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_up_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux1_dclick_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 1 dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_down_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 down peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_up_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 up peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_aux2_dclick_pegboard(self, evt: _gl.GLEvent) -> None:
        """Handle the aux 2 dclick peg board event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """

        self.Set2DCoordinates(evt)

        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    # QDockWidget.visibilityChanged / raise_() is the Qt equivalent for
    # focus-tracking; this stub preserves the hook for future use.
    # ------------------------------------------------------------------

    def _on_pane_activated(self, dock: QtWidgets.QDockWidget) -> None:
        """Handle the pane activated event.

        UNKNOWN details are inferred from the callable name and signature.

        :param dock: Value for ``dock``.
        :type dock: :class:`QDockWidget`
        """
        widget = dock.widget() if dock is not None else None

        if widget is self.editor2d.editor:
            pass
        elif widget is self.editor_pegboard.editor:
            pass
        elif widget is self.editor3d.editor:
            pass
        elif widget is self.editor_db.editor:
            pass
        elif widget is self.editor_obj.editor:
            pass
        elif widget is self.editor_assembly.editor:
            pass

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    def set_clone_obj(self, obj):
        """Set the clone obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._clone_obj = obj
        self.editor3d.set_clone_obj(obj)
        self.editor2d.set_clone_obj(obj)
        self.editor_pegboard.set_clone_obj(obj)

    def get_clone_obj(self):
        """Return the clone obj.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._clone_obj

    def set_obj_handler(self, handler):
        """Install an interactive placement handler.

        Cancels any handler that is currently active. Used by the editor
        context menus to start the same add-object flows as the toolbar.

        :param handler: Handler to install.
        :type handler: :class:`_handlers.HandlerBase`
        """
        if self._obj_handler is not None and not self._obj_handler.is_finalized:
            self._obj_handler.cancel()

        self._obj_handler = handler

    def add_object(self, obj):
        """Add an object.

        Fans out to all three editors -- peg board add is now genuinely
        incremental (``obj_pegboard`` is built once, at ``obj.__init__``
        time, and ``editor_pegboard.add_object`` just registers it), matching
        ``editor2d``/``editor3d`` exactly. This no longer triggers a full
        peg-board anchor-list rebuild on every call (that used to happen via
        an unconditional ``load_project()`` here -- removed).

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor2d.add_object(obj)
        self.editor3d.add_object(obj)
        self.editor_pegboard.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        See :meth:`add_object` -- same incremental-fan-out shape, same
        removed unconditional peg-board rebuild.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor2d.remove_object(obj)
        self.editor3d.remove_object(obj)
        self.editor_pegboard.remove_object(obj)

    def _set_selected(self, obj: "_objects.ObjectBase"):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_objects.ObjectBase`
        """
        self._selected_obj = obj
        self.editor3d.set_selected(obj)
        self.editor2d.set_selected(obj)
        self.editor_pegboard.set_selected(obj)
        _app.CallLater(self.editor_obj.set_selected, obj)

        if obj is None:
            return

        # Only consumed (and cleared) here, not on a deselect call (obj is
        # None, above) -- a click that swaps the selection deselects the
        # old object first, which would otherwise clear the flag before
        # the new object's own _set_selected call gets to read it.
        source_editor = self._selection_source_editor
        self._selection_source_editor = None

        # Bring the newly selected object into view in any editor where
        # it isn't already visible -- pan/zoom only when off-screen, so
        # clicking something already in view doesn't jerk the camera
        # around. 3D pans only (keeps current zoom, per user preference);
        # 2D has no equivalent "pan only" primitive yet so it reuses its
        # existing zoom_to_fit; the peg board's own center_on_object is
        # pan-only, matching 3D. Whichever editor the click that caused
        # this selection originated in is skipped entirely -- the object
        # is already exactly where the user put it on screen there, and
        # re-centering that editor just makes the click feel like it
        # teleported the view.
        if (
            source_editor != 'editor3d' and
            obj.obj3d is not None and not obj.is_in_3dview
        ):
            self.editor3d.camera.CenterOn(obj.obj3d.position)

        if (
            source_editor != 'editor2d' and
            obj.obj2d is not None and not obj.is_in_2dview
        ):
            # Editor2D (unlike Editor3D) has no .camera of its own --
            # go through .editor (the Canvas2D panel), which does.
            self.editor2d.editor.camera.zoom_to_fit([obj])

        if source_editor != 'editor_pegboard' and not obj.is_in_pegboardview:
            self.editor_pegboard.editor.center_on_object(obj)

    def set_selected(self, obj: "_objects.ObjectBase"):  # NOQA
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_objects.ObjectBase`
        """
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self) -> "_objects.ObjectBase":
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_objects.ObjectBase`
        """
        return self._selected_obj

    # ------------------------------------------------------------------
    # Add-object helpers
    # ------------------------------------------------------------------

    def _on_tool_mode_change(self, mode: int) -> None:
        if self._obj_handler is not None:
            if not self._obj_handler.is_finalized:
                self._obj_handler.cancel()

            self._obj_handler = None

        if mode == _toolbar.ID_SELECT:
            return
        elif mode == _toolbar.ID_CONNECTOR:
            self._obj_handler = _handlers.AddHousingHandler(self)
        elif mode == _toolbar.ID_TERMINAL:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddTerminalHandler(self, selected)
        elif mode == _toolbar.ID_WIRE:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddWireHandler(self, selected)
        elif mode == _toolbar.ID_WIRE_SERVICE_LOOP:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddWireServiceLoopHandler(self, selected)
        elif mode == _toolbar.ID_SPLICE:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddSpliceHandler(self, selected)
        elif mode == _toolbar.ID_NOTE:
            self._obj_handler = _handlers.AddNoteHandler(self)
        elif mode == _toolbar.ID_TRANSITION:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddTransitionHandler(self, selected)
        elif mode == _toolbar.ID_SEAL:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddSealHandler(self, selected)
        elif mode == _toolbar.ID_BUNDLE_COVER:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddBundleHandler(self, selected)
        elif mode == _toolbar.ID_TPA_LOCK:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddTPALockHandler(self, selected)
        elif mode == _toolbar.ID_CPA_LOCK:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddCPALockHandler(self, selected)
        elif mode == _toolbar.ID_COVER:
            if self.editor_toolbar.is_selected:
                selected = self.get_selected()
            else:
                selected = None

            self._obj_handler = _handlers.AddCoverHandler(self, selected)

    def unload(self):
        """Execute the unload operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def open_database(self, splash):
        """Open the database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..database.db_connectors import SQLConnector

        self.db_connector = SQLConnector(self)
        self.db_connector.connect(splash)

        from ..database import global_db
        from ..database import project_db

        self.global_db = global_db.GLBTables(splash, self)
        self.project_db = project_db.PJTTables(splash, self)
