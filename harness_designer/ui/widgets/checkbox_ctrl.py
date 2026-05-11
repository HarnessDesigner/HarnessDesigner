from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox


class CheckboxCtrl(QWidget):
    """Label + checkbox composite widget.

    The original was a wx.BoxSizer subclass, which made it behave like a
    layout object.  In Qt the composite is a proper QWidget so it can be
    inserted into any layout with addWidget().  All public methods from the
    original are preserved.
    """

    def __init__(self, parent=None, label: str = ''):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QLabel(label, self)
        self.ctrl = QCheckBox(self)

        layout.addWidget(self.st, 1)
        layout.addWidget(self.ctrl, 1)

    # ------------------------------------------------------------------
    # wx-compatible API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    # kept for call-site compatibility
    SetToolTipString = SetToolTip

    def SetValue(self, value: bool):
        self.ctrl.blockSignals(True)
        self.ctrl.setChecked(value)
        self.ctrl.blockSignals(False)

    def GetValue(self) -> bool:
        return self.ctrl.isChecked()

    # Expose the inner checkbox's signals so callers can do
    # ctrl.ctrl.checkStateChanged.connect(handler) or use the
    # convenience property below.
    @property
    def checkStateChanged(self):
        return self.ctrl.checkStateChanged
