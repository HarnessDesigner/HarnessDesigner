# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtCore, QtWidgets

from . import events as _events
from ... import check_types as _check_types


class Property(QtWidgets.QWidget):
    """Represent a property in :mod:`harness_designer.ui.prop_ctrls.prop_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged = QtCore.Signal(object)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, label: str,
                 orientation: str | None = None) -> None:
        """Initialise the :class:`Property` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param orientation: Value for ``orientation``.
        :type orientation: UNKNOWN
        """
        QtWidgets.QWidget.__init__(self, parent)

        self._label = label
        self._ctrl = None
        self._st = None
        self._button = None
        self._units_st = None
        self._parent = parent
        self._static_box = None
        self._orientation = orientation

        if orientation is None:
            self._sizer = QtWidgets.QVBoxLayout()
            self._sizer.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self._sizer)
        else:
            self._static_box = QtWidgets.QGroupBox(label, self)

            if orientation == 'vertical':
                self._sizer = QtWidgets.QVBoxLayout()
                self._sizer.setContentsMargins(4, 4, 4, 4)
                self._static_box.setLayout(self._sizer)

                sizer = QtWidgets.QHBoxLayout()
                sizer.addWidget(self._static_box, 1)
                self.setLayout(sizer)

            else:
                self._sizer = QtWidgets.QHBoxLayout()
                self._sizer.setContentsMargins(5, 5, 5, 5)
                self._static_box.setLayout(self._sizer)

                sizer = QtWidgets.QVBoxLayout()
                sizer.addWidget(self._static_box, 1)
                self.setLayout(sizer)

    @_check_types.do
    def addWidget(self, widget: QtWidgets.QWidget) -> None:
        if isinstance(self._sizer, QtWidgets.QHBoxLayout):
            self._sizer.addWidget(widget)
        else:
            self._sizer.addWidget(widget, 1)

    @_check_types.do
    def SetToolTip(self, text: str) -> None:
        """Execute the set tool tip operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param text: Text value.
        :type text: UNKNOWN
        """
        if self._st is not None:
            self._st.setToolTip(text)
        if self._ctrl is not None:
            self._ctrl.setToolTip(text)
        else:
            QtWidgets.QWidget.setToolTip(self, text)

    @_check_types.do
    def GetLabel(self) -> str:
        """Execute the get label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._label

    @_check_types.do
    def SetLabel(self, value: str) -> None:
        """Execute the set label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._label = value
        if self._static_box is not None:
            self._static_box.setTitle(value)
        elif self._st is not None:
            self._st.setText(value + ':')

    @_check_types.do
    def _send_changed_event(self, value_type: type, value: "_events.PropertyValue") -> None:
        """Execute the send changed event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value_type: Value for ``value_type``.
        :type value_type: UNKNOWN
        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        evt = _events.PropertyEvent()
        evt.SetValue(value)
        evt.SetPropertyType(value_type)
        evt.SetProperty(self)
        self.propertyChanged.emit(evt)

