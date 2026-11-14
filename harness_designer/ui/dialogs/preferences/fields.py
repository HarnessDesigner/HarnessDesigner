# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The building blocks the Preferences pages are made of.

A *field* ties one ``Config`` setting to one editing widget. Fields are
created from a dotted section path (``'editor_3d.floor.grid'``) and a setting
name, read their value when their widget is built and write it back in
:meth:`Field.apply`, and only when the user changed it: a widget that shows a
rounded value (a spin box with 3 decimals over a stored 0.2039) must not
rewrite settings the user never touched.
"""

from typing import Any

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from .... import config as _config
from .... import check_types as _check_types


@_check_types.do
def section(path: str) -> "_config.ConfigType":
    """
    The ``Config`` class at the dotted *path*.

    :param path: ``'editor_3d.floor.grid'`` for ``Config.editor_3d.floor.grid``.
    :type path: str

    :rtype: _config.ConfigType
    """

    found = _config.Config

    for name in path.split('.'):
        found = found[name]

    return found


class ColorButton(QtWidgets.QPushButton):
    """A colour swatch that opens the colour dialog; works on the ``Config``
    colour lists of 3 (RGB) or 4 (RGBA) floats in the range 0 to 1.

    The value handed in is kept exactly as it was until the user picks a new
    colour, so an untouched button never changes a stored colour through the
    8 bit round trip of ``QColor``.
    """

    colorChanged = QtCore.Signal()

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None, value: list[float] | tuple[float, ...]):
        super().__init__(parent)

        self._value = [float(item) for item in value]
        self._has_alpha = len(self._value) > 3

        self.setMinimumWidth(110)
        self.setToolTip('Click to choose a colour')
        self.clicked.connect(self._pick)

        self._refresh()

    @_check_types.do
    def _qcolor(self) -> QtGui.QColor:
        r, g, b = self._value[:3]

        if self._has_alpha:
            a = self._value[3]
        else:
            a = 1.0

        return QtGui.QColor.fromRgbF(
            min(max(r, 0.0), 1.0), min(max(g, 0.0), 1.0),
            min(max(b, 0.0), 1.0), min(max(a, 0.0), 1.0))

    @_check_types.do
    def _refresh(self) -> None:
        color = self._qcolor()

        if color.lightnessF() > 0.5:
            text_color = 'black'
        else:
            text_color = 'white'

        text = color.name(QtGui.QColor.NameFormat.HexRgb).upper()
        if self._has_alpha:
            text += f'  {round(color.alphaF() * 100)}%'

        self.setText(text)

        # The swatch shows the colour itself without its alpha, so the
        # percentage in the text is the only transparency cue.
        opaque = color.name(QtGui.QColor.NameFormat.HexRgb)
        self.setStyleSheet(
            f'background-color: {opaque}; color: {text_color}; '
            'border: 1px solid gray; min-height: 20px;')

    @_check_types.do
    def _pick(self) -> None:
        options = QtWidgets.QColorDialog.ColorDialogOption(0)
        if self._has_alpha:
            options = QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel

        chosen = QtWidgets.QColorDialog.getColor(
            self._qcolor(), self, 'Choose colour', options)

        if not chosen.isValid():
            return

        value = [chosen.redF(), chosen.greenF(), chosen.blueF()]
        if self._has_alpha:
            value.append(chosen.alphaF())

        self._value = value
        self._refresh()
        self.colorChanged.emit()

    @_check_types.do
    def GetValue(self) -> list[float]:
        return list(self._value)


class Field:
    """One ``Config`` setting and the widget that edits it.

    :param path: Dotted ``Config`` section path.
    :param name: The setting's name in that section.
    :param label: What the row says.
    :param restart: The setting is only read when the application starts.

    Subclasses make the widget in :meth:`_create` and read it back in
    :meth:`_read`.
    """

    @_check_types.do
    def __init__(self, path: str, name: str, label: str, restart: bool = False):
        self.path = path
        self.name = name
        self.label = label
        self.restart = restart

        #: True after :meth:`apply` wrote a new value.
        self.changed = False

        self._initial: Any = None
        self._as_tuple = False

    @_check_types.do
    def build(self, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        """Make the editing widget showing the stored value."""
        stored = section(self.path)[self.name]
        self._as_tuple = isinstance(stored, tuple)

        widget = self._create(parent, stored)
        self._initial = self._read()

        return widget

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        raise NotImplementedError

    @_check_types.do
    def _read(self) -> Any:
        raise NotImplementedError

    @_check_types.do
    def apply(self) -> bool:
        """
        Write the widget's value to ``Config`` if the user changed it.

        :returns: ``True`` when a new value was written.
        :rtype: bool
        """

        self.changed = False

        value = self._read()
        if value == self._initial:
            return False

        # Lists stay lists and tuples stay tuples, as they were stored.
        if self._as_tuple:
            section(self.path)[self.name] = tuple(value)
        else:
            section(self.path)[self.name] = value

        self._initial = value
        self.changed = True

        return True


class BoolField(Field):

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = QtWidgets.QCheckBox(parent)
        self._widget.setChecked(bool(stored))

        return self._widget

    @_check_types.do
    def _read(self) -> bool:
        return self._widget.isChecked()


class IntField(Field):

    @_check_types.do
    def __init__(self, path: str, name: str, label: str, low: int, high: int,
                 restart: bool = False):
        super().__init__(path, name, label, restart)
        self._low = low
        self._high = high

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = QtWidgets.QSpinBox(parent)
        self._widget.setRange(self._low, self._high)
        self._widget.setValue(int(stored))

        return self._widget

    @_check_types.do
    def _read(self) -> int:
        return self._widget.value()


class FloatField(Field):

    @_check_types.do
    def __init__(self, path: str, name: str, label: str, low: float,
                 high: float, step: float = 0.1, decimals: int = 3,
                 restart: bool = False):
        super().__init__(path, name, label, restart)
        self._low = low
        self._high = high
        self._step = step
        self._decimals = decimals

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = QtWidgets.QDoubleSpinBox(parent)
        self._widget.setDecimals(self._decimals)
        self._widget.setRange(self._low, self._high)
        self._widget.setSingleStep(self._step)
        self._widget.setValue(float(stored))

        return self._widget

    @_check_types.do
    def _read(self) -> float:
        return self._widget.value()


class VectorField(Field):
    """A fixed number of floats in a row (a position)."""

    @_check_types.do
    def __init__(self, path: str, name: str, label: str, low: float,
                 high: float, step: float = 1.0, decimals: int = 2,
                 restart: bool = False):
        super().__init__(path, name, label, restart)
        self._low = low
        self._high = high
        self._step = step
        self._decimals = decimals
        self._spins: list[QtWidgets.QDoubleSpinBox] = []

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spins = []

        for axis, item in zip('XYZW', stored):
            spin = QtWidgets.QDoubleSpinBox(widget)
            spin.setPrefix(f'{axis}: ')
            spin.setDecimals(self._decimals)
            spin.setRange(self._low, self._high)
            spin.setSingleStep(self._step)
            spin.setValue(float(item))

            layout.addWidget(spin)
            self._spins.append(spin)

        return widget

    @_check_types.do
    def _read(self) -> list[float]:
        return [spin.value() for spin in self._spins]


class ColorField(Field):

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = ColorButton(parent, stored)

        return self._widget

    @_check_types.do
    def _read(self) -> list[float]:
        return self._widget.GetValue()


class ChoiceField(Field):
    """A drop down. *choices* are ``(label, value)`` pairs; a stored value
    that is not among them is added as its own entry so opening the dialog
    and pressing OK never replaces it."""

    @_check_types.do
    def __init__(self, path: str, name: str, label: str,
                 choices: list[tuple[str, Any]], restart: bool = False):
        super().__init__(path, name, label, restart)
        self._choices = choices

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = QtWidgets.QComboBox(parent)

        for text, value in self._choices:
            self._widget.addItem(text, value)

        index = self._widget.findData(stored)
        if index < 0:
            self._widget.addItem(str(stored), stored)
            index = self._widget.count() - 1

        self._widget.setCurrentIndex(index)

        return self._widget

    @_check_types.do
    def _read(self) -> Any:
        return self._widget.currentData()


class TextField(Field):

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        self._widget = QtWidgets.QLineEdit(parent)
        self._widget.setText(str(stored))

        return self._widget

    @_check_types.do
    def _read(self) -> str:
        return self._widget.text()


class PathField(Field):
    """A path in a text box with a Browse button (a folder, or a file)."""

    @_check_types.do
    def __init__(self, path: str, name: str, label: str, directory: bool = True,
                 restart: bool = False):
        super().__init__(path, name, label, restart)
        self._directory = directory

    @_check_types.do
    def _create(self, parent: QtWidgets.QWidget, stored: Any) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget(parent)
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QtWidgets.QLineEdit(widget)
        self._edit.setText(str(stored))

        browse = QtWidgets.QPushButton('Browse...', widget)
        browse.clicked.connect(self._browse)

        layout.addWidget(self._edit, 1)
        layout.addWidget(browse)

        return widget

    @_check_types.do
    def _browse(self) -> None:
        if self._directory:
            chosen = QtWidgets.QFileDialog.getExistingDirectory(
                self._edit, self.label, self._edit.text())
        else:
            chosen, _ = QtWidgets.QFileDialog.getSaveFileName(
                self._edit, self.label, self._edit.text())

        if chosen:
            self._edit.setText(chosen)

    @_check_types.do
    def _read(self) -> str:
        return self._edit.text()


# Short builders the pages are written with. Every one takes the section path
# and the setting name first, as string literals: tools/checks that verify the
# pages against ``config.py`` rely on that.

@_check_types.do
def boolean(path: str, name: str, label: str, restart: bool = False) -> BoolField:
    return BoolField(path, name, label, restart)


@_check_types.do
def integer(path: str, name: str, label: str, low: int, high: int,
            restart: bool = False) -> IntField:
    return IntField(path, name, label, low, high, restart)


@_check_types.do
def real(path: str, name: str, label: str, low: float, high: float,
         step: float = 0.1, decimals: int = 3, restart: bool = False) -> FloatField:
    return FloatField(path, name, label, low, high, step, decimals, restart)


@_check_types.do
def vector(path: str, name: str, label: str, low: float, high: float,
           step: float = 1.0, decimals: int = 2, restart: bool = False) -> VectorField:
    return VectorField(path, name, label, low, high, step, decimals, restart)


@_check_types.do
def color(path: str, name: str, label: str, restart: bool = False) -> ColorField:
    return ColorField(path, name, label, restart)


@_check_types.do
def choice(path: str, name: str, label: str, choices: list[tuple[str, Any]],
           restart: bool = False) -> ChoiceField:
    return ChoiceField(path, name, label, choices, restart)


@_check_types.do
def text(path: str, name: str, label: str, restart: bool = False) -> TextField:
    return TextField(path, name, label, restart)


@_check_types.do
def folder(path: str, name: str, label: str, restart: bool = False) -> PathField:
    return PathField(path, name, label, True, restart)


@_check_types.do
def file(path: str, name: str, label: str, restart: bool = False) -> PathField:
    return PathField(path, name, label, False, restart)
