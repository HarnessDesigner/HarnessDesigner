# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import build123d
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QToolBar

from ... import gl as _gl
from ... import image as _image
from ...objects import note as _note


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


# ---------------------------------------------------------------------------
# Tool IDs — plain ints replace wx.NewIdRef().  Unique sentinel values used
# throughout mainframe.py to identify the active editor mode.
# ---------------------------------------------------------------------------

_id_counter = iter(range(1, 1000))


def _new_id() -> int:
    return next(_id_counter)


ID_SELECT = _new_id()
ID_CONNECTOR = _new_id()
ID_TERMINAL = _new_id()
ID_WIRE = _new_id()
ID_SPLICE = _new_id()
ID_NOTE = _new_id()
ID_WIRE_SERVICE_LOOP = _new_id()
ID_COVER = _new_id()

ID_ZOOM_IN = _new_id()
ID_ZOOM_OUT = _new_id()

ID_CIRCLE = _new_id()
ID_SQUARE = _new_id()

ID_TRANSITION = _new_id()
ID_SEAL = _new_id()
ID_BUNDLE_COVER = _new_id()
ID_TPA_LOCK = _new_id()
ID_CPA_LOCK = _new_id()


def _make_icon(img_attr, size: int = 32) -> QIcon:
    """Convert a harness_designer image object to a QIcon."""
    return QIcon(img_attr.resize(size, size).pixmap)


# ---------------------------------------------------------------------------
# EditorToolbar
# ---------------------------------------------------------------------------

class EditorToolbar:
    """
    Object-placement mode toolbar.

    wx: subclassed aui.AuiPaneInfo AND held an aui.AuiToolBar internally.
    Qt: is a thin wrapper around a QToolBar added to the QMainWindow.
    The toolbar object itself is self.toolbar; callers that stored a reference
    to the whole class continue to work because all public methods delegate.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe
        self._mode: int | None = None

        tb = QToolBar('Editor', mainframe)
        tb.setObjectName('editor_toolbar')
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(__import__('PySide6.QtCore', fromlist=['QSize']).QSize(32, 32))
        self.toolbar = tb

        # Radio group for mode buttons
        self._mode_group = QActionGroup(tb)
        self._mode_group.setExclusive(True)

        def _radio(id_: int, label: str, icon: QIcon) -> QAction:
            act_ = QAction(icon, label, tb)
            act_.setCheckable(True)
            act_.setToolTip(label)
            act_.setData(id_)
            act_.triggered.connect(lambda checked=False, i=id_: self._on_mode(i))
            self._mode_group.addAction(act_)
            tb.addAction(act_)
            return act_

        icons = _image.icons
        self._select = _radio(ID_SELECT, 'Select', _make_icon(icons.select_object))
        self._housing = _radio(ID_CONNECTOR, 'Add Housing', _make_icon(icons.connector))
        self._terminal = _radio(ID_TERMINAL, 'Add Terminal', _make_icon(icons.terminal))
        self._wire = _radio(ID_WIRE, 'Add Wire', _make_icon(icons.wire))
        self._splice = _radio(ID_SPLICE, 'Add Splice', _make_icon(icons.splice))
        self._note = _radio(ID_NOTE, 'Add Note', _make_icon(icons.notes))
        self._zoom_in = _radio(ID_ZOOM_IN, 'Zoom +', _make_icon(icons.zoom_in))
        self._zoom_out = _radio(ID_ZOOM_OUT, 'Zoom -', _make_icon(icons.zoom_out))
        self._draw_circle = _radio(ID_CIRCLE, 'Draw Circle', _make_icon(icons.circle))
        self._draw_square = _radio(ID_SQUARE, 'Draw Square', _make_icon(icons.square))
        self._transition = _radio(ID_TRANSITION, 'Add Transition', _make_icon(icons.transition))
        self._seal = _radio(ID_SEAL, 'Add Seal', _make_icon(icons.seal))
        self._bundle = _radio(ID_BUNDLE_COVER, 'Add Bundle', _make_icon(icons.bundle_cover))
        self._tpa_lock = _radio(ID_TPA_LOCK, 'Add TPA Lock', _make_icon(icons.tpa_lock))
        self._cpa_lock = _radio(ID_CPA_LOCK, 'Add CPA Lock', _make_icon(icons.cpa_lock))

        # Initially disabled (context-dependent) — mirrors AUI_BUTTON_STATE_DISABLED
        for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                    self._transition, self._draw_square, self._draw_circle,
                    self._splice, self._terminal):
            act.setEnabled(False)

        self._select.setChecked(True)
        self._mode = ID_SELECT

        mainframe.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        # GL object selection drives button enable/disable
        mainframe.editor3d.gl_object_selected.connect(self._on_obj_selected)
        mainframe.editor3d.gl_object_unselected.connect(self._on_obj_unselected)

    # --- mode ---

    def get_mode(self) -> int | None:
        return self._mode

    def _on_mode(self, id_: int):
        self._mode = id_

    # --- context-sensitive enable/disable ---

    def _on_obj_selected(self, evt: "_gl.GLObjectEvent"):
        from ...objects import housing as _housing
        from ...objects import wire as _wire
        from ...objects import terminal as _terminal
        from ...objects import bundle as _bundle

        obj = evt.GetGLObject()

        # Reset everything to disabled first, then selectively enable.
        for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                    self._transition, self._draw_square, self._draw_circle,
                    self._splice, self._terminal):
            act.setEnabled(False)

        if isinstance(obj, _housing.Housing):
            for act in (self._cpa_lock, self._tpa_lock, self._seal, self._terminal):
                act.setEnabled(True)

        elif isinstance(obj, _wire.Wire):
            for act in (self._bundle, self._splice):
                act.setEnabled(True)

        elif isinstance(obj, _bundle.Bundle):
            self._transition.setEnabled(True)

        elif isinstance(obj, _terminal.Terminal):
            self._seal.setEnabled(True)

    def _on_obj_unselected(self, _: "_gl.GLObjectEvent"):
        for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                    self._transition, self._draw_square, self._draw_circle,
                    self._splice, self._terminal):

            act.setEnabled(False)

    # --- passthrough helpers used by mainframe ---

    def Refresh(self, *_, **__):
        self.toolbar.repaint()

    def Destroy(self):
        self.toolbar.deleteLater()


# ---------------------------------------------------------------------------
# NoteToolbar
# ---------------------------------------------------------------------------

class NoteToolbar:
    """Text-alignment toolbar, visible when a Note object is selected."""

    ID_ALIGN_HORIZ_CENTER = _new_id()
    ID_ALIGN_HORIZ_LEFT = _new_id()
    ID_ALIGN_HORIZ_RIGHT = _new_id()

    ID_ALIGN_VERT_CENTER = _new_id()
    ID_ALIGN_VERT_TOP = _new_id()
    ID_ALIGN_VERT_BOTTOM = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe

        tb = QToolBar('Note', mainframe)
        tb.setObjectName('note_toolbar')
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(QSize(32, 32))
        self.toolbar = tb

        group = QActionGroup(tb)
        group.setExclusive(True)

        def _radio(id_: int, label: str, icon: QIcon) -> QAction:
            act = QAction(icon, label, tb)
            act.setCheckable(True)
            act.setEnabled(False)
            act.setToolTip(label)
            act.setData(id_)
            group.addAction(act)
            tb.addAction(act)
            return act

        icons = _image.icons
        self.align_left = _radio(self.ID_ALIGN_HORIZ_LEFT, 'Align Left',
                                 _make_icon(icons.align_left_edge))
        self.align_center = _radio(self.ID_ALIGN_HORIZ_CENTER, 'Align Center',
                                   _make_icon(icons.align_horizontal_center))
        self.align_right = _radio(self.ID_ALIGN_HORIZ_RIGHT, 'Align Right',
                                  _make_icon(icons.align_right_edge))

        mainframe.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

        mainframe.editor2d.gl_object_selected.connect(self.on_obj2d_selected)
        mainframe.editor2d.gl_object_unselected.connect(self.on_obj2d_unselected)
        mainframe.editor3d.gl_object_selected.connect(self.on_obj3d_selected)
        mainframe.editor3d.gl_object_unselected.connect(self.on_obj3d_unselected)

        # "Pane activated" → QDockWidget.visibilityChanged on the editor docks.
        # We connect to each dock and check which editor is now on top.
        mainframe.editor2d.visibilityChanged.connect(
            lambda visible: self._on_editor_visibility('editor2d', visible))
        mainframe.editor3d.visibilityChanged.connect(
            lambda visible: self._on_editor_visibility('editor3d', visible))

    def _on_editor_visibility(self, editor_name: str, visible: bool):
        if not visible:
            return
        obj = self.mainframe.get_selected()
        if not isinstance(obj, _note.Note):
            self.set_buttons(-1)
            return
        if editor_name == 'editor2d':
            self.set_buttons(obj.db_obj.h_align2d)
        elif editor_name == 'editor3d':
            self.set_buttons(obj.db_obj.h_align3d)
        else:
            self.set_buttons(-1)

    def set_buttons(self, align):
        if align == -1:
            for act in (self.align_left, self.align_center, self.align_right):
                act.setEnabled(False)
                act.setChecked(False)
        else:
            for act in (self.align_left, self.align_center, self.align_right):
                act.setEnabled(True)

            if align == build123d.TextAlign.LEFT:
                self.align_left.setChecked(True)
            elif align == build123d.TextAlign.CENTER:
                self.align_center.setChecked(True)
            elif align == build123d.TextAlign.RIGHT:
                self.align_right.setChecked(True)
            else:
                raise RuntimeError('sanity check')

    def on_obj2d_selected(self, evt: "_gl.GLObjectEvent"):
        obj = evt.GetGLObject()
        self.set_buttons(obj.db_obj.h_align2d if isinstance(obj, _note.Note) else -1)

    def on_obj2d_unselected(self, _: "_gl.GLObjectEvent"):
        self.set_buttons(-1)

    def on_obj3d_selected(self, evt: "_gl.GLObjectEvent"):
        obj = evt.GetGLObject()
        self.set_buttons(obj.db_obj.h_align3d if isinstance(obj, _note.Note) else -1)

    def on_obj3d_unselected(self, _: "_gl.GLObjectEvent"):
        self.set_buttons(-1)

    def Refresh(self, *_, **__):
        self.toolbar.repaint()

    def Destroy(self):
        self.toolbar.deleteLater()


# ---------------------------------------------------------------------------
# EditorObjectToolbar
# ---------------------------------------------------------------------------

class EditorObjectToolbar:
    """Transform-mode toolbar (rotate / scale / move on each axis)."""

    ID_ROTATE_X = _new_id()
    ID_ROTATE_Y = _new_id()
    ID_ROTATE_Z = _new_id()

    ID_SCALE_X = _new_id()
    ID_SCALE_Y = _new_id()
    ID_SCALE_Z = _new_id()

    ID_MOVE_X = _new_id()
    ID_MOVE_Y = _new_id()
    ID_MOVE_Z = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe

        tb = QToolBar('Object', mainframe)
        tb.setObjectName('object_toolbar')
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(__import__('PySide6.QtCore', fromlist=['QSize']).QSize(32, 32))
        self.toolbar = tb

        group = QActionGroup(tb)
        group.setExclusive(True)

        def _radio(id_: int, label: str, icon: QIcon) -> QAction:
            act = QAction(icon, label, tb)
            act.setCheckable(True)
            act.setToolTip(label)
            act.setData(id_)
            act.triggered.connect(lambda checked=False, i=id_: self.on_tools(i))
            group.addAction(act)
            tb.addAction(act)
            return act

        icons = _image.icons
        _radio(self.ID_ROTATE_X, 'Rotate on X Axis', _make_icon(icons.rotate_x))
        _radio(self.ID_ROTATE_Y, 'Rotate on Y Axis', _make_icon(icons.rotate_y))
        _radio(self.ID_ROTATE_Z, 'Rotate on Z Axis', _make_icon(icons.rotate_z))
        _radio(self.ID_SCALE_X, 'Scale on X Axis', _make_icon(icons.scale_x))
        _radio(self.ID_SCALE_Y, 'Scale on Y Axis', _make_icon(icons.scale_y))
        _radio(self.ID_SCALE_Z, 'Scale on Z Axis', _make_icon(icons.scale_z))
        _radio(self.ID_MOVE_X, 'Move on X Axis', _make_icon(icons.move_x))
        _radio(self.ID_MOVE_Y, 'Move on Y Axis', _make_icon(icons.move_y))
        _radio(self.ID_MOVE_Z, 'Move on Z Axis', _make_icon(icons.move_z))

        mainframe.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def on_tools(self, id_: int):
        pass  # future: notify handlers of transform mode change

    def Refresh(self, *_, **__):
        self.toolbar.repaint()

    def Destroy(self):
        self.toolbar.deleteLater()


# ---------------------------------------------------------------------------
# Setting3DToolbar
# ---------------------------------------------------------------------------

class Setting3DToolbar:
    """Toggle toolbar for 3D viewport display settings."""

    ID_SHOW_SPOTLIGHT = _new_id()
    ID_SHOW_NORMALS = _new_id()
    ID_SHOW_WIREFRAME = _new_id()
    ID_SHOW_VERTICES = _new_id()
    ID_SHOW_REFLECTIONS = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe

        tb = QToolBar('3D Settings', mainframe)
        tb.setObjectName('settings3d_toolbar')
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(__import__('PySide6.QtCore', fromlist=['QSize']).QSize(32, 32))
        self.toolbar = tb

        def _toggle(id_: int, label: str, icon: QIcon, slot) -> QAction:
            act = QAction(icon, label, tb)
            act.setCheckable(True)
            act.setToolTip(label)
            act.setData(id_)
            act.triggered.connect(slot)
            tb.addAction(act)
            return act

        icons = _image.icons
        self._wireframe = _toggle(self.ID_SHOW_WIREFRAME, 'Show Wireframe',
                                  _make_icon(icons.show_wireframe), self.on_show_wireframe)
        self._reflections = _toggle(self.ID_SHOW_REFLECTIONS, 'Show Reflections',
                                    _make_icon(icons.reflections), self.on_show_reflections)
        self._spotlight = _toggle(self.ID_SHOW_SPOTLIGHT, 'Show Spotlight',
                                  _make_icon(icons.spot_light), self.on_show_spotlight)
        self._normals = _toggle(self.ID_SHOW_NORMALS, 'Show Normals',
                                _make_icon(icons.normals), self.on_show_normals)
        self._vertices = _toggle(self.ID_SHOW_VERTICES, 'Show Vertices',
                                 _make_icon(icons.vertices), self.on_show_vertices)

        mainframe.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def on_show_wireframe(self, checked: bool):
        pass

    def on_show_reflections(self, checked: bool):
        pass

    def on_show_spotlight(self, checked: bool):
        pass

    def on_show_normals(self, checked: bool):
        pass

    def on_show_vertices(self, checked: bool):
        pass

    def Refresh(self, *_, **__):
        self.toolbar.repaint()

    def Destroy(self):
        self.toolbar.deleteLater()


# ---------------------------------------------------------------------------
# GeneralToolbar
# ---------------------------------------------------------------------------

class GeneralToolbar:
    """Application-level toolbar (browser, settings, tools, connect, BOM)."""

    ID_BROWSER = _new_id()
    ID_SETTINGS = _new_id()
    ID_TOOLS = _new_id()
    ID_CONNECT = _new_id()
    ID_BOM = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.mainframe = mainframe

        tb = QToolBar('General', mainframe)
        tb.setObjectName('general_toolbar')
        tb.setMovable(True)
        tb.setFloatable(True)
        tb.setIconSize(__import__('PySide6.QtCore', fromlist=['QSize']).QSize(32, 32))
        self.toolbar = tb

        def _push(id_: int, label: str, icon: QIcon, slot) -> QAction:
            act = QAction(icon, label, tb)
            act.setToolTip(label)
            act.setData(id_)
            act.triggered.connect(slot)
            tb.addAction(act)
            return act

        icons = _image.icons
        _push(self.ID_BROWSER, 'Internet', _make_icon(icons.internet), self.on_browser)
        _push(self.ID_SETTINGS, 'Settings', _make_icon(icons.settings), self.on_settings)
        _push(self.ID_TOOLS, 'Tools', _make_icon(icons.tool), self.on_tools)
        _push(self.ID_CONNECT, 'Connect Database', _make_icon(icons.connect), self.on_database)
        _push(self.ID_BOM, 'BOM', _make_icon(icons.bom), self.on_bom)

        mainframe.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    def on_browser(self, checked: bool = False):
        pass

    def on_settings(self, checked: bool = False):
        pass

    def on_tools(self, checked: bool = False):
        pass

    def on_database(self, checked: bool = False):
        pass

    def on_bom(self, checked: bool = False):
        pass

    def Refresh(self, *_, **__):
        self.toolbar.repaint()

    def Destroy(self):
        self.toolbar.deleteLater()
