# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Signal

from . import events as _events


class Property(QWidget):

    property_changed = Signal(object)

    def __init__(self, parent, label, orientation=None):
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
            inner = QVBoxLayout() if orientation == 'vertical' else QHBoxLayout()
            inner.setContentsMargins(4, 4, 4, 4)
            self._static_box.setLayout(inner)
            self._sizer = inner

            outer = QHBoxLayout() if orientation == 'vertical' else QVBoxLayout()
            outer.setContentsMargins(5, 5, 5, 5)
            outer.addWidget(self._static_box)
            self.setLayout(outer)

    def SetToolTip(self, text):
        if self._st is not None:
            self._st.setToolTip(text)
        if self._ctrl is not None:
            self._ctrl.setToolTip(text)
        else:
            QWidget.setToolTip(self, text)

    def Realize(self):
        # In Qt the children are already parented and the layout is set during
        # __init__; Realize() is a no-op hook kept for call-site compatibility.
        self.update()

    def GetLabel(self) -> str:
        return self._label

    def SetLabel(self, value: str):
        self._label = value
        if self._static_box is not None:
            self._static_box.setTitle(value)
        elif self._st is not None:
            self._st.setText(value + ':')

    def Enable(self, flag=True):
        for child in self.findChildren(QWidget):
            child.setEnabled(flag)

    def _send_changed_event(self, value_type, value):
        evt = _events.PropertyEvent()
        evt.SetValue(value)
        evt.SetPropertyType(value_type)
        evt.SetProperty(self)
        self.property_changed.emit(evt)
