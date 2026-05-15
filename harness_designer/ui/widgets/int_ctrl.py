from PySide6 import QtWidgets
from PySide6 import QtCore


class IntCtrl(QtWidgets.QWidget):
    """Label + QSpinBox + optional QSlider composite widget.

    Replaces the wx.BoxSizer-based IntCtrl.  Emits value_changed(int) whenever
    the spin or slider changes.
    """

    value_changed: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, parent, label: str, min_val: int,
                 max_val: int, slider: bool = True):

        super().__init__(parent)

        self.__min_val = min_val
        self.__max_val = max_val

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        top = QtWidgets.QHBoxLayout()
        self.st = QtWidgets.QLabel(label, self)
        self.ctrl = QtWidgets.QSpinBox(self)
        self.ctrl.setRange(min_val, max_val)
        self.ctrl.setValue(max_val)

        top.addWidget(self.st, 1)
        top.addWidget(self.ctrl, 1)
        outer.addLayout(top)

        if slider:
            self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
            self.slider.setRange(min_val, max_val)
            self.slider.setValue(max_val)

            bottom = QtWidgets.QHBoxLayout()
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
    def _on_slider(self, value: int):
        self.ctrl.blockSignals(True)
        self.ctrl.setValue(value)
        self.ctrl.blockSignals(False)
        self.value_changed.emit(value)

    def _on_spin(self, value: int):
        if self.slider is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(value)
            self.slider.blockSignals(False)

        self.value_changed.emit(value)

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

    def SetValue(self, value: int):
        self.ctrl.blockSignals(True)
        self.ctrl.setValue(value)
        self.ctrl.blockSignals(False)

        if self.slider is not None:
            self.slider.blockSignals(True)
            self.slider.setValue(value)
            self.slider.blockSignals(False)

    def GetValue(self) -> int:
        return self.ctrl.value()
