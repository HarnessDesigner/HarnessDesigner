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
        from ...objects import housing as _housing
        from ...objects import wire as _wire
        from ...objects import terminal as _terminal
        from ...objects import bundle as _bundle
        from ...objects import transition as _transition
        from ...objects import splice as _splice

        obj = evt.GetGLObject()

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

        group = QtGui.QActionGroup(self)
        group.setExclusive(True)

        def _radio(id_: int, label: str, icon: QtGui.QIcon) -> QtGui.QAction:
            """
            Execute the radio operation.

            :param id_: Identifier for the ID.
            :type id_: int
            :param label: Value for ``label``.
            :type label: str
            :param icon: Value for ``icon``.
            :type icon: :class:`QIcon`
            :returns: Return value. UNKNOWN details.
            :rtype: :class:`QAction`
            """

            act = QtGui.QAction(icon, label, self)
            act.setCheckable(True)
            act.setEnabled(False)
            act.setToolTip(label)
            act.setData(id_)
            group.addAction(act)
            self.addAction(act)
            return act

        icons = _image.icons
        self.align_left = _radio(self.ID_ALIGN_HORIZ_LEFT, 'Align Left',
                                 _make_icon(icons.align_left_edge))
        self.align_center = _radio(self.ID_ALIGN_HORIZ_CENTER, 'Align Center',
                                   _make_icon(icons.align_horizontal_center))
        self.align_right = _radio(self.ID_ALIGN_HORIZ_RIGHT, 'Align Right',
                                  _make_icon(icons.align_right_edge))

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

        mainframe.editor2d.bind(_gl.EVT_GL_OBJECT_SELECTED, self.on_obj2d_selected)
        mainframe.editor2d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self.on_obj2d_unselected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_SELECTED, self.on_obj3d_selected)
        mainframe.editor3d.bind(_gl.EVT_GL_OBJECT_UNSELECTED, self.on_obj3d_unselected)

        # "Pane activated" → QDockWidget.visibilityChanged on the editor docks.
        # We connect to each dock and check which editor is now on top.
        # mainframe.editor2d.visibilityChanged.connect(
        #     lambda visible: self._on_editor_visibility('editor2d', visible))
        # mainframe.editor3d.connect('visibilityChanged',
        #     lambda visible: self._on_editor_visibility('editor3d', visible))

    def _on_editor_visibility(self, editor_name: str, visible: bool):
        """
        Handle the editor visibility event.

        :param editor_name: Value for ``editor_name``.
        :type editor_name: str
        :param visible: Value for ``visible``.
        :type visible: bool
        """

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
        """
        Set the buttons.

        :param align: Value for ``align``.
        :type align: UNKNOWN
        :raises RuntimeError: Raised when the operation cannot be completed.
        """

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
        """
        Handle the obj 2D selected event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        obj = evt.GetGLObject()
        self.set_buttons(obj.db_obj.h_align2d if isinstance(obj, _note.Note) else -1)

    def on_obj2d_unselected(self, _: "_gl.GLObjectEvent"):
        """
        Handle the obj 2D unselected event.

        :type _: :class:`_gl.GLObjectEvent`
        """

        self.set_buttons(-1)

    def on_obj3d_selected(self, evt: "_gl.GLObjectEvent"):
        """
        Handle the obj 3D selected event.

        :param evt: Event object.
        :type evt: :class:`_gl.GLObjectEvent`
        """

        obj = evt.GetGLObject()
        self.set_buttons(obj.db_obj.h_align3d if isinstance(obj, _note.Note) else -1)

    def on_obj3d_unselected(self, _: "_gl.GLObjectEvent"):
        """
        Handle the obj 3D unselected event.

        :type _: :class:`_gl.GLObjectEvent`
        """

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

    def _on_obj_selected(self, evt):
        from ...objects import bundle as _bundle
        from ...objects import wire as _wire

        obj = evt.GetGLObject()

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

        if isinstance(obj, (_bundle.Bundle, _wire.Wire)):
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

            self._position3d = obj.db_obj.position3d
            self._position3d.bind(self.on_position)

            self._angle3d = obj.db_obj.angle3d
            self._angle3d.bind(self.on_angle)

            self._scale3d = obj.db_obj.scale3d
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

        mainframe.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self)

    @staticmethod
    def _get_icon(state, icon):
        if state:
            icon = icon + _image.icons.checkbox
        else:
            icon = icon + _image.icons.uncheckbox

        return _make_icon(icon)

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
