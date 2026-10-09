# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtCore, QtWidgets
from PySide6 import QtCore
from ... import check_types as _check_types


class _AutoCompleter:
    """Pure-Python autocomplete state machine, shared by all widget wrappers."""

    @_check_types.do
    def __init__(self, choices: list[str]) -> None:
        """Initialise the :class:`_AutoCompleter` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices = list(choices)

    @_check_types.do
    def SetChoices(self, choices: list[str]) -> None:
        """Execute the set choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices = list(choices)

    @_check_types.do
    def GetChoices(self) -> list[str]:
        """Execute the get choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.choices[:]

    @_check_types.do
    def AppendChoices(self, choices: list[str]) -> None:
        """Execute the append choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self.choices.extend(choices)

    @_check_types.do
    def InsertChoice(self, item: str, pos: int) -> None:
        """Execute the insert choice operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: str
        :param pos: Value for ``pos``.
        :type pos: int
        """
        self.choices.insert(pos, item)

    @_check_types.do
    def RemoveChoice(self, pos: int) -> None:
        """Execute the remove choice operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: int
        """
        self.choices.pop(pos)


@_check_types.do
def _attach_completer(widget: QtWidgets.QLineEdit, ac: _AutoCompleter) -> QtWidgets.QCompleter:
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


@_check_types.do
def _refresh_completer(widget: QtWidgets.QLineEdit, ac: _AutoCompleter) -> None:
    """Rebuild the completer model from the current choices list."""
    completer = widget.completer()
    if completer is None:
        _attach_completer(widget, ac)
    else:
        completer.setModel(QtCore.QStringListModel(ac.choices, completer))


class AutoComplete(QtWidgets.QLineEdit):
    """
    QLineEdit with inline autocomplete (replaces the wx AutoComplete TextCtrl).
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None, value: str = '', autocomplete_choices: list[str] | None = None) -> None:
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

    @_check_types.do
    def SetAutoCompleteChoices(self, choices: list[str]) -> None:
        """Execute the set auto complete choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param choices: Value for ``choices``.
        :type choices: UNKNOWN
        """
        self._ac.SetChoices(choices)
        _refresh_completer(self, self._ac)

    @_check_types.do
    def GetAutoCompleteChoices(self) -> list[str]:
        """Execute the get auto complete choices operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._ac.GetChoices()
