# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import checkbox_ctrl as _checkbox_ctrl


class StippleEditor(QtWidgets.QWidget):
    """Row of 32 toggle squares representing a uint32 stipple pattern.

    Square 0 (leftmost) = bit 0 (LSB) = first 1/32 of each tile-length
    segment in the floor shader.  Squares are grouped into four bytes
    of eight for readability.

    Interactions
    ────────────
    Left-click          Toggle a single square.
    Left-click-and-drag Paint a run of squares to the same state as the
                        first square clicked (on → off, or off → on).
    """
    # emits the current uint32 on every change
    valueChanged: QtCore.SignalInstance = QtCore.Signal(int)

    # ── appearance ────────────────────────────────────────────────────────────

    # lit square fill
    _C_ON = QtGui.QColor(45,  45,  45)

    # unlit square fill
    _C_OFF = QtGui.QColor(210, 210, 210)

    # square outline
    _C_BORDER = QtGui.QColor(255,  80,  80)

    # widget background
    _C_BG = QtGui.QColor(28,  28,  28)

    def __init__(self, value: int = 0, parent: QtWidgets.QWidget = None):
        super().__init__(parent)

        self._value = int(value) & 0xFFFFFFFF

        # True = painting ON, False = painting OFF
        self._drag_on = None

    # ── public API ────────────────────────────────────────────────────────────
    def GetValue(self) -> int:
        """Current uint32 stipple pattern value."""
        return self._value

    def SetValue(self, v: int):
        v = int(v) & 0xFFFFFFFF
        if v != self._value:
            self._value = v
            self.update()
            self.valueChanged.emit(self._value)

    # ── geometry ──────────────────────────────────────────────────────────────
    def _rect(self, i: int) -> QtCore.QRect:
        """Return the bounding QRect of square i."""
        size = self.size()

        w = size.width()
        h = size.height()

        f_steps = w / 32.0
        steps = int(f_steps)
        i_steps = steps * 32

        pad = int((w - i_steps) / 2.0)

        x = pad * (i + 1)
        y = pad

        h -= int(pad * 2)

        return QtCore.QRect(x, y, steps, h)

    def _index_at(self, pt: QtCore.QPoint) -> int:
        """
        Return the bit index under pt, or -1 if pt is not inside any square.
        """
        for i in range(32):
            if self._rect(i).contains(pt):
                return i

        return -1

    # ── bit helpers ───────────────────────────────────────────────────────────
    def _bit(self, i: int) -> bool:
        return bool(self._value & (1 << i))

    def _set_bit(self, i: int, on: bool):
        if on:
            self._value |= (1 << i)
        else:
            self._value &= ~(1 << i)
        self._value &= 0xFFFFFFFF
        self.update()
        self.valueChanged.emit(self._value)

    # ── mouse events ──────────────────────────────────────────────────────────
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            i = self._index_at(event.position().toPoint())
            if i >= 0:
                # paint state is the opposite of whatever was clicked
                self._drag_on = not self._bit(i)
                self._set_bit(i, self._drag_on)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_on is not None:
            i = self._index_at(event.position().toPoint())
            if i >= 0:
                self._set_bit(i, self._drag_on)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_on = None

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        pen = QtGui.QPen(self._C_BORDER, 1)

        p.fillRect(self.rect(), self._C_BG)

        for i in range(32):
            r = self._rect(i)
            p.fillRect(r, self._C_ON if self._bit(i) else self._C_OFF)
            p.setPen(pen)
            p.drawRect(r)

        p.end()


class StippleCtrl(QtWidgets.QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        sizer = QtWidgets.QVBoxLayout(self)
        sizer.setContentsMargins(0, 0, 0, 0)

        self.stipple_ctrl = StippleEditor(self)
        self.offset_ctrl = _checkbox_ctrl.CheckboxCtrl(
            self, 'Shift Odd Lines:')

        self.offset_ctrl.SetValue(False)

        sizer.addWidget(self.stipple_ctrl, 1)
        sizer.addWidget(self.offset_ctrl)

    def SetValue(self, pattern: int, offset: bool) -> None:
        self.stipple_ctrl.SetValue(pattern)
        self.offset_ctrl.SetValue(offset)

    def GetValue(self) -> tuple[int, bool]:
        return self.stipple_ctrl.GetValue(), self.offset_ctrl.GetValue()



