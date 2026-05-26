# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QHBoxLayout
from ..widgets import tri_state_checkbox_ctrl as _tri_state_checkbox_ctrl
from . import prop_base as _prop_base


class TriStateCheckboxProperty(_prop_base.Property):
    """
    Represent a 3 state checkbox property in :mod:`harness_designer.ui.prop_ctrls.tri_state_checkbox_prop`.
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

        self._ctrl = _tri_state_checkbox_ctrl.TriStateCheckboxCtrl(self, label + ':')
        row.addWidget(self._ctrl)
        row.addStretch(1)
        self._sizer.addLayout(row)

        self._ctrl.checkStateChanged.connect(self._on_change)

    def _on_change(self, value: bool | None):
        """Handle the change event.

        UNKNOWN details are inferred from the callable name and signature.

        :type value: bool | None
        """
        if value == self._value:
            return

        self._value = value
        self._send_changed_event(object, value)

    def SetValue(self, value: bool | None):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool | None
        """
        self._value = value
        self._ctrl.SetValue(value)

    def GetValue(self) -> bool | None:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool | None
        """
        return self._ctrl.GetValue()
