from PySide6.QtWidgets import QLineEdit, QCompleter
from PySide6.QtCore import Qt, QStringListModel


class AutoCompleteTextCtrl(QLineEdit):
    """QLineEdit with inline autocomplete (replaces wx AutoCompleteTextCtrl).

    Choice-management API is identical to the original so all call sites work
    without modification.
    """

    def __init__(self, parent=None, choices=None):
        super().__init__(parent)
        self._choices = list(choices or [])
        self._completer = QCompleter(self._choices, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.InlineCompletion)
        self.setCompleter(self._completer)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------
    def _rebuild_completer(self):
        self._completer.setModel(QStringListModel(self._choices, self._completer))

    # ------------------------------------------------------------------
    # wx-compatible choice management
    # ------------------------------------------------------------------
    def Clear(self):
        self._choices.clear()
        self._rebuild_completer()

    def Delete(self, n: int):
        self._choices.pop(n)
        self._rebuild_completer()

    def Insert(self, item: str, pos: int):
        self._choices.insert(pos, item)
        self._rebuild_completer()

    def Set(self, items):
        self._choices = list(items)
        self._rebuild_completer()

    def SetItems(self, items):
        self.Set(items)

    def Append(self, item):
        if isinstance(item, list):
            self._choices.extend(item)
        else:
            self._choices.append(item)
        self._rebuild_completer()

    # ------------------------------------------------------------------
    # Value access (QLineEdit already provides text()/setText())
    # ------------------------------------------------------------------
    def SetValue(self, value: str):
        # ChangeValue equivalent: set without triggering textEdited
        self.blockSignals(True)
        self.setText(value)
        self.blockSignals(False)

    def GetValue(self) -> str:
        return self.text()
