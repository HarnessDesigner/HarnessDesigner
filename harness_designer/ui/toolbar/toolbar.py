# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import build123d
from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ... import gl as _gl
from ... import image as _image
from ...objects import note as _note
from . import float_spin_button as _fsb
from . import snap_angle_button as _sab
from . import pegboard_snap_button as _psb
from . import pegboard_drag_mode_button as _pdmb
from ... import config as _config
from ...objects import project_model as _project_model
from ...objects import bundle as _bundle
from ...objects import wire as _wire
from ...objects import cavity as _cavity
from ...objects import wire_marker as _wire_marker
from ...objects import housing as _housing
from ...objects import terminal as _terminal
from ...objects import transition as _transition
from ...objects import splice as _splice
from ...objects import wire_layout as _wire_layout
from ...objects import bundle_layout as _bundle_layout


if TYPE_CHECKING:
    from .. import mainframe as _mainframe
    from ...geometry import point as _point
    from ...geometry import angle as _angle

# ---------------------------------------------------------------------------
# Tool IDs — plain ints replace wx.NewIdRef().  Unique sentinel values used
# throughout mainframe.py to identify the active editor mode.
# ---------------------------------------------------------------------------

_id_counter = iter(range(1, 1000))


def _new_id() -> int:
    """Execute the new ID operation.

    UNKNOWN details are inferred from the callable name and signature.

    :returns: Return value. UNKNOWN details.
    :rtype: int
    """
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


def _make_icon(img_attr, size: int = 32) -> QtGui.QIcon:
    """Convert a harness_designer image object to a QIcon."""
    return QtGui.QIcon(img_attr.resize(size, size).pixmap)


# ---------------------------------------------------------------------------
# EditorToolbar
# ---------------------------------------------------------------------------

class EditorToolbar(QtWidgets.QToolBar):
    """
    Object-placement mode toolbar.

    wx: subclassed aui.AuiPaneInfo AND held an aui.AuiToolBar internally.
    Qt: is a thin wrapper around a QToolBar added to the QMainWindow.
    The toolbar object itself is self.toolbar; callers that stored a reference
    to the whole class continue to work because all public methods delegate.
    """

    modeChanged: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorToolbar` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self.mainframe = mainframe
        self._mode: int | None = None

        super().__init__('Editor', mainframe)
        self.setObjectName('editor_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        # Radio group for mode buttons
        self._mode_group = QtGui.QActionGroup(self)
        self._mode_group.setExclusive(True)

        def _radio(id_: int, label: str, icon: QtGui.QIcon) -> QtGui.QAction:
            """Execute the radio operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param id_: Identifier for the ID.
            :type id_: int
            :param label: Value for ``label``.
            :type label: str
            :param icon: Value for ``icon``.
            :type icon: :class:`QIcon`
            :returns: Return value. UNKNOWN details.
            :rtype: :class:`QAction`
            """
            act_ = QtGui.QAction(icon, label, self)
            act_.setCheckable(True)
            act_.setToolTip(label)
            act_.setData(id_)
            act_.triggered.connect(lambda checked=False, i=id_: self._on_mode(i))
            self._mode_group.addAction(act_)
            self.addAction(act_)
            return act_

        icons = _image.icons
        self._select = _radio(ID_SELECT, 'Select', _make_icon(icons.select_object))
        self._housing = _radio(ID_CONNECTOR, 'Add Housing', _make_icon(icons.connector))
        self._terminal = _radio(ID_TERMINAL, 'Add Terminal', _make_icon(icons.terminal))
        self._wire = _radio(ID_WIRE, 'Add Wire', _make_icon(icons.wire))
        self._splice = _radio(ID_SPLICE, 'Add Splice', _make_icon(icons.splice))
        self._note = _radio(ID_NOTE, 'Add Note', _make_icon(icons.notes))
        self._transition = _radio(ID_TRANSITION, 'Add Transition', _make_icon(icons.transition))
        self._seal = _radio(ID_SEAL, 'Add Seal', _make_icon(icons.seal))
        self._bundle = _radio(ID_BUNDLE_COVER, 'Add Bundle', _make_icon(icons.bundle_cover))
        self._tpa_lock = _radio(ID_TPA_LOCK, 'Add TPA Lock', _make_icon(icons.tpa_lock))
        self._cpa_lock = _radio(ID_CPA_LOCK, 'Add CPA Lock', _make_icon(icons.cpa_lock))
        self._cover = _radio(ID_COVER, 'Add Cover', _make_icon(icons.cover))

        # Initially disabled (context-dependent) — mirrors AUI_BUTTON_STATE_DISABLED
        self._select.setChecked(True)
        self._mode = ID_SELECT
        self._selected = None

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

        # GL object selection drives button enable/disable
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_SELECTED, self._on_obj_selected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected)

    def get_mode(self) -> int | None:
        """Return the mode.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int | None
        """
        return self._mode

    def _on_mode(self, id_: int):
        """Handle the mode event.

        UNKNOWN details are inferred from the callable name and signature.

        :param id_: Identifier for the ID.
        :type id_: int
        """
        self._mode = id_

        self.modeChanged.emit(id_)

    def _on_obj_selected(self, evt: "_gl.GLObjectEvent"):
        """Handle the obj selected event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        obj = evt.GetGLObject()
        if isinstance(obj, _project_model.ProjectModel):
            evt.StopPropagation()
            return

        # Reset everything to disabled first, then selectively enable.
        for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                    self._transition, self._splice, self._terminal, self._cover,
                    self._wire):
            act.setEnabled(False)

        if isinstance(obj, _housing.Housing):
            for act in (self._cpa_lock, self._tpa_lock, self._seal, self._terminal, self._cover):
                act.setEnabled(True)
                self._selected = obj

        elif isinstance(obj, _wire.Wire):
            for act in (self._bundle, self._splice, self._transition, self._wire):
                act.setEnabled(True)
                self._selected = obj

        elif isinstance(obj, _bundle.Bundle):
            for act in (self._bundle, self._transition):
                act.setEnabled(True)
                self._selected = obj

        elif isinstance(obj, _terminal.Terminal):
            for act in (self._seal, self._wire):
                act.setEnabled(True)
                self._selected = obj

        elif isinstance(obj, _transition.Transition):
            for act in (self._bundle,):
                act.setEnabled(True)
                self._selected = obj

        elif isinstance(obj, _splice.Splice):
            for act in (self._wire,):
                act.setEnabled(True)
                self._selected = obj
        else:
            for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                        self._transition, self._splice, self._terminal, self._cover,
                        self._wire):

                act.setEnabled(True)

            self._selected = None

    def _on_obj_unselected(self, _: "_gl.GLObjectEvent"):
        """Handle the obj unselected event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: :class:`_gl.GLObjectEvent`
        """
        for act in (self._cpa_lock, self._tpa_lock, self._bundle, self._seal,
                    self._transition, self._splice, self._terminal, self._cover,
                    self._wire):

            act.setEnabled(True)

        self._selected = None

    @property
    def is_selected(self):
        return self._selected is not None

    # --- passthrough helpers used by mainframe ---

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.repaint()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.deleteLater()


# ---------------------------------------------------------------------------
# NoteToolbar
# ---------------------------------------------------------------------------

class NoteToolbar(QtWidgets.QToolBar):
    """
    Text-alignment toolbar, visible when a Note object is selected.
    """

    ID_ALIGN_HORIZ_CENTER = _new_id()
    ID_ALIGN_HORIZ_LEFT = _new_id()
    ID_ALIGN_HORIZ_RIGHT = _new_id()

    ID_ALIGN_VERT_CENTER = _new_id()
    ID_ALIGN_VERT_TOP = _new_id()
    ID_ALIGN_VERT_BOTTOM = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`NoteToolbar` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self.mainframe = mainframe

        super().__init__('Note', mainframe)
        self.setObjectName('note_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        self._obj = None

        icons = _image.icons

        icn = self._get_icon(False, icons.align_left_edge)

        self.align_left = QtGui.QAction(icn, 'Align Left', self)
        self.align_left.setCheckable(False)
        self.align_left.triggered.connect(self.on_align_left)
        self.align_left.setEnabled(False)
        self.addAction(self.align_left)

        icn = self._get_icon(False, icons.align_horizontal_center)

        self.align_center = QtGui.QAction(icn, 'Align Center', self)
        self.align_center.setCheckable(False)
        self.align_center.triggered.connect(self.on_align_center)
        self.align_center.setEnabled(False)
        self.addAction(self.align_center)

        icn = self._get_icon(False, icons.align_right_edge)

        self.align_right = QtGui.QAction(icn, 'Align Right', self)
        self.align_right.setCheckable(False)
        self.align_right.triggered.connect(self.on_align_right)
        self.align_right.setEnabled(False)
        self.addAction(self.align_right)

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

        mainframe.editor2d.bind(_gl.EVT_GL_OBJECT_SELECTED, self.on_obj2d_selected)
        mainframe.editor2d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self.on_obj2d_unselected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_SELECTED, self.on_obj3d_selected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self.on_obj3d_unselected)

    def set_buttons(self, align):
        icons = _image.icons
        left_icn = self._get_icon(False, icons.align_left_edge)
        center_icn = self._get_icon(False, icons.align_horizontal_center)
        right_icn = self._get_icon(False, icons.align_right_edge)

        state = True

        if align == build123d.TextAlign.LEFT.value:
            left_icn = self._get_icon(True, icons.align_left_edge)
        elif align == build123d.TextAlign.CENTER.value:
            center_icn = self._get_icon(True, icons.align_horizontal_center)
        elif align == build123d.TextAlign.RIGHT.value:
            right_icn = self._get_icon(True, icons.align_right_edge)
        else:
            state = False

        self.align_left.setIcon(left_icn)
        self.align_center.setIcon(center_icn)
        self.align_right.setIcon(right_icn)

        self.align_left.setEnabled(state)
        self.align_center.setEnabled(state)
        self.align_right.setEnabled(state)

    def on_align_left(self):
        self._obj.set_alignment(build123d.TextAlign.LEFT.value)
        self.set_buttons(build123d.TextAlign.LEFT.value)

    def on_align_center(self):
        self._obj.set_alignment(build123d.TextAlign.CENTER.value)
        self.set_buttons(build123d.TextAlign.CENTER.value)

    def on_align_right(self):
        self._obj.set_alignment(build123d.TextAlign.RIGHT.value)
        self.set_buttons(build123d.TextAlign.RIGHT.value)

    @staticmethod
    def _get_icon(state, icon):
        if state:
            icon = icon + _image.icons.checkbox
        else:
            icon = icon + _image.icons.uncheckbox

        return _make_icon(icon)

    def on_obj2d_selected(self, evt: "_gl.GLObjectEvent"):
        """
        Handle the obj 2D selected event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        obj = evt.GetGLObject()
        if isinstance(obj, _project_model.ProjectModel):
            evt.StopPropagation()
            return

        if isinstance(obj, _note.Note):
            self._obj = obj.obj2d
            self.set_buttons(obj.db_obj.h_align2d)
        else:
            self._obj = None
            self.set_buttons(-1)

    def on_obj2d_unselected(self, _: "_gl.GLObjectEvent"):
        """
        Handle the obj 2D unselected event.

        :type _: :class:`_gl.GLObjectEvent`
        """

        self._obj = None
        self.set_buttons(-1)

    def on_obj3d_selected(self, evt: "_gl.GLObjectEvent"):
        """
        Handle the obj 3D selected event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        obj = evt.GetGLObject()
        if isinstance(obj, _project_model.ProjectModel):
            evt.StopPropagation()
            return

        if isinstance(obj, _note.Note):
            self._obj = obj.obj3d
            self.set_buttons(obj.db_obj.h_align3d)
        else:
            self._obj = None
            self.set_buttons(-1)

    def on_obj3d_unselected(self, _: "_gl.GLObjectEvent"):
        """
        Handle the obj 3D unselected event.

        :type _: :class:`_gl.GLObjectEvent`
        """

        self._obj = None
        self.set_buttons(-1)

    def Refresh(self, *_, **__):
        """
        Execute the refresh operation.
        """

        self.repaint()

    def Destroy(self):
        """
        Execute the destroy operation.
        """

        self.deleteLater()


# ---------------------------------------------------------------------------
# EditorObjectToolbar
# ---------------------------------------------------------------------------

class EditorObjectToolbar(QtWidgets.QToolBar):
    """
    Transform-mode toolbar (rotate / scale / move on each axis).
    """

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
        """
        Initialise the :class:`EditorObjectToolbar` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self.mainframe = mainframe

        super().__init__('Object', mainframe)

        self.setObjectName('object_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        self._selected = None
        self._position3d: "_point.Point" = None
        self._angle3d: "_angle.Angle" = None
        self._scale3d: "_point.Point" = None

        icons = _image.icons
        self.rotate_x = _fsb.FloatSpinButton(
            self, 'X Axis', _make_icon(icons.rotate_x),
            -180, 180, 0.01, 2, '°')

        self.rotate_x.valueChanged.connect(self.on_rotate_x)
        self.addWidget(self.rotate_x)
        self.rotate_x.setEnabled(False)

        self.rotate_y = _fsb.FloatSpinButton(
            self, 'Y Axis', _make_icon(icons.rotate_y),
            -180, 180, 0.01, 2, '°')

        self.rotate_y.valueChanged.connect(self.on_rotate_y)
        self.addWidget(self.rotate_y)
        self.rotate_y.setEnabled(False)

        self.rotate_z = _fsb.FloatSpinButton(
            self, 'Z Axis', _make_icon(icons.rotate_z),
            -180, 180, 0.01, 2, '°')

        self.rotate_z.valueChanged.connect(self.on_rotate_z)
        self.addWidget(self.rotate_z)
        self.rotate_z.setEnabled(False)

        # Rotation-drag snap: left click toggles (checkbox overlay shows the
        # state), right click opens the angle popup. Always enabled — it is
        # a mode setting, not an object property.
        ring_config = _config.Config.editor3d.rotation_rings

        self.snap_angle = _sab.SnapAngleButton(
            self, 'Rotation Snap',
            _make_icon(icons.rotation_snap + icons.checkbox),
            _make_icon(icons.rotation_snap + icons.uncheckbox))

        self.snap_angle.SetValue(ring_config.snap_angle)
        self.snap_angle.SetSnapEnabled(ring_config.snap_enable)

        self.snap_angle.snapEnabledChanged.connect(self._on_snap_enabled)
        self.snap_angle.snapAngleChanged.connect(self._on_snap_angle)
        self.addWidget(self.snap_angle)

        self.scale_x = _fsb.FloatSpinButton(
            self, 'X Axis', _make_icon(icons.scale_x),
            0.01, 10.0, 0.01, 2, 'x')

        self.scale_x.valueChanged.connect(self.on_scale_x)
        self.addWidget(self.scale_x)
        self.scale_x.setEnabled(False)

        self.scale_y = _fsb.FloatSpinButton(
            self, 'Y Axis', _make_icon(icons.scale_y),
            0.01, 10.0, 0.01, 2, 'x')

        self.scale_y.valueChanged.connect(self.on_scale_y)
        self.addWidget(self.scale_y)
        self.scale_y.setEnabled(False)

        self.scale_z = _fsb.FloatSpinButton(
            self, 'Z Axis', _make_icon(icons.scale_z),
            0.01, 10.0, 0.01, 2, 'x')

        self.scale_z.valueChanged.connect(self.on_scale_z)
        self.addWidget(self.scale_z)
        self.scale_z.setEnabled(False)

        self.move_x = _fsb.FloatSpinButton(
            self, 'X Axis', _make_icon(icons.move_x),
            -9999.99, 9999.99, 0.01, 2, 'mm')

        self.move_x.valueChanged.connect(self.on_move_x)
        self.addWidget(self.move_x)
        self.move_x.setEnabled(False)

        self.move_y = _fsb.FloatSpinButton(
            self, 'Y Axis', _make_icon(icons.move_y),
            -9999.99, 9999.99, 0.01, 2, 'mm')

        self.move_y.valueChanged.connect(self.on_move_y)
        self.addWidget(self.move_y)
        self.move_y.setEnabled(False)

        self.move_z = _fsb.FloatSpinButton(
            self, 'Z Axis', _make_icon(icons.move_z),
            -9999.99, 9999.99, 0.01, 2, 'mm')

        self.move_z.valueChanged.connect(self.on_move_z)
        self.addWidget(self.move_z)
        self.move_z.setEnabled(False)

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

        # GL object selection drives button enable/disable
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_SELECTED, self._on_obj_selected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self._on_obj_unselected)

    def _on_obj_selected(self, evt: "_gl.GLObjectEvent"):
        obj = evt.GetGLObject()

        if isinstance(obj, _project_model.ProjectModel):
            evt.StopPropagation()
            return

        if self._position3d is not None:
            self._position3d.unbind(self.on_position)
            self._position3d = None

        if self._angle3d is not None:
            self._angle3d.unbind(self.on_angle)
            self._angle3d = None

        if self._scale3d is not None:
            self._scale3d.unbind(self.on_scale)
            self._scale3d = None

        if self._selected is not None:
            self._selected = None

        if isinstance(obj, (
            _bundle.Bundle, _wire.Wire, _cavity.Cavity, _wire_marker.WireMarker,
            _wire_layout.WireLayout, _bundle_layout.BundleLayout)):

            for act in (self.rotate_x, self.rotate_y, self.rotate_z, self.scale_x,
                        self.scale_y, self.scale_z, self.move_x, self.move_y,
                        self.move_z):

                act.setEnabled(False)
        else:
            for act in (self.rotate_x, self.rotate_y, self.rotate_z, self.scale_x,
                        self.scale_y, self.scale_z, self.move_x, self.move_y,
                        self.move_z):

                act.setEnabled(True)

            self._selected = obj

            self._position3d = obj.db_obj.position3d  # NOQA
            self._position3d.bind(self.on_position)

            self._angle3d = obj.db_obj.angle3d  # NOQA
            self._angle3d.bind(self.on_angle)

            self._scale3d = obj.db_obj.scale3d  # NOQA
            self._scale3d.bind(self.on_scale)

            x, y, z = self._position3d.as_float
            self.move_x.SetValue(x)
            self.move_y.SetValue(y)
            self.move_z.SetValue(z)

            x, y, z = self._angle3d.as_euler_float
            self.rotate_x.SetValue(x)
            self.rotate_y.SetValue(y)
            self.rotate_z.SetValue(z)

            x, y, z = self._scale3d.as_float
            self.scale_x.SetValue(x)
            self.scale_y.SetValue(y)
            self.scale_z.SetValue(z)

    def _on_obj_unselected(self, _):
        if self._position3d is not None:
            self._position3d.unbind(self.on_position)
            self._position3d = None

        if self._angle3d is not None:
            self._angle3d.unbind(self.on_angle)
            self._angle3d = None

        if self._scale3d is not None:
            self._scale3d.unbind(self.on_scale)
            self._scale3d = None

        if self._selected is not None:
            self._selected = None

        for act in (self.rotate_x, self.rotate_y, self.rotate_z, self.scale_x,
                    self.scale_y, self.scale_z, self.move_x, self.move_y,
                    self.move_z):

            act.setEnabled(False)
            act.SetValue(0.0)

    @staticmethod
    def _on_snap_enabled(enabled: bool) -> None:
        _config.Config.editor3d.rotation_rings.snap_enable = bool(enabled)

    @staticmethod
    def _on_snap_angle(value: float) -> None:
        _config.Config.editor3d.rotation_rings.snap_angle = float(value)

    def on_rotate_x(self, value: float) -> None:
        if self._angle3d is not None:
            self._angle3d.unbind(self.on_angle)
            self._angle3d.x = value
            self._angle3d.bind(self.on_angle)

    def on_rotate_y(self, value: float) -> None:
        if self._angle3d is not None:
            self._angle3d.unbind(self.on_angle)
            self._angle3d.y = value
            self._angle3d.bind(self.on_angle)

    def on_rotate_z(self, value: float) -> None:
        if self._angle3d is not None:
            self._angle3d.unbind(self.on_angle)
            self._angle3d.z = value
            self._angle3d.bind(self.on_angle)

    def on_angle(self, angle: "_angle.Angle"):
        self.rotate_x.SetValue(angle.x)
        self.rotate_y.SetValue(angle.y)
        self.rotate_z.SetValue(angle.z)

    def on_scale_x(self, value: float) -> None:
        if self._scale3d is not None:
            self._scale3d.unbind(self.on_scale)
            self._scale3d.x = value
            self._scale3d.bind(self.on_scale)

    def on_scale_y(self, value: float) -> None:
        if self._scale3d is not None:
            self._scale3d.unbind(self.on_scale)
            self._scale3d.y = value
            self._scale3d.bind(self.on_scale)

    def on_scale_z(self, value: float) -> None:
        if self._scale3d is not None:
            self._scale3d.unbind(self.on_scale)
            self._scale3d.z = value
            self._scale3d.bind(self.on_scale)

    def on_scale(self, scale: "_point.Point"):
        self.scale_x.SetValue(scale.x)
        self.scale_y.SetValue(scale.y)
        self.scale_z.SetValue(scale.z)

    def on_move_x(self, value: float) -> None:
        if self._position3d is not None:
            self._position3d.unbind(self.on_position)
            self._position3d.x = value
            self._position3d.bind(self.on_position)

    def on_move_y(self, value: float) -> None:
        if self._position3d is not None:
            self._position3d.unbind(self.on_position)
            self._position3d.y = value
            self._position3d.bind(self.on_position)

    def on_move_z(self, value: float) -> None:
        if self._position3d is not None:
            self._position3d.unbind(self.on_position)
            self._position3d.z = value
            self._position3d.bind(self.on_position)

    def on_position(self, position: "_point.Point"):
        self.move_x.SetValue(position.x)
        self.move_y.SetValue(position.y)
        self.move_z.SetValue(position.z)

    def on_tools(self, id_: int):
        """
        Handle the tools event.

        :param id_: Identifier for the ID.
        :type id_: int
        """

        pass  # future: notify handlers of transform mode change

    def Refresh(self, *_, **__):
        """
        Execute the refresh operation.
        """

        self.repaint()

    def Destroy(self):
        """
        Execute the destroy operation.
        """

        self.deleteLater()


# ---------------------------------------------------------------------------
# Setting3DToolbar
# ---------------------------------------------------------------------------

class Setting3DToolbar(QtWidgets.QToolBar):
    """Toggle toolbar for 3D viewport display settings."""

    ID_SHOW_SPOTLIGHT = _new_id()
    ID_SHOW_NORMALS = _new_id()
    ID_SHOW_WIREFRAME = _new_id()
    ID_SHOW_VERTICES = _new_id()
    ID_SHOW_REFLECTIONS = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`Setting3DToolbar` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        super().__init__('3D Settings', mainframe)
        self.mainframe = mainframe

        self.setObjectName('settings3d_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        icons = _image.icons

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_aabb, icons.aabb)

        self.show_aabb = QtGui.QAction(icn, 'Show AABB', self)
        self.show_aabb.setCheckable(False)
        self.show_aabb.triggered.connect(self.on_aabb)
        self.addAction(self.show_aabb)

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_obb, icons.obb)

        self.show_obb = QtGui.QAction(icn, 'Show OBB', self)
        self.show_obb.setCheckable(False)
        self.show_obb.triggered.connect(self.on_obb)
        self.addAction(self.show_obb)

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_edges, icons.wireframe)

        self.show_wireframe = QtGui.QAction(icn, 'Show Wireframe', self)
        self.show_wireframe.setCheckable(False)
        self.show_wireframe.triggered.connect(self.on_wireframe)
        self.addAction(self.show_wireframe)

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_faces, icons.faces)

        self.show_faces = QtGui.QAction(icn, 'Show Faces', self)
        self.show_faces.setCheckable(False)
        self.show_faces.triggered.connect(self.on_faces)
        self.addAction(self.show_faces)

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_normals, icons.normals)

        self.show_normals = QtGui.QAction(icn, 'Show Normals', self)
        self.show_normals.setCheckable(False)
        self.show_normals.triggered.connect(self.on_normals)
        self.addAction(self.show_normals)

        icn = self._get_icon(
            mainframe.config.debug.rendering3d.draw_vertices, icons.vertices)

        self.show_vertices = QtGui.QAction(icn, 'Show Vertices', self)
        self.show_vertices.setCheckable(False)
        self.show_vertices.triggered.connect(self.on_vertices)
        self.addAction(self.show_vertices)

        icn = self._get_icon(
            mainframe.config.editor3d.floor.reflections.enable, icons.reflections)

        self.show_reflections = QtGui.QAction(icn, 'Show Reflections', self)
        self.show_reflections.setCheckable(False)
        self.show_reflections.triggered.connect(self.on_reflections)
        self.addAction(self.show_reflections)

        icn = self._get_icon(
            mainframe.config.editor3d.headlight.enable, icons.spot_light)

        self.show_spotlight = QtGui.QAction(icn, 'Show Spotlight', self)
        self.show_spotlight.setCheckable(False)
        self.show_spotlight.triggered.connect(self.on_spotlight)
        self.addAction(self.show_spotlight)

        # Locked top-down (bird's-eye) view: composes the camera icon with
        # the lock/unlock overlay rather than the checkbox one, since this
        # isn't a simple display toggle — it also snaps/restricts the camera.
        icn = self._get_lock_icon(mainframe.config.editor3d.edit2d.enable)

        self.lock_top_view = QtGui.QAction(icn, 'Lock Top View', self)
        self.lock_top_view.setCheckable(False)
        self.lock_top_view.triggered.connect(self.on_lock_top_view)
        self.addAction(self.lock_top_view)

        # Apply the persisted lock state to the camera at startup.
        mainframe.editor3d.camera.SetTopDownLock(mainframe.config.editor3d.edit2d.enable)

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

    @staticmethod
    def _get_icon(state, icon):
        if state:
            icon = icon + _image.icons.checkbox
        else:
            icon = icon + _image.icons.uncheckbox

        return _make_icon(icon)

    @staticmethod
    def _get_lock_icon(enable):
        icons = _image.icons
        return _make_icon(icons.camera + (icons.lock if enable else icons.unlock))

    def on_wireframe(self, _: bool):
        """
        Handle the show wireframe toggle.
        """
        self.mainframe.config.debug.rendering3d.draw_edges = (
            not self.mainframe.config.debug.rendering3d.draw_edges)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_edges, _image.icons.wireframe)

        self.show_wireframe.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_reflections(self, _: bool):
        """
        Handle the show reflections toggle.
        """
        self.mainframe.config.editor3d.floor.reflections.enable = (
            not self.mainframe.config.editor3d.floor.reflections.enable)

        icn = self._get_icon(
            self.mainframe.config.editor3d.floor.reflections.enable, _image.icons.reflections)

        self.show_reflections.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_spotlight(self, _: bool):
        """
        Handle the show spotlight toggle.
        """
        self.mainframe.config.editor3d.headlight.enable = (
            not self.mainframe.config.editor3d.headlight.enable)

        icn = self._get_icon(
            self.mainframe.config.editor3d.headlight.enable, _image.icons.spot_light)

        self.show_spotlight.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_lock_top_view(self, _: bool = False):
        """
        Handle the locked top-down view toggle.
        """
        enable = not self.mainframe.config.editor3d.edit2d.enable

        self.mainframe.editor3d.camera.SetTopDownLock(enable)

        self.lock_top_view.setIcon(self._get_lock_icon(enable))

        self.mainframe.editor3d.Refresh()

    def on_normals(self, _: bool):
        """
        Handle the show normals toggle.
        """

        self.mainframe.config.debug.rendering3d.draw_normals = (
            not self.mainframe.config.debug.rendering3d.draw_normals)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_normals, _image.icons.normals)

        self.show_normals.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_vertices(self, _: bool):
        """
        Handle the show vertices toggle.
        """
        self.mainframe.config.debug.rendering3d.draw_vertices = (
            not self.mainframe.config.debug.rendering3d.draw_vertices)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_vertices, _image.icons.vertices)

        self.show_vertices.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_aabb(self, _: bool):
        """
        Handle the show aabb toggle.
        """

        self.mainframe.config.debug.rendering3d.draw_aabb = (
            not self.mainframe.config.debug.rendering3d.draw_aabb)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_aabb, _image.icons.aabb)

        self.show_aabb.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_faces(self, _: bool):
        """
        Handle the show faces toggle.
        """

        self.mainframe.config.debug.rendering3d.draw_faces = (
            not self.mainframe.config.debug.rendering3d.draw_faces)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_faces, _image.icons.faces)

        self.show_faces.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def on_obb(self, _: bool):
        """
        Handle the show obb toggle.
        """

        self.mainframe.config.debug.rendering3d.draw_obb = (
            not self.mainframe.config.debug.rendering3d.draw_obb)

        icn = self._get_icon(
            self.mainframe.config.debug.rendering3d.draw_obb, _image.icons.obb)

        self.show_obb.setIcon(icn)

        self.mainframe.editor3d.Refresh()

    def Refresh(self, *_, **__):
        """Repaint the toolbar."""
        self.repaint()

    def Destroy(self):
        """Schedule the toolbar for deletion."""
        self.deleteLater()


# ---------------------------------------------------------------------------
# PegBoardToolbar
# ---------------------------------------------------------------------------

class PegBoardToolbar(QtWidgets.QToolBar):
    """
    Peg Board Editor interaction toolbar.

    Structural mirror of :class:`Setting3DToolbar` -- a small, focused,
    always-visible toolbar dedicated to one editor's settings. Holds only
    the grid-snap toggle for now (see
    :class:`harness_designer.ui.toolbar.pegboard_snap_button.PegboardSnapButton`).

    A new toolbar (rather than folding this button into an existing one)
    because none of the existing toolbars share this button's theme:
    ``EditorObjectToolbar`` is specifically about 3D object transforms
    (rotate/scale/move), ``Setting3DToolbar`` is specifically about the 3D
    viewport's debug/display toggles, and ``GeneralToolbar`` is app-level
    dialogs (settings/tools/BOM/etc.), not per-viewport interaction state.
    Still follows this codebase's "toolbars are global, not per-editor-
    focus" convention -- constructed unconditionally in ``mainframe.py``
    alongside the others, regardless of which editor dock has focus.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`PegBoardToolbar` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self.mainframe = mainframe

        super().__init__('Peg Board', mainframe)
        self.setObjectName('pegboard_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        # Grid snap: left click toggles (checkbox overlay shows the state),
        # right click opens the manual-spacing popup. Always enabled -- it
        # is a mode setting, not an object property.
        grid_config = _config.Config.editor_pegboard.grid

        icons = _image.icons
        self.pegboard_snap = _psb.PegboardSnapButton(
            self, 'Grid Snap',
            _make_icon(icons.mip_mapping + icons.checkbox),
            _make_icon(icons.mip_mapping + icons.uncheckbox))

        self.pegboard_snap.SetManualSpacing(grid_config.manual_snap_spacing)
        self.pegboard_snap.SetSnapEnabled(grid_config.snap)

        self.pegboard_snap.snapEnabledChanged.connect(self._on_snap_enabled)
        self.pegboard_snap.manualSpacingChanged.connect(self._on_manual_spacing)
        self.addWidget(self.pegboard_snap)

        # Drag mode: "clamp" (dragging stops at each segment's length
        # limit) or "pull" (dragging past a taut segment pulls the
        # neighboring point along instead). A mode setting, not an object
        # property -- always enabled, same convention as the grid-snap
        # button above.
        self.pegboard_drag_mode = _pdmb.PegboardDragModeButton(self)
        self.pegboard_drag_mode.SetDragMode(
            _config.Config.editor_pegboard.drag.mode)
        self.pegboard_drag_mode.dragModeChanged.connect(self._on_drag_mode)
        self.addWidget(self.pegboard_drag_mode)

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

    @staticmethod
    def _on_snap_enabled(enabled: bool) -> None:
        _config.Config.editor_pegboard.grid.snap = bool(enabled)

    @staticmethod
    def _on_manual_spacing(value) -> None:
        _config.Config.editor_pegboard.grid.manual_snap_spacing = (
            None if value is None else float(value))

    @staticmethod
    def _on_drag_mode(mode: str) -> None:
        _config.Config.editor_pegboard.drag.mode = mode

    def Refresh(self, *_, **__):
        """Repaint the toolbar."""
        self.repaint()

    def Destroy(self):
        """Schedule the toolbar for deletion."""
        self.deleteLater()


# ---------------------------------------------------------------------------
# GeneralToolbar
# ---------------------------------------------------------------------------

class GeneralToolbar(QtWidgets.QToolBar):
    """Application-level toolbar (browser, settings, tools, connect, BOM)."""

    ID_BROWSER = _new_id()
    ID_SETTINGS = _new_id()
    ID_TOOLS = _new_id()
    ID_CONNECT = _new_id()
    ID_BOM = _new_id()

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`GeneralToolbar` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self.mainframe = mainframe

        super().__init__('General', mainframe)
        self.setObjectName('general_toolbar')
        self.setMovable(True)
        self.setFloatable(True)
        self.setIconSize(QtCore.QSize(32, 32))

        def _push(id_: int, label: str, icon: QtGui.QIcon, slot) -> QtGui.QAction:
            """Execute the push operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param id_: Identifier for the ID.
            :type id_: int
            :param label: Value for ``label``.
            :type label: str
            :param icon: Value for ``icon``.
            :type icon: :class:`QIcon`
            :param slot: Value for ``slot``.
            :type slot: UNKNOWN
            :returns: Return value. UNKNOWN details.
            :rtype: :class:`QAction`
            """
            act = QtGui.QAction(icon, label, self)
            act.setToolTip(label)
            act.setData(id_)
            act.triggered.connect(slot)
            self.addAction(act)
            return act

        icons = _image.icons
        _push(self.ID_BROWSER, 'Internet', _make_icon(icons.internet), self.on_browser)
        _push(self.ID_SETTINGS, 'Settings', _make_icon(icons.settings), self.on_settings)
        _push(self.ID_TOOLS, 'Tools', _make_icon(icons.tool), self.on_tools)
        _push(self.ID_CONNECT, 'Connect Database', _make_icon(icons.connect), self.on_database)
        _push(self.ID_BOM, 'BOM', _make_icon(icons.bom), self.on_bom)

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

    def on_browser(self, checked: bool = False):
        """Handle the browser event.

        UNKNOWN details are inferred from the callable name and signature.

        :param checked: Value for ``checked``.
        :type checked: bool
        """
        pass

    def on_settings(self, checked: bool = False):
        """Handle the settings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param checked: Value for ``checked``.
        :type checked: bool
        """
        pass

    def on_tools(self, checked: bool = False):
        """Handle the tools event.

        UNKNOWN details are inferred from the callable name and signature.

        :param checked: Value for ``checked``.
        :type checked: bool
        """
        pass

    def on_database(self, checked: bool = False):
        """Handle the database event.

        UNKNOWN details are inferred from the callable name and signature.

        :param checked: Value for ``checked``.
        :type checked: bool
        """
        pass

    def on_bom(self, checked: bool = False):
        """Handle the bom event.

        UNKNOWN details are inferred from the callable name and signature.

        :param checked: Value for ``checked``.
        :type checked: bool
        """
        pass

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.repaint()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.deleteLater()
