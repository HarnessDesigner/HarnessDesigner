# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtCore import Signal


class PropertyEvent:

    def __init__(self):
        self._name = None
        self._property = None
        self._property_type = None
        self._value = None

    def GetName(self) -> str:
        return self._name

    def SetName(self, value: str):
        self._name = value

    def SetProperty(self, value):
        self._property = value

    def Getproperty(self):
        return self._property

    def SetPropertyType(self, value):
        self._property_type = value

    def GetPropertyType(self):
        return self._property_type

    def GetValue(self):
        return self._value

    def SetValue(self, value):
        self._value = value


# Sentinel used by property controls to expose the signal; consumers connect via:
#   prop.property_changed.connect(handler)
# The handler receives a PropertyEvent instance.
EVT_PROPERTY_CHANGED = 'property_changed'
