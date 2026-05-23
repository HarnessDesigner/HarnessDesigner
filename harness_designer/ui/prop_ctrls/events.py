# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtCore import Signal


class PropertyEvent:
    """Represent a property event in :mod:`harness_designer.ui.prop_ctrls.events`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self):
        """Initialise the :class:`PropertyEvent` instance.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._name = None
        self._property = None
        self._property_type = None
        self._value = None

    def GetName(self) -> str:
        """Execute the get name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._name

    def SetName(self, value: str):
        """Execute the set name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._name = value

    def SetProperty(self, value):
        """Execute the set property operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._property = value

    def Getproperty(self):
        """Execute the getproperty operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._property

    def SetPropertyType(self, value):
        """Execute the set property type operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._property_type = value

    def GetPropertyType(self):
        """Execute the get property type operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._property_type

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._value

    def SetValue(self, value):
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._value = value


# Sentinel used by property controls to expose the signal; consumers connect via:
#   prop.property_changed.connect(handler)
# The handler receives a PropertyEvent instance.
EVT_PROPERTY_CHANGED = 'property_changed'
