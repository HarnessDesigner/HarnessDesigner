# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Signal

from . import events as _events


class Property(QWidget):
    """Represent a property in :mod:`harness_designer.ui.prop_ctrls.prop_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    propertyChanged = Signal(object)

    def __init__(self, parent, label, orientation=None):
        """Initialise the :class:`Property` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param orientation: Value for ``orientation``.
        :type orientation: UNKNOWN
        """
        QWidget.__init__(self, parent)

        self._label = label
        self._ctrl = None
        self._st = None
        self._button = None
        self._units_st = None
        self._parent = parent
        self._static_box = None
        self._orientation = orientation

        if orientation is None:
            self._sizer = QVBoxLayout()
            self._sizer.setContentsMargins(0, 0, 0, 0)
            self.setLayout(self._sizer)
        else:
            self._static_box = QGroupBox(label, self)

            if orientation == 'vertical':
                self._sizer = QVBoxLayout()
                self._sizer.setContentsMargins(4, 4, 4, 4)
                self._static_box.setLayout(self._sizer)

                sizer = QHBoxLayout()
                sizer.addWidget(self._static_box, 1)
                self.setLayout(sizer)

            else:
                self._sizer = QHBoxLayout()
                self._sizer.setContentsMargins(5, 5, 5, 5)
                self._static_box.setLayout(self._sizer)

                sizer = QVBoxLayout()
                sizer.addWidget(self._static_box, 1)
                self.setLayout(sizer)

    def addWidget(self, widget):
        if isinstance(self._sizer, QHBoxLayout):
            self._sizer.addWidget(widget)
        else:
            self._sizer.addWidget(widget, 1)

    def SetToolTip(self, text):
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
            QWidget.setToolTip(self, text)

    def GetLabel(self) -> str:
        """Execute the get label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._label

    def SetLabel(self, value: str):
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

    def _send_changed_event(self, value_type, value):
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

