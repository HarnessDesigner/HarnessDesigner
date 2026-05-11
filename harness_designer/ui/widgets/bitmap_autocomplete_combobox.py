from PySide6.QtWidgets import QComboBox, QCompleter
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QIcon, QPixmap


class BitmapAutoCompleteComboBox(QComboBox):
    """Editable, icon-bearing combobox with inline autocomplete.

    Replaces wx.adv.BitmapComboBox + AutoCompleter.  Each item is a
    (label: str, pixmap: QPixmap, tooltip: str) tuple, matching the original
    wx API where the third argument was clientData used as a tooltip.

    Signals
    -------
    currentTextChanged  — fired on selection or Enter (replaces EVT_COMBOBOX +
                         EVT_TEXT_ENTER).  Connect to this instead.
    """

    def __init__(self, parent=None, choices=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)

        self._choices: list[tuple[str, QPixmap | None, str | None]] = []
        self._ac_labels: list[str] = []

        self._completer = QCompleter([], self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.InlineCompletion)
        self.lineEdit().setCompleter(self._completer)

        self.currentIndexChanged.connect(self._on_index_changed)
        self.lineEdit().returnPressed.connect(self._on_enter)

        for item in (choices or []):
            self.Append(*item)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rebuild_completer(self):
        self._completer.setModel(QStringListModel(self._ac_labels, self._completer))

    def _on_index_changed(self, index: int):
        if 0 <= index < len(self._choices):
            tooltip = self._choices[index][2]
            if tooltip:
                self.setToolTip(tooltip)

    def _on_enter(self):
        index = self.currentIndex()
        if 0 <= index < len(self._choices):
            tooltip = self._choices[index][2]
            if tooltip:
                self.setToolTip(tooltip)

    # ------------------------------------------------------------------
    # wx-compatible item management
    # ------------------------------------------------------------------
    def Clear(self):
        super().clear()
        self._choices.clear()
        self._ac_labels.clear()
        self._rebuild_completer()

    def Delete(self, n: int):
        self.removeItem(n)
        self._choices.pop(n)
        self._ac_labels.pop(n)
        self._rebuild_completer()

    def Insert(self, item: str, bitmap=None, pos: int = 0, clientData=None):
        pixmap = bitmap if isinstance(bitmap, QPixmap) else None
        icon = QIcon(pixmap) if pixmap else QIcon()
        self.insertItem(pos, icon, item)
        self._choices.insert(pos, (item, pixmap, clientData))
        self._ac_labels.insert(pos, item)
        self._rebuild_completer()

    def Set(self, items):
        self.Clear()
        for entry in items:
            self.Append(*entry)

    def SetItems(self, items):
        self.Set(items)

    def Append(self, item: str, bitmap=None, clientData=None):
        pixmap = bitmap if isinstance(bitmap, QPixmap) else None
        icon = QIcon(pixmap) if pixmap else QIcon()
        super().addItem(icon, item)
        self._choices.append((item, pixmap, clientData))
        self._ac_labels.append(item)
        self._rebuild_completer()
        return self.count() - 1

    # ------------------------------------------------------------------
    # Value access
    # ------------------------------------------------------------------
    def GetValue(self) -> str:
        return self.currentText()

    def SetValue(self, value: str):
        idx = self.findText(value, Qt.MatchFixedString)
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.lineEdit().setText(value)

    def GetItems(self) -> list[str]:
        return self._ac_labels[:]

    def GetClientData(self, n: int):
        """Return the tooltip/clientData stored with item n."""
        if 0 <= n < len(self._choices):
            return self._choices[n][2]
        return None

    def GetSelection(self) -> int:
        return self.currentIndex()
