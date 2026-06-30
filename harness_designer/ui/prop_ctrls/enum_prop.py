# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import events as _events


class EnumProperty(QtWidgets.QWidget):
    """
    Represent an enum property in
    :mod:`harness_designer.ui.prop_ctrls.enum_prop`.
    """

    propertyChanged: QtCore.SignalInstance = QtCore.Signal(object)

    def __init__(self, parent, label):
        """
        Initialise the :class:`EnumProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """

        super().__init__(parent)
        self._label = label

        self._choices = []
        self._value = 0
        self._labels = []
        self._button_group = None
        self._radio_box = None
        self._sizer = None
        self._label = label

        self._outer_sizer = QtWidgets.QVBoxLayout()
        self._outer_sizer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._outer_sizer)

    def _on_change(self, button_id: int) -> None:
        """
        Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param button_id: Identifier for the button.
        :type button_id: `int`
        """

        value = self._choices[button_id]
        if value == self._value:
            return

        self._value = value

        evt = _events.PropertyEvent()
        evt.SetValue(self._value)
        evt.SetPropertyType(int)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

    def SetValue(self, value: int) -> None:
        """
        Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: `int`
        """

        if value not in self._choices:
            return

        index = self._choices.index(value)
        self._value = value

        if self._button_group is not None:
            btn = self._button_group.button(index)
            if btn is not None:
                btn.blockSignals(True)

                btn.setChecked(True)

                btn.blockSignals(False)

    def GetValue(self) -> int:
        """
        Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: `int`
        """

        return self._value

    def Enable(self, flag: bool = True) -> None:
        """
        Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: `bool`
        """

        if self._radio_box is not None:
            self._radio_box.setEnabled(flag)

    def SetLabels(self, labels: list[str]) -> None:
        """
        Execute the set labels operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param labels: Value for ``labels``.
        :type labels: `list[str]`
        """

        self._labels = labels

        if self._radio_box is not None:
            self._outer_sizer.removeWidget(self._radio_box)
            self._radio_box.deleteLater()

        self._radio_box = QtWidgets.QGroupBox(self._label, self)
        self._sizer = QtWidgets.QVBoxLayout()
        self._sizer.setContentsMargins(4, 4, 4, 4)
        self._radio_box.setLayout(self._sizer)
        self._outer_sizer.addWidget(self._radio_box)

        bg = QtWidgets.QButtonGroup(self._radio_box)
        bg.setExclusive(True)

        rows = len(labels) // 3

        for i in range(rows):
            sizer = QtWidgets.QHBoxLayout()
            for j in range(3):
                index = j * (i + 1)
                lbl = labels[index]

                rb = QtWidgets.QRadioButton(lbl, self._radio_box)
                bg.addButton(rb, index)
                sizer.addWidget(rb)

            self._sizer.addLayout(sizer)

        bg.idClicked.connect(self._on_change)

        self._button_group = bg

        # Re-apply current selection
        if self._value in self._choices:
            index = self._choices.index(self._value)

            btn = bg.button(index)
            if btn is not None:
                btn.setChecked(True)


    def GetLabels(self) -> list[str]:
        """
        Execute the get labels operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: `list[str]`
        """

        return self._labels

    def GetItems(self) -> list[int]:
        """
        Execute the get items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: `list[int]`
        """

        return self._choices

    def SetItems(self, items: list[int]):
        """
        Execute the set items operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param items: Collection of items to process.
        :type items: `list[int]`
        """

        self._choices = items

    def SetLabel(self, value: str):
        self._label = value
        if self._radio_box is not None:
            self._radio_box.setTitle(value)

    def GetLabel(self) -> str:
        return self._label
