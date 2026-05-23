from PySide6 import QtWidgets


class CheckboxCtrl(QtWidgets.QWidget):
    """
    Label + checkbox composite widget.

    The original was a wx.BoxSizer subclass, which made it behave like a
    layout object.  In Qt the composite is a proper QWidget so it can be
    inserted into any layout with addWidget().  All public methods from the
    original are preserved.
    """

    def __init__(self, parent=None, label: str = ''):
        """Initialise the :class:`CheckboxCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        """
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.st = QtWidgets.QLabel(label, self)
        self.ctrl = QtWidgets.QCheckBox(self)

        layout.addWidget(self.st, 1)
        layout.addWidget(self.ctrl, 1)

    # ------------------------------------------------------------------
    # wx-compatible API
    # ------------------------------------------------------------------
    def Enable(self, flag: bool = True):
        """Execute the enable operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self.ctrl.setEnabled(flag)
        self.st.setEnabled(flag)

    def SetToolTip(self, text: str):
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: str
        """
        self.ctrl.setToolTip(text)
        self.st.setToolTip(text)

    # kept for call-site compatibility
    SetToolTipString = SetToolTip

    def SetValue(self, value: bool):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self.ctrl.blockSignals(True)
        self.ctrl.setChecked(value)
        self.ctrl.blockSignals(False)

    def GetValue(self) -> bool:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self.ctrl.isChecked()

    # Expose the inner checkbox's signals so callers can do
    # ctrl.ctrl.checkStateChanged.connect(handler) or use the
    # convenience property below.
    @property
    def checkStateChanged(self):
        """Return the check state changed.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.ctrl.checkStateChanged
