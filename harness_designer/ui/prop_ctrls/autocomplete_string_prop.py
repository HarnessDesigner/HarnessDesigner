# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from ..widgets import autocomplete_textctrl as _autocomplete_textctrl
from . import events as _events
from ... import check_types as _check_types


class AutocompleteStringProperty(QtWidgets.QWidget):
    """Represent an autocomplete string property in :mod:`harness_designer.ui.prop_ctrls.autocomplete_string_prop`.

    Single-line (the default), ONE Enter commits and sends ``propertyChanged``. Constructed with ``multiline=True`` the first two
    Enters type newlines and the THIRD Enter in a row commits (see :class:`AutoCompleteTextEdit`), leaving a single newline at the
    end of the text. The Enter that commits is never added to the text, and no spaces are stripped: they matter to the completer.
    Each control has a tooltip that says how to save.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, label: str, style: int = 0, units: str | None = None,
                 multiline: bool = False):
        """
        Initialise the :class:`AutocompleteStringProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param style: Value for ``style``.
        :type style: UNKNOWN
        :param units: Value for ``units``.
        :type units: UNKNOWN
        :param multiline: Build a multi-line control, which needs three Enters in a row to commit.
        :type multiline: bool
        """
        self._choices = []
        self._value = ''
        self._multiline = multiline
        self._units_st = None
        self._label = label

        super().__init__(parent)

        self._st = QtWidgets.QLabel(label + ':', self)
        if multiline:
            self._ctrl = _autocomplete_textctrl.AutoCompleteTextEdit(self, choices=[])
            self._ctrl.setToolTip(
                f'Press Enter {_autocomplete_textctrl.AutoCompleteTextEdit.COMMIT_ENTERS} times to save')
        else:
            self._ctrl = _autocomplete_textctrl.AutoCompleteTextCtrl(self, choices=[])
            self._ctrl.setToolTip('Press Enter to save')

        if units is not None:
            self._units_st = QtWidgets.QLabel(units, self)

        sizer = QtWidgets.QHBoxLayout()
        sizer.setContentsMargins(5, 2, 5, 2)
        sizer.addWidget(self._st)

        col = QtWidgets.QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self._ctrl)
        sizer.addLayout(col, stretch=1)

        if self._units_st:
            sizer.addWidget(
                self._units_st, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        self.setLayout(sizer)
        self._ctrl.returnPressed.connect(self._on_enter)

    @_check_types.do
    def GetValue(self) -> str:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._value

    @_check_types.do
    def SetValue(self, value: str) -> None:
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._value = value
        self._ctrl.SetValue(value)

    @_check_types.do
    def SetItems(self, items: list) -> None:
        """Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: list
        """
        self._choices = list(items)
        if self._ctrl is not None:
            self._ctrl.SetItems(self._choices)

    @_check_types.do
    def _on_enter(self) -> None:
        """Commit the text when the control reports its Enter.

        The control decides which Enter commits: the single-line control reports every Enter, the multi-line one only the
        third in a row (and has already cut its trailing newlines to one). The text is sent exactly as the control holds it,
        with no spaces stripped. A new single-line value is added to the choices; a multi-line text is not, because the completer
        matches one line at a time and a whole earlier text is a bad completion for it.
        """
        text = self._ctrl.GetValue()
        self._value = text

        if text and not self._multiline and text not in self._choices:
            self._choices.append(text)
            self._ctrl.SetItems(self._choices)

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(str)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    @_check_types.do
    def SetLabel(self, value: str) -> None:
        self._label = value
        self._st.setText(value)

    @_check_types.do
    def GetLabel(self) -> str:
        return self._label
