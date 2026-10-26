# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The right-hand information pane: what is known about the wire selected in
the cross-section.

An enlarged drawing of the selected wire on top, then its colour, size, part
number, length (straight, and calculated along its helix), the current through
it and its approximate maximum temperature. Everything comes in as plain
:class:`.section_model.WireDetail` values; nothing here reads the database.
"""

import math

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from . import section_model as _section_model
from . import wire_painter as _wire_painter
from ..widgets import wrap_label as _wrap_label
from ... import check_types as _check_types


_FEET_PER_METRE = 3.28084
_NOT_AVAILABLE = 'not available'

# the one fixed colour: a warning has to read as one on any theme
_WARNING_STYLE = 'color: rgb(220, 70, 50);'


class CablePreview(QtWidgets.QWidget):
    """A large drawing of the one selected cable, centred."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        self._cable: _section_model.CableSpec | None = None
        self.setMinimumHeight(90)

    @_check_types.do
    def set_cable(self, cable: _section_model.CableSpec | None) -> None:
        self._cable = cable
        self.update()

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if self._cable is None:
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        scale = min(self.width(), self.height()) / (2.0 * self._cable.radius_mm * 1.15)
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(scale, scale)
        _wire_painter.paint_cable(painter, self._cable, 0.0)
        painter.end()


@_check_types.do
def format_length(length_mm: float) -> str:
    """``mm  /  m  /  ft``, the way the circuit editor shows a wire's length."""
    metres = length_mm / 1000.0
    return f'{length_mm:.1f} mm  /  {metres:.4f} m  /  {metres * _FEET_PER_METRE:.4f} ft'


@_check_types.do
def format_current(current_a: float | None) -> str:
    if current_a is None:
        return _NOT_AVAILABLE

    return f'{abs(current_a):.3f} A'


@_check_types.do
def format_temperature(max_temp_c: float | None, over_temp: bool, runaway: bool) -> str:
    if max_temp_c is None:
        return _NOT_AVAILABLE

    text = f'{max_temp_c:.0f} °C'
    if runaway:
        text += '  (thermal runaway)'
    elif over_temp:
        text += '  (over its rating)'

    return text


class WireInfoPanel(QtWidgets.QWidget):
    """The pane itself. :meth:`show_wire` fills it, :meth:`clear` empties it."""

    # what matters most first (colour, size, part number, calculated length,
    # current, temperature), the construction details after it
    _FIELDS = (
        ('part', 'Part:'), ('color', 'Color:'), ('size', 'Size:'), ('helix', 'Wire length (helix):'),
        ('current', 'Current:'), ('temperature', 'Max temperature:'), ('straight', 'Run length:'),
        ('layer', 'Layer / lay:'), ('conductor', 'Conductor:'), ('insulation', 'Insulation:'),
        ('od', 'OD:'), ('conductors', 'Conductors:'),
    )

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)

        # The content sits in a scroll area: a QSplitter does not pass
        # height-for-width on to its panes, so wrapped values would be clipped
        # to one line; a scroll area gives wrapped text the height it needs
        # (and scrolls if there is more than fits).
        content = QtWidgets.QWidget()
        inner = QtWidgets.QVBoxLayout(content)
        inner.setContentsMargins(6, 6, 6, 6)

        self._title = _wrap_label.WrapLabel('Select a wire', content)
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)

        self._preview = CablePreview(content)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.RowWrapPolicy.WrapLongRows)

        self._values: dict[str, _wrap_label.WrapLabel] = {}
        for field_key, caption in self._FIELDS:
            value = _wrap_label.WrapLabel('', content)
            self._values[field_key] = value
            form.addRow(caption, value)

        inner.addWidget(self._title)
        inner.addWidget(self._preview)
        inner.addLayout(form)
        inner.addStretch(1)

        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    @_check_types.do
    def clear(self) -> None:
        """Nothing selected."""
        self._title.setText('Select a wire')
        self._preview.set_cable(None)

        for value in self._values.values():
            value.setText('')
            value.setStyleSheet('')

    @_check_types.do
    def show_wire(self, detail: _section_model.WireDetail, cable: _section_model.CableSpec,
                  straight_length_mm: float, helix_length_mm: float) -> None:
        """Fill the pane for one wire.

        :param detail: What is known about the wire.
        :param cable: The wire as drawn (for the enlarged picture and its OD).
        :param straight_length_mm: The length of bundle it runs through.
        :param helix_length_mm: The wire's own length following its helix.
        """
        self._title.setText(detail.name or 'Wire')
        self._preview.set_cable(cable)

        color = detail.color or 'unknown'
        if detail.stripe_color:
            color += f', stripe {detail.stripe_color}'

        conductors = f'{detail.conductors}'
        if detail.shielded:
            conductors += ' (shielded)'

        layer = detail.layer or 'unknown'
        if detail.lay_direction:
            layer += f', {detail.lay_direction}'

        straight = format_length(straight_length_mm)
        helix = format_length(helix_length_mm)
        if straight_length_mm > 0.0:
            growth = (helix_length_mm / straight_length_mm - 1.0) * 100.0
            helix += f'  (+{growth:.1f}%)'

        values = self._values
        values['part'].setText(detail.part_number or 'unknown')
        values['color'].setText(color)
        values['size'].setText(detail.size or 'unknown')
        values['conductor'].setText(detail.conductor_material or 'unknown')
        values['insulation'].setText(detail.insulation or 'unknown')
        values['od'].setText(f'{cable.od_mm:.2f} mm')
        values['conductors'].setText(conductors)
        values['layer'].setText(layer)
        values['straight'].setText(straight)
        values['helix'].setText(helix)
        values['current'].setText(format_current(detail.current_a))
        values['temperature'].setText(
            format_temperature(detail.max_temp_c, detail.over_temp, detail.runaway))

        values['temperature'].setStyleSheet('')
        if detail.over_temp or detail.runaway:
            values['temperature'].setStyleSheet(_WARNING_STYLE)
