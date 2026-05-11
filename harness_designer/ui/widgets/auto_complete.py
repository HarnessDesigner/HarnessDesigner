from PySide6.QtWidgets import QLineEdit, QCompleter
from PySide6.QtCore import Qt


class _AutoCompleter:
    """Pure-Python autocomplete state machine, shared by all widget wrappers."""

    def __init__(self, choices):
        self.choices = list(choices)

    def SetChoices(self, choices):
        self.choices = list(choices)

    def GetChoices(self):
        return self.choices[:]

    def AppendChoices(self, choices):
        self.choices.extend(choices)

    def InsertChoice(self, item: str, pos: int):
        self.choices.insert(pos, item)

    def RemoveChoice(self, pos: int):
        self.choices.pop(pos)


def _attach_completer(widget, ac: _AutoCompleter):
    """Create and attach a QCompleter to *widget*, returning it so callers can
    refresh it when the choices list changes."""
    completer = QCompleter(ac.choices, widget)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setCompletionMode(QCompleter.InlineCompletion)
    widget.setCompleter(completer)
    return completer


def _refresh_completer(widget, ac: _AutoCompleter):
    """Rebuild the completer model from the current choices list."""
    completer = widget.completer()
    if completer is None:
        _attach_completer(widget, ac)
    else:
        from PySide6.QtCore import QStringListModel
        completer.setModel(QStringListModel(ac.choices, completer))


class AutoComplete(QLineEdit):
    """QLineEdit with inline autocomplete (replaces the wx AutoComplete TextCtrl)."""

    def __init__(self, parent=None, value='', autocomplete_choices=None):
        super().__init__(parent)
        self.setText(value)
        self._ac = _AutoCompleter(autocomplete_choices or [])
        _attach_completer(self, self._ac)

    def SetAutoCompleteChoices(self, choices):
        self._ac.SetChoices(choices)
        _refresh_completer(self, self._ac)

    def GetAutoCompleteChoices(self):
        return self._ac.GetChoices()
