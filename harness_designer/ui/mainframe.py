# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QLabel,
    QDockWidget,
    QWidget,
    QProgressBar,
    QDialog,
    QApplication
)

from PySide6.QtCore import Qt, QTimer, QByteArray
from PySide6.QtGui import QCursor

from .. import config as _config
from . import dialogs as _dialogs
from . import toolbar as _toolbar
from .. import gl as _gl
from .. import handlers as _handlers


if TYPE_CHECKING:
    from ..database.db_connectors import SQLConnector as _SQLConnector
    from ..database import global_db as _global_db
    from ..database import project_db as _project_db
    from ..objects import project as _project
    from .. import objects as _objects
    from .. import logger as _logger
    from ..geometry import point as _point


_mainframe: "MainFrame" = None

Config = _config.Config.mainframe

# ---------------------------------------------------------------------------
# EVT_GL_* constants are plain strings equal to the signal names,
# so pass them directly to editor.connect() — no mapping table needed.


class MainFrame(QMainWindow):
    """Represent a main frame in :mod:`harness_designer.ui.mainframe`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_connector: "_SQLConnector" = None

    global_db: "_global_db.GLBTables" = None
    project_db: "_project_db.PJTTables" = None
    project: "_project.Project" = None

    def __init__(self, splash, logger: "_logger.Log"):
        """Initialise the :class:`MainFrame` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        :param logger: Value for ``logger``.
        :type logger: :class:`_logger.Log`
        """
        QMainWindow.__init__(self)

        self.config = _config.Config

        splash.SetText('Startup logging ...')
        splash.flush()

        self.logger = logger
        self._clone_obj = None
        self._add_handler: _handlers.HandlerBase = None

        if not Config.size:
            screen = self.screen()
            geo = screen.availableGeometry()
            w = geo.width() * 2 // 3
            h = geo.height() * 2 // 3
            Config.size = (w, h)

        if not Config.position:
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

        self._bundle_handler: _handlers.AddBundleHandler = None
        self._bundle_layout_handler: _handlers.AddBundleLayoutHandler = None
        self._cover_handler: _handlers.AddCoverHandler = None
        self._cpa_lock_handler: _handlers.AddCPALockHandler = None
        self._housing_handler: _handlers.AddHousingHandler = None
        self._seal_handler: _handlers.AddSealHandler = None
        self._splice_handler: _handlers.AddSpliceHandler = None
        self._terminal_handler: _handlers.AddTerminalHandler = None
        self._tpa_lock_handler: _handlers.AddTPALockHandler = None
        self._transition_handler: _handlers.AddTransitionHandler = None
        self._wire_handler: _handlers.AddWireHandler = None
        self._wire_layout_handler: _handlers.AddWireLayoutHandler = None
        self._wire_service_loop_handler: _handlers.AddWireServiceLoopHandler = None

        # ------------------------------------------------------------------
        # Docking setup
        # Qt QMainWindow has built-in dock support. For full AUI-equivalent
        # floating/tabbing behaviour (Phase 17 note: PySide6-QtAds was
        # considered but QMainWindow dock widgets faithfully reproduce the
        # pane layout needed here; QtAds would be needed only if free-
        # floating drag-and-tab between arbitrary positions is required).
        # ------------------------------------------------------------------
        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        splash.SetText('Creating statusbar...')
        splash.flush()

        # ------------------------------------------------------------------
        # Status bar — 3 permanent QLabel widgets replace CreateStatusBar(3).
        # showMessage() is for transient notifications; coordinates use
        # permanent widgets so they are never overwritten by transient text.
        # ------------------------------------------------------------------
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        self.status_bar = status_bar

        fm = self.fontMetrics()
        coord_text = 'X: 0.000000'
        label_width = fm.horizontalAdvance(coord_text) + 8

        self._status_x = QLabel('X: 0.000000')
        self._status_x.setFixedWidth(label_width)
        self._status_y = QLabel('Y: 0.000000')
        self._status_y.setFixedWidth(label_width)
        self._status_z = QLabel('Z: 0.000000')
        self._status_z.setFixedWidth(label_width)

        status_bar.addPermanentWidget(self._status_x)
        status_bar.addPermanentWidget(self._status_y)
        status_bar.addPermanentWidget(self._status_z)

        self.progress_bar = QProgressBar()
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

        splash.SetText('Creating database editor...')
        splash.flush()

        from . import editor_db

        self.editor_db = editor_db.EditorDB(self)

        splash.SetText('Creating attribute editor...')
        splash.flush()

        from . import editor_ciruit

        self.editor_obj = editor_ciruit.EditorCircuit(self)

        splash.SetText('Creating circuit editor...')
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

        splash.SetText('Loading system menu...')
        splash.flush()

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
            if isinstance(state, str):
                # Guard: if an old str value slipped in, encode before use
                state = state.encode('latin-1')
            self.restoreState(QByteArray(state))

        if Config.position:
            QTimer.singleShot(0, lambda: self.move(*Config.position))
        else:
            QTimer.singleShot(0, self._center_on_screen)

        # ------------------------------------------------------------------
        # Connect GL canvas signals using editor3d.connect() shim.
        # editor3d.connect(signal_name, handler) calls
        # getattr(self.editor, signal_name).connect(handler) on the inner
        # QOpenGLWidget.  We derive the snake_case signal name from the
        # EVT_GL_* constants are plain strings equal to the signal names.
        # ------------------------------------------------------------------
        self._connect_editor3d_signals()
        self._connect_editor2d_signals()

        # ------------------------------------------------------------------
        # Idle processing — replaces wx.EVT_IDLE.
        # A zero-interval QTimer fires as fast as the event loop allows when
        # no other events are pending, giving the same semantics as wx idle.
        # The timer is started lazily (after initializeGL) to avoid GL calls
        # before the context is ready; we use a 0ms single-shot here which
        # chains itself only when there is remaining work, matching the
        # original event.RequestMore() pattern.
        # ------------------------------------------------------------------
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(0)
        self._idle_timer.timeout.connect(self._on_idle)
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

    def set_progress(self, value, label=None):
        """Set the progress.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        if label is not None:
            self.status_bar.showMessage(label)

        self.progress_bar.setValue(value)

        if value == self.progress_bar.maximum():
            self.status_bar.showMessage("Ready")
            self.progress_bar.hide()

    def start_progress(self, label, max_value):
        """Start the progress.

        UNKNOWN details are inferred from the callable name and signature.

        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param max_value: Value for ``max_value``.
        :type max_value: UNKNOWN
        """
        self.progress_bar.setRange(0, max_value)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage(label)
        self.progress_bar.show()

    def _make_dock(self, title: str, name: str, widget: QWidget,
                   area=None) -> QDockWidget:
        """Create and register a QDockWidget.

        Parameters
        ----------
        title:  Human-readable pane caption (shown in the title bar).
        name:   Stable object name used by saveState/restoreState.
                Must be unique across all dock widgets.
        widget: The content widget to embed in the dock.
        area:   Qt dock area constant (Qt.LeftDockWidgetArea etc.).
                Pass Qt.CentralWidget to set the widget as the central
                widget instead of docking it.  Defaults to
                Qt.RightDockWidgetArea when None.
        """
        if area is Qt.DockWidgetArea.AllDockWidgetAreas:
            # The 3D editor fills the central area — not a dockable pane
            self.setCentralWidget(widget)
            return None  # no QDockWidget to return

        dock = QDockWidget(title, self)
        dock.setObjectName(name)   # required for saveState/restoreState
        dock.setWindowTitle(title)
        dock.setWidget(widget)

        if area is None:
            area = Qt.DockWidgetArea.RightDockWidgetArea

        self.addDockWidget(area, dock)
        return dock

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
        pairs = [
            (_gl.EVT_GL_OBJECT_SELECTED,      self._on_obj_selected_3d),
            (_gl.EVT_GL_OBJECT_UNSELECTED,    self._on_obj_unselected_3d),
            (_gl.EVT_GL_OBJECT_ACTIVATED,     self._on_obj_activated_3d),
            (_gl.EVT_GL_OBJECT_RIGHT_CLICK,   self._on_obj_right_click_3d),
            (_gl.EVT_GL_OBJECT_RIGHT_DCLICK,  self._on_obj_right_dclick_3d),
            (_gl.EVT_GL_OBJECT_MIDDLE_CLICK,  self._on_obj_middle_click_3d),
            (_gl.EVT_GL_OBJECT_MIDDLE_DCLICK, self._on_obj_middle_dclick_3d),
            (_gl.EVT_GL_OBJECT_AUX1_CLICK,   self._on_obj_aux1_click_3d),
            (_gl.EVT_GL_OBJECT_AUX1_DCLICK,  self._on_obj_aux1_dclick_3d),
            (_gl.EVT_GL_OBJECT_AUX2_CLICK,   self._on_obj_aux2_click_3d),
            (_gl.EVT_GL_OBJECT_AUX2_DCLICK,  self._on_obj_aux2_dclick_3d),
            (_gl.EVT_GL_OBJECT_DRAG,         self._on_obj_drag_3d),
            (_gl.EVT_GL_KEY_DOWN,            self._on_key_down_3d),
            (_gl.EVT_GL_KEY_UP,              self._on_key_up_3d),
            (_gl.EVT_GL_MOUSE_MOVE,          self._on_mouse_move_3d),
            (_gl.EVT_GL_CAPTURE_LOST,        self._on_capture_lost_3d),
            (_gl.EVT_GL_LEFT_DOWN,           self._on_left_down_3d),
            (_gl.EVT_GL_LEFT_UP,             self._on_left_up_3d),
            (_gl.EVT_GL_LEFT_DCLICK,         self._on_left_dclick_3d),
            (_gl.EVT_GL_RIGHT_DOWN,          self._on_right_down_3d),
            (_gl.EVT_GL_RIGHT_UP,            self._on_right_up_3d),
            (_gl.EVT_GL_RIGHT_DCLICK,        self._on_right_dclick_3d),
            (_gl.EVT_GL_MIDDLE_DOWN,         self._on_middle_down_3d),
            (_gl.EVT_GL_MIDDLE_UP,           self._on_middle_up_3d),
            (_gl.EVT_GL_MIDDLE_DCLICK,       self._on_middle_dclick_3d),
            (_gl.EVT_GL_AUX1_DOWN,           self._on_aux1_down_3d),
            (_gl.EVT_GL_AUX1_UP,             self._on_aux1_up_3d),
            (_gl.EVT_GL_AUX1_DCLICK,         self._on_aux1_dclick_3d),
            (_gl.EVT_GL_AUX2_DOWN,           self._on_aux2_down_3d),
            (_gl.EVT_GL_AUX2_UP,             self._on_aux2_up_3d),
            (_gl.EVT_GL_AUX2_DCLICK,         self._on_aux2_dclick_3d),
        ]
        for evt_type, handler in pairs:
            self.editor3d.bind(evt_type, handler)

    def _connect_editor2d_signals(self):
        """Wire all EVT_GL_* signal sentinels to their mainframe 2D handlers."""
        pairs = [
            (_gl.EVT_GL_OBJECT_SELECTED,      self._on_obj_selected_2d),
            (_gl.EVT_GL_OBJECT_UNSELECTED,    self._on_obj_unselected_2d),
            (_gl.EVT_GL_OBJECT_ACTIVATED,     self._on_obj_activated_2d),
            (_gl.EVT_GL_OBJECT_RIGHT_CLICK,   self._on_obj_right_click_2d),
            (_gl.EVT_GL_OBJECT_RIGHT_DCLICK,  self._on_obj_right_dclick_2d),
            (_gl.EVT_GL_OBJECT_MIDDLE_CLICK,  self._on_obj_middle_click_2d),
            (_gl.EVT_GL_OBJECT_MIDDLE_DCLICK, self._on_obj_middle_dclick_2d),
            (_gl.EVT_GL_OBJECT_AUX1_CLICK,   self._on_obj_aux1_click_2d),
            (_gl.EVT_GL_OBJECT_AUX1_DCLICK,  self._on_obj_aux1_dclick_2d),
            (_gl.EVT_GL_OBJECT_AUX2_CLICK,   self._on_obj_aux2_click_2d),
            (_gl.EVT_GL_OBJECT_AUX2_DCLICK,  self._on_obj_aux2_dclick_2d),
            (_gl.EVT_GL_OBJECT_DRAG,         self._on_obj_drag_2d),
            (_gl.EVT_GL_KEY_DOWN,            self._on_key_down_2d),
            (_gl.EVT_GL_KEY_UP,              self._on_key_up_2d),
            (_gl.EVT_GL_MOUSE_MOVE,          self._on_mouse_move_2d),
            (_gl.EVT_GL_CAPTURE_LOST,        self._on_capture_lost_2d),
            (_gl.EVT_GL_LEFT_DOWN,           self._on_left_down_2d),
            (_gl.EVT_GL_LEFT_UP,             self._on_left_up_2d),
            (_gl.EVT_GL_LEFT_DCLICK,         self._on_left_dclick_2d),
            (_gl.EVT_GL_RIGHT_DOWN,          self._on_right_down_2d),
            (_gl.EVT_GL_RIGHT_UP,            self._on_right_up_2d),
            (_gl.EVT_GL_RIGHT_DCLICK,        self._on_right_dclick_2d),
            (_gl.EVT_GL_MIDDLE_DOWN,         self._on_middle_down_2d),
            (_gl.EVT_GL_MIDDLE_UP,           self._on_middle_up_2d),
            (_gl.EVT_GL_MIDDLE_DCLICK,       self._on_middle_dclick_2d),
            (_gl.EVT_GL_AUX1_DOWN,           self._on_aux1_down_2d),
            (_gl.EVT_GL_AUX1_UP,             self._on_aux1_up_2d),
            (_gl.EVT_GL_AUX1_DCLICK,         self._on_aux1_dclick_2d),
            (_gl.EVT_GL_AUX2_DOWN,           self._on_aux2_down_2d),
            (_gl.EVT_GL_AUX2_UP,             self._on_aux2_up_2d),
            (_gl.EVT_GL_AUX2_DCLICK,         self._on_aux2_dclick_2d),
        ]
        for evt_type, handler in pairs:
            self.editor2d.bind(evt_type, handler)

    # ------------------------------------------------------------------
    # QMainWindow event overrides (replace wx.EVT_* bindings)
    # ------------------------------------------------------------------

    def moveEvent(self, event):
        """Execute the move event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        QMainWindow.moveEvent(self, event)
        QTimer.singleShot(0, self._save_position)

    def resizeEvent(self, event):
        """Execute the resize event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        QMainWindow.resizeEvent(self, event)
        QTimer.singleShot(0, self._save_size)

    def closeEvent(self, event):
        """Execute the close event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        self._on_close()
        event.accept()

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

        if self.project is None:
            return

        if not self.project.cleanup.process_chunk():
            # No remaining work; pause idle processing.  The timer will
            # still fire on the next Qt event-loop pass and re-check, which
            # is effectively the same cost as the original wx idle pattern.
            pass

    # ------------------------------------------------------------------
    # Close / shutdown
    # ------------------------------------------------------------------

    def _on_close(self):
        """Handle the close event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.logger.info('Harness Designer shutting down')

        self.logger.info('Stopping Process Manager...')
        self.process_manager.stop()

        self.logger.info('Saving UI layout...')
        # saveState() returns QByteArray; store as bytes for Config
        Config.ui_perspective = bytes(self.saveState())

        self.logger.info('Closing 2D Editor....')
        self.editor2d.Destroy()

        self.logger.info('Closing 3D Editor....')
        self.editor3d.Destroy()

        self.logger.info('Closing Database Editor....')
        self.editor_db.Destroy()

        self.logger.info('Closing Object Editor....')
        self.editor_obj.Destroy()

        self.logger.info('Closing Assembly Editor....')
        self.editor_assembly.Destroy()

        self.logger.info('Closing Log Viewer....')
        self.log_viewer.Destroy()

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

    def Set2DCoordinates(self, x, y):
        """Execute the set 2dcoordinates operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        :param y: Y-coordinate value.
        :type y: UNKNOWN
        """
        self._status_x.setText(f'X: {round(float(x), 4)}')
        self._status_y.setText(f'Y: {round(float(y), 4)}')
        self._status_z.setText('')

    def Set3DCoordinates(self, x, y, z):
        """Execute the set 3dcoordinates operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param x: X-coordinate value.
        :type x: UNKNOWN
        :param y: Y-coordinate value.
        :type y: UNKNOWN
        :param z: Z-coordinate value.
        :type z: UNKNOWN
        """
        self._status_x.setText(f'X: {round(float(x), 4)}')
        self._status_y.setText(f'Y: {round(float(y), 4)}')
        self._status_z.setText(f'Z: {round(float(z), 4)}')

    def showEvent(self, event):
        """Execute the show event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        # super().showEvent(event)

        if self._splash is not None:
            self._splash.Destroy()
            self._splash = None

        from ..objects import project as _proj

        self.editor_db.load_db(self.global_db)

        self.project = _proj.Project.select_project(self)

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

            context_menu = obj.obj3d.get_context_menu()
            if context_menu is not None:
                # QMenu.exec() takes a global screen position.
                # evt.GetPosition() returns a Point in canvas-local coords;
                # map it to global via the canvas widget.
                x, y, _ = evt.GetPosition().as_int
                canvas_widget = self.editor3d.editor
                global_pos = canvas_widget.mapToGlobal(
                    canvas_widget.rect().topLeft().__class__(x, y)
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
            if keycode == Qt.Key.Key_Escape:
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
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

        mouse_pos = evt.GetPosition()

        if self._add_handler is not None:
            self._add_handler.hover(mouse_pos)
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
            self._obj_handler.veto_position()
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_left_down_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the left down 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
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
        if self._obj_handler is not None:
            self._obj_handler.release_capture()

            if self._obj_handler.is_finalized:
                self._obj_handler = None

            evt.StopPropagation()
            return
        else:
            evt.Skip()

        mode = self.editor_toolbar.get_mode()

        if mode == _toolbar.ID_SELECT:
            return
        elif mode == _toolbar.ID_CONNECTOR:
            evt.StopPropagation()
            self.add_housing(position3d=evt.GetPosition())


        elif mode == _toolbar.ID_TERMINAL:
            evt.StopPropagation()
            self.add_terminal(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_WIRE:
            evt.StopPropagation()
            self.add_wire(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_WIRE_SERVICE_LOOP:
            evt.StopPropagation()
            self.add_wire_service_loop(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SPLICE:
            evt.StopPropagation()
            self.add_splice(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_NOTE:
            evt.StopPropagation()
            self.add_note(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_CIRCLE:
            evt.StopPropagation()
            self.add_circle(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SQUARE:
            evt.StopPropagation()
            self.add_square(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_TRANSITION:
            evt.StopPropagation()
            self.add_transition(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SEAL:
            evt.StopPropagation()
            self.add_seal(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_BUNDLE_COVER:
            evt.StopPropagation()
            self.add_bundle(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_TPA_LOCK:
            evt.StopPropagation()
            self.add_tpa_lock(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_CPA_LOCK:
            evt.StopPropagation()
            self.add_cpa_lock(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_COVER:
            evt.StopPropagation()
            self.add_cover(position3d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_ZOOM_IN:
            evt.StopPropagation()
            self.editor3d.editor.Zoom(1.0)
        elif mode == _toolbar.ID_ZOOM_OUT:
            evt.StopPropagation()
            self.editor3d.editor.Zoom(-1.0)

        evt.Skip()

    def _on_left_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the left dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
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
        if self._obj_handler is not None:
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_right_dclick_3d(self, evt: _gl.GLEvent) -> None:
        """Handle the right dclick 3D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLEvent`
        """
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
            obj = evt.GetGLObject()

            context_menu = obj.obj2d.get_context_menu()
            if context_menu is not None:
                x, y, _ = evt.GetPosition().as_int
                canvas_widget = self.editor2d.editor
                global_pos = canvas_widget.mapToGlobal(
                    canvas_widget.rect().topLeft().__class__(x, y)
                )
                context_menu.exec(global_pos)

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
            if keycode == Qt.Key.Key_Escape:
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

        mouse_pos = evt.GetPosition()

        if self._add_handler is not None:
            self._add_handler.hover(mouse_pos)
            evt.StopPropagation()
        else:
            evt.Skip()

    def _on_capture_lost_2d(self, evt: _gl.GLCaptureLostEvent) -> None:
        """Handle the capture lost 2D event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLCaptureLostEvent`
        """
        if self._obj_handler is not None:
            self._obj_handler.veto_position()
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

        mode = self.editor_toolbar.get_mode()

        if mode == _toolbar.ID_SELECT:
            return
        elif mode == _toolbar.ID_CONNECTOR:
            evt.StopPropagation()

            if (
                self._housing_handler is not None and
                not self._housing_handler.is_finalized
            ):
                raise RuntimeError('sanity check')

            self.add_housing(position2d=evt.GetPosition())

        elif mode == _toolbar.ID_TERMINAL:
            evt.StopPropagation()
            self.add_terminal(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_WIRE:
            evt.StopPropagation()
            self.add_wire(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_WIRE_SERVICE_LOOP:
            evt.StopPropagation()
            self.add_wire_service_loop(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SPLICE:
            evt.StopPropagation()
            self.add_splice(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_NOTE:
            evt.StopPropagation()
            self.add_note(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_CIRCLE:
            evt.StopPropagation()
            self.add_circle(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SQUARE:
            evt.StopPropagation()
            self.add_square(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_TRANSITION:
            evt.StopPropagation()
            self.add_transition(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_SEAL:
            evt.StopPropagation()
            self.add_seal(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_BUNDLE_COVER:
            evt.StopPropagation()
            self.add_bundle(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_TPA_LOCK:
            evt.StopPropagation()
            self.add_tpa_lock(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_CPA_LOCK:
            evt.StopPropagation()
            self.add_cpa_lock(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_COVER:
            evt.StopPropagation()
            self.add_cover(position2d=evt.GetWorldPosition())
        elif mode == _toolbar.ID_ZOOM_IN:
            evt.StopPropagation()
            self.editor2d.editor.camera.zoom_at_point(evt.GetPosition(), 1.0)
        elif mode == _toolbar.ID_ZOOM_OUT:
            evt.StopPropagation()
            self.editor2d.editor.camera.zoom_at_point(evt.GetPosition(), -1.0)

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
    # QDockWidget.visibilityChanged / raise_() is the Qt equivalent for
    # focus-tracking; this stub preserves the hook for future use.
    # ------------------------------------------------------------------

    def _on_pane_activated(self, dock: QDockWidget) -> None:
        """Handle the pane activated event.

        UNKNOWN details are inferred from the callable name and signature.

        :param dock: Value for ``dock``.
        :type dock: :class:`QDockWidget`
        """
        widget = dock.widget() if dock is not None else None

        if widget is self.editor2d.editor:
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

    def get_clone_obj(self):
        """Return the clone obj.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._clone_obj

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor2d.add_object(obj)
        self.editor3d.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor2d.remove_object(obj)
        self.editor3d.remove_object(obj)

    def _set_selected(self, obj: "_objects.ObjectBase"):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_objects.ObjectBase`
        """
        self._selected_obj = obj
        self.editor3d.set_selected(obj)
        self.editor2d.set_selected(obj)
        self.editor_obj.set_selected(obj)

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

    def add_housing(self, position2d: "_point.Point" = None,
                    position3d: "_point.Point" = None) -> None:
        """Add a housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        """

        if position3d is not None:
            housing_handler = _handlers.AddHousingHandler(self)
            housing_handler.capture_position(position3d)
            housing_handler.release_capture()

    def add_terminal(self, position2d: "_point.Point" = None,
                     position3d: "_point.Point" = None, part_id: int = None) -> None:
        """Add a terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.terminals.GetSelection()

        if part_id is None:
            return

        self.project.add_terminal(part_id, position2d, position3d)

    def add_wire(self, position2d: "_point.Point" = None,
                 position3d: "_point.Point" = None, part_id: int = None) -> None:
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.wires.GetSelection()

        if part_id is None:
            return

        self.project.add_wire(part_id, position2d, position3d)

    def add_wire_service_loop(self, position3d: "_point.Point",
                              part_id: int = None) -> None:
        """Add a wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.wires.GetSelection()

        if part_id is None:
            return

        self.project.add_wire_service_loop(part_id, position3d)

    def add_wire_marker(self, position2d: "_point.Point" = None,
                        position3d: "_point.Point" = None, part_id: int = None) -> None:
        """Add a wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.wire_markers.GetSelection()

        if part_id is None:
            return

        self.project.add_wire_marker(part_id, position2d, position3d)

    def add_splice(self, position2d: "_point.Point" = None,
                   position3d: "_point.Point" = None, part_id: int = None) -> None:
        """Add a splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.splices.GetSelection()

        if part_id is None:
            return

        self.project.add_splice(part_id, position2d, position3d)

    def add_note(self, position2d: "_point.Point" = None,
                 position3d: "_point.Point" = None, note: str = '') -> None:
        """Add a note.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d: 2D position value.
        :type position2d: :class:`_point.Point`
        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param note: Value for ``note``.
        :type note: str
        """

        self.project.add_note(note, position2d, position3d)

    def add_transition(self, position3d: "_point.Point",
                       part_id: int = None) -> None:
        """Add a transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.transitions.GetSelection()

        if part_id is None:
            return

        self.project.add_transition(part_id, position3d)

    def add_seal(self, position3d: "_point.Point",
                 part_id: int = None) -> None:
        """Add a seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.seals.GetSelection()

        if part_id is None:
            return

        self.project.add_seal(part_id, position3d)

    def add_bundle(self, position3d: "_point.Point",
                   part_id: int = None) -> None:
        """Add a bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.bundle_covers.GetSelection()

        if part_id is None:
            return

        self.project.add_bundle(part_id, position3d)

    def add_tpa_lock(self, position3d: "_point.Point",
                     part_id: int = None) -> None:
        """Add a TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.tpa_locks.GetSelection()

        if part_id is None:
            return

        self.project.add_tpa_lock(part_id, position3d)

    def add_cpa_lock(self, position3d: "_point.Point",
                     part_id: int = None) -> None:
        """Add a CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.cpa_locks.GetSelection()

        if part_id is None:
            return

        self.project.add_cpa_lock(part_id, position3d)

    def add_boot(self, position3d: "_point.Point",
                 part_id: int = None) -> None:
        """Add a boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.boots.GetSelection()

        if part_id is None:
            return

        self.project.add_boot(part_id, position3d)

    def add_cover(self, position3d: "_point.Point",
                  part_id: int = None) -> None:
        """Add a cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d: 3D position value.
        :type position3d: :class:`_point.Point`
        :param part_id: Identifier for the part.
        :type part_id: int
        """

        if part_id is None:
            part_id = self.editor_db.covers.GetSelection()

        if part_id is None:
            return

        self.project.add_cover(part_id, position3d)

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
        self.db_connector.connect()

        from ..database import global_db
        from ..database import project_db

        self.global_db = global_db.GLBTables(splash, self)
        self.project_db = project_db.PJTTables(splash, self)
