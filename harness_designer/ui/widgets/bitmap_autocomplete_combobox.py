# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui
from ... import check_types as _check_types


class BitmapAutoCompleteComboBox(QtWidgets.QComboBox):
    """
    Editable, icon-bearing combobox with inline autocomplete.

    Replaces wx.adv.BitmapComboBox + AutoCompleter.  Each item is a
    (label: str, pixmap: QPixmap, tooltip: str) tuple, matching the original
    wx API where the third argument was clientData used as a tooltip.

    Signals
    -------
    currentTextChanged  — fired on selection or Enter (replaces EVT_COMBOBOX +
                         EVT_TEXT_ENTER).  Connect to this instead.
    """

    @_check_types.do
    def __init__(self, parent=None, choices=None):
        """Initialise the :class:`BitmapAutoCompleteComboBox` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)

        self._choices: list[tuple[str, QtGui.QPixmap | None, str | None]] = []
        self._ac_labels: list[str] = []

        self._completer = QtWidgets.QCompleter([], self)
        self._completer.setCaseSensitivity(
            QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self._completer.setCompletionMode(
            QtWidgets.QCompleter.CompletionMode.InlineCompletion)

        self.lineEdit().setCompleter(self._completer)

        self.currentIndexChanged.connect(self._on_index_changed)
        self.lineEdit().returnPressed.connect(self._on_enter)

        for item in (choices or []):
            self.Append(*item)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @_check_types.do
    def _rebuild_completer(self):
        """Execute the rebuild completer operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._completer.setModel(
            QtCore.QStringListModel(self._ac_labels, self._completer))

    @_check_types.do
    def _on_index_changed(self, index: int):
        """Handle the index changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: int
        """
        if 0 <= index < len(self._choices):
            tooltip = self._choices[index][2]
            if tooltip:
                self.setToolTip(tooltip)

    @_check_types.do
    def _on_enter(self):
        """Handle the enter event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        index = self.currentIndex()
        if 0 <= index < len(self._choices):
            tooltip = self._choices[index][2]
            if tooltip:
                self.setToolTip(tooltip)

    # ------------------------------------------------------------------
    # wx-compatible item management
    # ------------------------------------------------------------------
    @_check_types.do
    def Clear(self):
        """Execute the clear operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        super().clear()
        self._choices.clear()
        self._ac_labels.clear()
        self._rebuild_completer()

    @_check_types.do
    def Delete(self, n: int):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param n: Value for ``n``.
        :type n: int
        """
        self.removeItem(n)
        self._choices.pop(n)
        self._ac_labels.pop(n)
        self._rebuild_completer()

    @_check_types.do
    def Insert(self, item: str, bitmap=None, pos: int = 0, clientData=None):
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param bitmap: Value for ``bitmap``.
        :type bitmap: UNKNOWN
        :param pos: Value for ``pos``.
        :type pos: int
        :param clientData: Value for ``clientData``.
        :type clientData: UNKNOWN
        """
        pixmap = bitmap if isinstance(bitmap, QtGui.QPixmap) else None
        icon = QtGui.QIcon(pixmap) if pixmap else QtGui.QIcon()
        self.insertItem(pos, icon, item)
        self._choices.insert(pos, (item, pixmap, clientData))
        self._ac_labels.insert(pos, item)
        self._rebuild_completer()

    @_check_types.do
    def Set(self, items):
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Clear()
        for entry in items:
            self.Append(*entry)

    @_check_types.do
    def SetItems(self, items):
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: UNKNOWN
        """
        self.Set(items)

    @_check_types.do
    def Append(self, item: str, bitmap=None, clientData=None):
        """Execute the append operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param bitmap: Value for ``bitmap``.
        :type bitmap: UNKNOWN
        :param clientData: Value for ``clientData``.
        :type clientData: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        pixmap = bitmap if isinstance(bitmap, QtGui.QPixmap) else None
        icon = QtGui.QIcon(pixmap) if pixmap else QtGui.QIcon()
        super().addItem(icon, item)
        self._choices.append((item, pixmap, clientData))
        self._ac_labels.append(item)
        self._rebuild_completer()
        return self.count() - 1

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    @_check_types.do
    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.currentText()

    @_check_types.do
    def SetValue(self, value: str):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        idx = self.findText(value, QtCore.Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.lineEdit().setText(value)

    @_check_types.do
    def GetItems(self) -> list[str]:
        """Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list[str]
        """
        return self._ac_labels[:]

    @_check_types.do
    def GetClientData(self, n: int):
        """Return the tooltip/clientData stored with item n."""
        if 0 <= n < len(self._choices):
            return self._choices[n][2]
        return None

    @_check_types.do
    def GetSelection(self) -> int:
        """Execute the get selection operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        return self.currentIndex()
