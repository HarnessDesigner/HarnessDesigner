# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Mouse and Keyboard panels of the Preferences dialog.

Each is a notebook with one page per editor (3D, Pegboard, Schematic) that
edits that editor's ``Config.editor_*.input`` bindings. The mouse and key
handlers read those settings on every event, so a change applies at once.

How the settings are stored:

* ``mouse`` is a bit mask: one bit per mouse button (``MOUSE_LEFT`` ...,
  ``MOUSE_WHEEL``) plus the modifier bits ``MOUSE_REVERSE_X_AXIS``,
  ``MOUSE_REVERSE_Y_AXIS`` and ``MOUSE_SWAP_AXIS``.
* ``*_key`` is ``None`` (unbound), the lower case ``ord`` of a printable key
  (``ord('w')``) or the ``QtCore.Qt.Key`` value of any other key (the arrows,
  Home, ...). ``gl/canvas_base/key_handler.py`` ``_process_key_event``
  matches a pressed key against that, so :func:`_to_config_key` writes the
  same two forms.
"""

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import fields as _fields
from . import page_base as _page_base
from .... import config as _config
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui


_MOUSE_BUTTONS: list[tuple[str, int]] = [
    ('Left', _config.MOUSE_LEFT),
    ('Middle', _config.MOUSE_MIDDLE),
    ('Right', _config.MOUSE_RIGHT),
    ('Aux 1', _config.MOUSE_AUX1),
    ('Aux 2', _config.MOUSE_AUX2),
    ('Wheel', _config.MOUSE_WHEEL)
]

_MOUSE_OPTIONS: list[tuple[str, int]] = [
    ('Reverse X', _config.MOUSE_REVERSE_X_AXIS),
    ('Reverse Y', _config.MOUSE_REVERSE_Y_AXIS),
    ('Swap X / Y', _config.MOUSE_SWAP_AXIS)
]

# (setting name, title, has a speed setting)
_MOUSE_ACTIONS_3D: list[tuple[str, str, bool]] = [
    ('rotate', 'Rotate (orbit)', False),
    ('pan_tilt', 'Pan / Tilt', False),
    ('truck_pedestal', 'Truck / Pedestal', True),
    ('walk', 'Walk', True),
    ('dolly', 'Dolly', False),
    ('zoom', 'Zoom', False),
    ('reset', 'Reset view', False)
]

# The two flat editors store only these three; their other actions are
# placeholders that are not saved.
_MOUSE_ACTIONS_2D: list[tuple[str, str, bool]] = [
    ('truck_pedestal', 'Pan (truck / pedestal)', True),
    ('zoom', 'Zoom', False),
    ('reset', 'Reset view', False)
]

# (setting name, title, [(setting name, label), ...])
_KEY_ACTIONS_3D: list[tuple[str, str, list[tuple[str, str]]]] = [
    ('rotate', 'Rotate (orbit)', [
        ('up_key', 'Up'), ('down_key', 'Down'),
        ('left_key', 'Left'), ('right_key', 'Right')]),
    ('pan_tilt', 'Pan / Tilt', [
        ('up_key', 'Up'), ('down_key', 'Down'),
        ('left_key', 'Left'), ('right_key', 'Right')]),
    ('truck_pedestal', 'Truck / Pedestal', [
        ('up_key', 'Up'), ('down_key', 'Down'),
        ('left_key', 'Left'), ('right_key', 'Right')]),
    ('walk', 'Walk', [
        ('forward_key', 'Forward'), ('backward_key', 'Backward'),
        ('left_key', 'Left'), ('right_key', 'Right')]),
    ('dolly', 'Dolly', [('in_key', 'In'), ('out_key', 'Out')]),
    ('zoom', 'Zoom', [('in_key', 'In'), ('out_key', 'Out')]),
    ('reset', 'Reset view', [('key', 'Reset')])
]

_KEY_ACTIONS_2D: list[tuple[str, str, list[tuple[str, str]]]] = [
    ('truck_pedestal', 'Pan (truck / pedestal)', [
        ('up_key', 'Up'), ('down_key', 'Down'),
        ('left_key', 'Left'), ('right_key', 'Right')]),
    ('zoom', 'Zoom', [('in_key', 'In'), ('out_key', 'Out')]),
    ('reset', 'Reset view', [('key', 'Reset')])
]

# Editor tabs, in notebook order: (section path, tab title).
EDITORS: list[tuple[str, str]] = [
    ('editor_3d', '3D'),
    ('editor_pegboard', 'Pegboard'),
    ('editor_schematic', 'Schematic')
]

_KEYBOARD_SPEED_NAMES = ['start_speed_factor', 'speed_factor_increment',
                         'max_speed_factor']

_MODIFIER_KEYS = {
    QtCore.Qt.Key.Key_Shift, QtCore.Qt.Key.Key_Control, QtCore.Qt.Key.Key_Alt,
    QtCore.Qt.Key.Key_AltGr, QtCore.Qt.Key.Key_Meta,
    QtCore.Qt.Key.Key_CapsLock, QtCore.Qt.Key.Key_NumLock,
    QtCore.Qt.Key.Key_ScrollLock
}


@_check_types.do
def _to_config_key(qt_key: int) -> int:
    """A ``QKeyEvent.key()`` as ``Config`` stores it: printable keys as the
    lower case ``ord`` (``Qt.Key_W`` 0x57 -> ``ord('w')``), the rest as is."""
    if 32 <= qt_key <= 126:
        return ord(chr(qt_key).lower())

    return qt_key


@_check_types.do
def _key_name(key: int | None) -> str:
    """What a stored key is called on the button."""
    if key is None:
        return '(none)'

    if key == 32:
        return 'Space'

    if 32 < key <= 126:
        return chr(key).upper()

    name = QtGui.QKeySequence(key).toString()
    if name:
        return name

    return f'Key {key}'


class MouseActionGroup(QtWidgets.QGroupBox):
    """One mouse action: which buttons drive it and how fast.

    :param path: Section of the action, ``'editor_3d.input.rotate'``.
    :param title: The group's title.
    :param has_speed: The action also has a ``speed`` setting.
    :param buttons_only: The action has only ``mouse`` (reset view).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, path: str, title: str,
                 has_speed: bool, buttons_only: bool):
        super().__init__(title, parent)

        self._section = _fields.section(path)
        self._buttons: list[tuple[QtWidgets.QCheckBox, int]] = []
        self._options: list[tuple[QtWidgets.QCheckBox, int]] = []
        self._sensitivity: QtWidgets.QDoubleSpinBox | None = None
        self._speed: QtWidgets.QDoubleSpinBox | None = None

        stored = self._section['mouse']
        if stored is None:
            stored = 0

        self._known_bits = 0

        grid = QtWidgets.QGridLayout(self)

        row = QtWidgets.QHBoxLayout()
        for label, bit in _MOUSE_BUTTONS:
            box = QtWidgets.QCheckBox(label, self)
            box.setChecked(bool(stored & bit))
            row.addWidget(box)
            self._buttons.append((box, bit))
            self._known_bits |= bit

        row.addStretch(1)
        grid.addWidget(QtWidgets.QLabel('Buttons:', self), 0, 0)
        grid.addLayout(row, 0, 1)

        if not buttons_only:
            row = QtWidgets.QHBoxLayout()
            for label, bit in _MOUSE_OPTIONS:
                box = QtWidgets.QCheckBox(label, self)
                box.setChecked(bool(stored & bit))
                row.addWidget(box)
                self._options.append((box, bit))
                self._known_bits |= bit

            row.addStretch(1)
            grid.addWidget(QtWidgets.QLabel('Options:', self), 1, 0)
            grid.addLayout(row, 1, 1)

            row = QtWidgets.QHBoxLayout()
            row.addWidget(QtWidgets.QLabel('Sensitivity:', self))

            self._sensitivity = QtWidgets.QDoubleSpinBox(self)
            self._sensitivity.setDecimals(3)
            self._sensitivity.setRange(0.0, 1000.0)
            self._sensitivity.setSingleStep(0.05)
            self._sensitivity.setValue(float(self._section['sensitivity']))
            row.addWidget(self._sensitivity)

            if has_speed:
                row.addSpacing(20)
                row.addWidget(QtWidgets.QLabel('Speed:', self))

                self._speed = QtWidgets.QDoubleSpinBox(self)
                self._speed.setDecimals(3)
                self._speed.setRange(0.0, 1000.0)
                self._speed.setSingleStep(0.1)
                self._speed.setValue(float(self._section['speed']))
                row.addWidget(self._speed)

            row.addStretch(1)
            grid.addLayout(row, 2, 1)

        self._initial_mouse = self._read_mouse()
        self._initial_sensitivity = self._read_spin(self._sensitivity)
        self._initial_speed = self._read_spin(self._speed)

    @_check_types.do
    def _read_spin(self, spin: QtWidgets.QDoubleSpinBox | None) -> float | None:
        if spin is None:
            return None

        return spin.value()

    @_check_types.do
    def _read_mouse(self) -> int:
        """The mask with the boxes applied; bits the dialog has no box for
        are kept as they are stored."""
        stored = self._section['mouse']
        if stored is None:
            stored = 0

        mask = stored & ~self._known_bits

        for box, bit in self._buttons + self._options:
            if box.isChecked():
                mask |= bit

        return mask

    @_check_types.do
    def apply(self) -> list[str]:
        mask = self._read_mouse()
        if mask != self._initial_mouse:
            self._section['mouse'] = mask
            self._initial_mouse = mask

        sensitivity = self._read_spin(self._sensitivity)
        if sensitivity is not None and sensitivity != self._initial_sensitivity:
            self._section['sensitivity'] = sensitivity
            self._initial_sensitivity = sensitivity

        speed = self._read_spin(self._speed)
        if speed is not None and speed != self._initial_speed:
            self._section['speed'] = speed
            self._initial_speed = speed

        return []


class KeyButton(QtWidgets.QPushButton):
    """Shows a bound key. Click it, then press the new key: Escape cancels,
    Backspace or Delete unbinds it."""

    keyChanged = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, key: int | None):
        super().__init__(parent)

        self._key = key
        self._capturing = False

        self.setMinimumWidth(90)
        self.setToolTip('Click, then press a key. Backspace or Delete '
                        'unbinds, Escape cancels.')

        self.clicked.connect(self._begin_capture)
        self._refresh()

    @_check_types.do
    def _refresh(self) -> None:
        self.setText(_key_name(self._key))

    @_check_types.do
    def _begin_capture(self) -> None:
        self._capturing = True
        self.setText('Press a key...')
        self.grabKeyboard()

    @_check_types.do
    def _end_capture(self) -> None:
        self._capturing = False
        self.releaseKeyboard()
        self._refresh()

    @_check_types.do
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if not self._capturing:
            super().keyPressEvent(event)
            return

        qt_key = event.key()

        # A lone modifier is not a binding; wait for the real key.
        if qt_key in _MODIFIER_KEYS:
            return

        if qt_key == QtCore.Qt.Key.Key_Escape:
            self._end_capture()
            return

        if qt_key in (QtCore.Qt.Key.Key_Backspace, QtCore.Qt.Key.Key_Delete):
            self._key = None
        else:
            self._key = _to_config_key(qt_key)

        self._end_capture()
        self.keyChanged.emit()

    @_check_types.do
    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        if self._capturing:
            self._end_capture()

        super().focusOutEvent(event)

    @_check_types.do
    def GetValue(self) -> int | None:
        return self._key


class KeyActionGroup(QtWidgets.QGroupBox):
    """The keys of one action (up / down / left / right, in / out, ...).

    :param path: Section of the action, ``'editor_3d.input.walk'``.
    :param title: The group's title.
    :param keys: ``(setting name, label)`` for each key of the action.
    """

    keyChanged = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, path: str, title: str,
                 keys: list[tuple[str, str]]):
        super().__init__(title, parent)

        self._section = _fields.section(path)
        self._title = title

        #: (setting name, label, button)
        self.buttons: list[tuple[str, str, KeyButton]] = []
        self._initial: dict[str, int | None] = {}

        row = QtWidgets.QHBoxLayout(self)

        for name, label in keys:
            button = KeyButton(self, self._section[name])
            button.keyChanged.connect(self.keyChanged)

            row.addWidget(QtWidgets.QLabel(label + ':', self))
            row.addWidget(button)
            row.addSpacing(10)

            self.buttons.append((name, label, button))
            self._initial[name] = button.GetValue()

        row.addStretch(1)

    @_check_types.do
    def bindings(self) -> list[tuple[int | None, str]]:
        """``(key, "Action label")`` for each button, for the conflict check."""
        return [(button.GetValue(), f'{self._title} {label.lower()}')
                for _, label, button in self.buttons]

    @_check_types.do
    def apply(self) -> list[str]:
        for name, _, button in self.buttons:
            key = button.GetValue()
            if key != self._initial[name]:
                self._section[name] = key
                self._initial[name] = key

        return []


class MouseTab(_page_base.PreferencesPage):
    """The mouse bindings of one editor."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None,
                 mainframe: "_ui.MainFrame", editor: str,
                 actions: list[tuple[str, str, bool]]):
        super().__init__(parent, mainframe)

        for name, title, has_speed in actions:
            self.add_item(MouseActionGroup(
                self, f'{editor}.input.{name}', title, has_speed,
                name == 'reset'))

        self.finish()


class KeyboardTab(_page_base.PreferencesPage):
    """The key bindings of one editor, and its key movement speed."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None,
                 mainframe: "_ui.MainFrame", editor: str,
                 actions: list[tuple[str, str, list[tuple[str, str]]]]):
        super().__init__(parent, mainframe)

        self._groups: list[KeyActionGroup] = []

        self._conflicts = QtWidgets.QLabel(self)
        self._conflicts.setWordWrap(True)
        self._conflicts.setStyleSheet('color: red;')
        self._conflicts.hide()
        self._layout.addWidget(self._conflicts)

        for name, title, keys in actions:
            group = KeyActionGroup(self, f'{editor}.input.{name}', title, keys)
            group.keyChanged.connect(self._update_conflicts)

            self._groups.append(group)
            self.add_item(group)

        self.add_group('Movement speed', [
            _fields.real(f'{editor}.keyboard_settings', 'start_speed_factor',
                         'Start speed factor', 0.0, 100.0, 0.05),
            _fields.real(f'{editor}.keyboard_settings', 'speed_factor_increment',
                         'Speed increase per step', 0.0, 100.0, 0.01),
            _fields.real(f'{editor}.keyboard_settings', 'max_speed_factor',
                         'Maximum speed factor', 0.0, 100.0, 0.1)
        ])

        self.finish()
        self._update_conflicts()

    @_check_types.do
    def _update_conflicts(self) -> None:
        """Warn (without blocking) when one key is bound to several keys."""
        used: dict[int, list[str]] = {}

        for group in self._groups:
            for key, label in group.bindings():
                if key is not None:
                    used.setdefault(key, []).append(label)

        lines = [f'{_key_name(key)} is bound to: {", ".join(labels)}'
                 for key, labels in used.items() if len(labels) > 1]

        if lines:
            self._conflicts.setText('\n'.join(lines))
            self._conflicts.show()
        else:
            self._conflicts.hide()


@_check_types.do
def build_mouse_panel(parent: QtWidgets.QWidget | None,
                      mainframe: "_ui.MainFrame") -> _page_base.TabbedPanel:
    """The Mouse notebook: one tab per editor, in :data:`EDITORS` order."""
    panel = _page_base.TabbedPanel(parent)

    for editor, title in EDITORS:
        if editor == 'editor_3d':
            actions = _MOUSE_ACTIONS_3D
        else:
            actions = _MOUSE_ACTIONS_2D

        panel.add_tab(title, MouseTab(panel, mainframe, editor, actions))

    return panel


@_check_types.do
def build_keyboard_panel(parent: QtWidgets.QWidget | None,
                         mainframe: "_ui.MainFrame") -> _page_base.TabbedPanel:
    """The Keyboard notebook: one tab per editor, in :data:`EDITORS` order."""
    panel = _page_base.TabbedPanel(parent)

    for editor, title in EDITORS:
        if editor == 'editor_3d':
            actions = _KEY_ACTIONS_3D
        else:
            actions = _KEY_ACTIONS_2D

        panel.add_tab(title, KeyboardTab(panel, mainframe, editor, actions))

    return panel
