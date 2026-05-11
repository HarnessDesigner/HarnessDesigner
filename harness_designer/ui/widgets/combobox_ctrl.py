from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from .autocomplete_combobox import AutoCompleteComboBox


class ComboBoxCtrl(QWidget):
    """Label + autocomplete combobox composite widget.

    Replaces the wx.BoxSizer-based ComboBoxCtrl.  The widget emits
    currentTextChanged from the inner AutoCompleteComboBox for all selection
    and enter-key commits; call sites should connect to that signal instead of
    binding EVT_COMBOBOX.
    """

    def __init__(self, parent=None, label: str = '', choices=None,
                 process_enter: bool = False):
        super().__init__(parent)
        self.process_enter = process_enter

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QLabel(label, self)
        self.ctrl = AutoCompleteComboBox(self, choices=choices or [])

        layout.addWidget(self.st, 0)
        layout.addWidget(self.ctrl, 1)

        # Enter key in the line edit commits the value by firing currentTextChanged
        self.ctrl.lineEdit().returnPressed.connect(self._on_enter)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_enter(self):
        # Normalise: if the typed text matches an item, select it so
        # currentIndex is consistent.
        text = self.ctrl.currentText()
        idx = self.ctrl.findText(text, Qt.MatchFixedString)
        if idx >= 0:
            self.ctrl.blockSignals(True)
            self.ctrl.setCurrentIndex(idx)
            self.ctrl.blockSignals(False)
        # Emit the signal so downstream handlers fire on Enter just as they
        # did with EVT_COMBOBOX in the original.
        self.ctrl.currentTextChanged.emit(text)

    # ------------------------------------------------------------------
    # wx-compatible API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    SetToolTipString = SetToolTip

    def SetValue(self, value: str):
        self.ctrl.SetValue(value)

    def GetValue(self) -> str:
        return self.ctrl.GetValue()

    def Clear(self):
        self.ctrl.Clear()

    def Delete(self, n: int):
        self.ctrl.Delete(n)

    def Insert(self, item: str, pos: int, clientData=None):
        self.ctrl.Insert(item, pos, clientData)

    def Set(self, items):
        self.ctrl.Set(items)

    def GetItems(self) -> list[str]:
        return self.ctrl.GetItems()

    def SetItems(self, items: list[str]):
        self.ctrl.SetItems(items)

    def AppendItems(self, items):
        self.ctrl.AppendItems(items)

    def Append(self, item):
        return self.ctrl.Append(item)

    # Convenience: expose the inner combobox signal so callers can do
    # combobox_ctrl.currentTextChanged.connect(handler)
    @property
    def currentTextChanged(self):
        return self.ctrl.currentTextChanged
