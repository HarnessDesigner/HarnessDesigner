from PySide6 import QtWidgets
from PySide6 import QtCore

from .autocomplete_combobox import AutoCompleteComboBox


class ComboBoxCtrl(QtWidgets.QWidget):
    """
    Label + autocomplete combobox composite widget.

    Replaces the wx.BoxSizer-based ComboBoxCtrl.  The widget emits
    currentTextChanged from the inner AutoCompleteComboBox for all selection
    and enter-key commits; call sites should connect to that signal instead of
    binding EVT_COMBOBOX.
    """

    def __init__(self, parent=None, label: str = '', choices=None,
                 process_enter: bool = False):
        """Initialise the :class:`ComboBoxCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        :param process_enter: Value for ``process_enter``.
        :type process_enter: bool
        """
        super().__init__(parent)
        self.process_enter = process_enter

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QtWidgets.QLabel(label, self)
        self.ctrl = AutoCompleteComboBox(self, choices=choices or [])

        layout.addWidget(self.st, 0)
        layout.addWidget(self.ctrl, 1)

        # Enter key in the line edit commits the value
        # by firing currentTextChanged
        self.ctrl.lineEdit().returnPressed.connect(self._on_enter)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_enter(self):
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        # Normalise: if the typed text matches an item, select it so
        # currentIndex is consistent.
        text = self.ctrl.currentText()
        idx = self.ctrl.findText(text, QtCore.Qt.MatchFlag.MatchFixedString)
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
        """Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    SetToolTipString = SetToolTip

    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self.ctrl.SetValue(value)

    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.ctrl.GetValue()

    def Clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.ctrl.Clear()

    def Delete(self, n: int):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param n: Value for ``n``.
        :type n: int
        """
        self.ctrl.Delete(n)

    def Insert(self, item: str, pos: int, clientData=None):
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        :param clientData: Value for ``clientData``.
        :type clientData: UNKNOWN
        """
        self.ctrl.Insert(item, pos, clientData)

    def Set(self, items):
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.ctrl.Set(items)

    def GetItems(self) -> list[str]:
        """Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list[str]
        """
        return self.ctrl.GetItems()

    def SetItems(self, items: list[str]):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: list[str]
        """
        self.ctrl.SetItems(items)

    def AppendItems(self, items):
        """Execute the append items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.ctrl.AppendItems(items)

    def Append(self, item):
        """Execute the append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.ctrl.Append(item)

    # Convenience: expose the inner combobox signal so callers can do
    # combobox_ctrl.currentTextChanged.connect(handler)
    @property
    def currentTextChanged(self):
        """Return the current text changed.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.ctrl.currentTextChanged
