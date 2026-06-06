# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore


class _AutoCompleter:
    """Pure-Python autocomplete state machine, shared by all widget wrappers."""

    def __init__(self, choices):
        """Initialise the :class:`_AutoCompleter` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices = list(choices)

    def SetChoices(self, choices):
        """Execute the set choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices = list(choices)

    def GetChoices(self):
        """Execute the get choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.choices[:]

    def AppendChoices(self, choices):
        """Execute the append choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices.extend(choices)

    def InsertChoice(self, item: str, pos: int):
        """Execute the insert choice operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        """
        self.choices.insert(pos, item)

    def RemoveChoice(self, pos: int):
        """Execute the remove choice operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: int
        """
        self.choices.pop(pos)


def _attach_completer(widget, ac: _AutoCompleter):
    """
    Create and attach a QCompleter to *widget*, returning it so callers can
    refresh it when the choices list changes.
    """
    completer = QtWidgets.QCompleter(ac.choices, widget)
    completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

    completer.setCompletionMode(
        QtWidgets.QCompleter.CompletionMode.InlineCompletion)

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


class AutoComplete(QtWidgets.QLineEdit):
    """
    QLineEdit with inline autocomplete (replaces the wx AutoComplete TextCtrl).
    """

    def __init__(self, parent=None, value='', autocomplete_choices=None):
        """Initialise the :class:`AutoComplete` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param value: Value to store or process.
        :type value: UNKNOWN
        :param autocomplete_choices: Value for ``autocomplete_choices``.
        :type autocomplete_choices: UNKNOWN
        """
        super().__init__(parent)
        self.setText(value)
        self._ac = _AutoCompleter(autocomplete_choices or [])
        _attach_completer(self, self._ac)

    def SetAutoCompleteChoices(self, choices):
        """Execute the set auto complete choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self._ac.SetChoices(choices)
        _refresh_completer(self, self._ac)

    def GetAutoCompleteChoices(self):
        """Execute the get auto complete choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ac.GetChoices()
