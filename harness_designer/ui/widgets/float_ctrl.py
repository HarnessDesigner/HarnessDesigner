from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QSlider
)
from PySide6.QtCore import Qt, Signal

try:
    from ... import utils as _utils
    from ...geometry.decimal import Decimal as _d
except ImportError:
    from decimal import Decimal as _d
    class _utils:
        @staticmethod
        def remap(value, in_min, in_max, out_min, out_max):
            span_in = in_max - in_min
            span_out = out_max - out_min
            if span_in == 0:
                return out_min
            return out_min + (value - in_min) * span_out / span_in


class FloatCtrl(QWidget):
    """Label + QDoubleSpinBox + optional QSlider composite widget.

    Replaces the wx.BoxSizer-based FloatCtrl.  Emits value_changed(float)
    whenever the spin or slider changes; call sites should connect to that
    signal instead of binding EVT_SPINCTRLDOUBLE.
    """

    value_changed = Signal(float)

    def __init__(self, parent=None, label: str = '',
                 min_val: float = 0.0, max_val: float = 100.0,
                 inc: float = 1.0, slider: bool = True):
        super().__init__(parent)

        self.__min_val = min_val
        self.__max_val = max_val
        self.__increment = inc

        # Determine decimal precision from increment
        precision = 0
        d_inc = _d(str(inc))
        while d_inc < 1:
            precision += 1
            d_inc *= _d('10')
        self.__precision = precision

        # Compute a sensible initial value (midpoint snapped to increment)
        value_range = _d(str(max_val)) - _d(str(min_val))
        middle = (value_range / _d('2')) + _d(str(min_val))
        d_inc = _d(str(inc))
        remaining = middle % d_inc
        if remaining:
            middle += d_inc - remaining
        initial = float(middle)

        # Slider scale
        if slider:
            s_inc = _d('10') * _d(str(precision))
            self.__s_max = int(_d('100') * s_inc)
        else:
            self.__s_max = 0

        # --- Build UI ---
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        self.st = QLabel(label, self)
        self.ctrl = QDoubleSpinBox(self)
        self.ctrl.setDecimals(precision)
        self.ctrl.setSingleStep(inc)
        self.ctrl.setRange(min_val, max_val)
        self.ctrl.setValue(initial)

        top.addWidget(self.st, 1)
        top.addWidget(self.ctrl, 1)
        outer.addLayout(top)

        if slider:
            slider_val = _utils.remap(middle, min_val, max_val, 0, self.__s_max)
            self.slider = QSlider(Qt.Horizontal, self)
            self.slider.setRange(0, self.__s_max)
            self.slider.setValue(int(slider_val))

            bottom = QHBoxLayout()
            bottom.addWidget(self.slider)
            outer.addLayout(bottom)

            self.slider.valueChanged.connect(self._on_slider)
            self.ctrl.valueChanged.connect(self._on_spin)
        else:
            self.slider = None
            self.ctrl.valueChanged.connect(self._on_spin)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_slider(self, slider_val: int):
        spin_value = _utils.remap(slider_val, 0, self.__s_max,
                                  self.__min_val, self.__max_val)
        d = _d(str(spin_value))
        d_inc = _d(str(self.__increment))
        remaining = d % d_inc
        if remaining:
            d += d_inc - remaining

        self.ctrl.blockSignals(True)
        self.ctrl.setValue(float(d))
        self.ctrl.blockSignals(False)
        self.value_changed.emit(float(d))

    def _on_spin(self, spin_value: float):
        if self.slider is not None:
            sv = _utils.remap(spin_value, self.__min_val, self.__max_val,
                              0, self.__s_max)
            self.slider.blockSignals(True)
            self.slider.setValue(int(sv))
            self.slider.blockSignals(False)
        self.value_changed.emit(spin_value)

    # ------------------------------------------------------------------
    # wx-compatible public API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)
        if self.slider is not None:
            self.slider.setEnabled(flag)

    def SetToolTip(self, text: str):
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)
        if self.slider is not None:
            self.slider.setToolTip(text)

    SetToolTipString = SetToolTip

    def SetValue(self, value: float):
        value = round(value, self.__precision)
        d = _d(str(value))
        d_inc = _d(str(self.__increment))
        remaining = d % d_inc
        if remaining:
            d += d_inc - remaining
        d = max(_d(str(self.__min_val)), min(_d(str(self.__max_val)), d))

        self.ctrl.blockSignals(True)
        self.ctrl.setValue(float(d))
        self.ctrl.blockSignals(False)

        if self.slider is not None:
            sv = _utils.remap(float(d), self.__min_val, self.__max_val,
                              0, self.__s_max)
            self.slider.blockSignals(True)
            self.slider.setValue(int(sv))
            self.slider.blockSignals(False)

    def GetValue(self) -> float:
        return self.ctrl.value()
