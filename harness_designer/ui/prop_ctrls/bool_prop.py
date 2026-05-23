# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QCheckBox, QLabel, QHBoxLayout

from . import prop_base as _prop_base


class BoolProperty(_prop_base.Property):
    """Represent a bool property in :mod:`harness_designer.ui.prop_ctrls.bool_prop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label):
        """Initialise the :class:`BoolProperty` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        _prop_base.Property.__init__(self, parent, label)
        self._value = False

        row = QHBoxLayout()
        row.setContentsMargins(5, 2, 5, 2)
        self._st = QLabel(label + ':', self)
        self._ctrl = QCheckBox('', self)

        row.addWidget(self._st)
        row.addWidget(self._ctrl)
        row.addStretch(1)
        self._sizer.addLayout(row)

        self._ctrl.checkStateChanged.connect(self._on_change)

    def _on_change(self, _):
        """Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        value = self._ctrl.isChecked()
        if value == self._value:
            return
        self._value = value
        self._send_changed_event(bool, value)

    def SetValue(self, value: bool):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._value = value
        self._ctrl.blockSignals(True)
        self._ctrl.setChecked(value)
        self._ctrl.blockSignals(False)

    def GetValue(self) -> bool:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self._ctrl.isChecked()
