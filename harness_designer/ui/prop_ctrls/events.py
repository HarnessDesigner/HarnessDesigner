# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import color as _color
    from . import prop_base as _prop_base
    from PySide6 import QtGui

    # Every value a property control emits: scalars, the array lists, and the
    # colour control's [name, Color] pair.
    PropertyValue = (str | int | float | bool | None | list[float] | list[int]
                     | list[str] | list[str | _color.Color | QtGui.QColor])


class PropertyEvent:
    """Represent a property event in :mod:`harness_designer.ui.prop_ctrls.events`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self) -> None:
        """Initialise the :class:`PropertyEvent` instance.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._name = None
        self._property = None
        self._property_type = None
        self._value = None

    @_check_types.do
    def GetName(self) -> str:
        """Execute the get name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self._name

    @_check_types.do
    def SetName(self, value: str) -> None:
        """Execute the set name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._name = value

    @_check_types.do
    def SetProperty(self, value: "_prop_base.Property") -> None:
        """Execute the set property operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._property = value

    @_check_types.do
    def Getproperty(self) -> _Union["_prop_base.Property", None]:
        """Execute the getproperty operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._property

    @_check_types.do
    def SetPropertyType(self, value: type) -> None:
        """Execute the set property type operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._property_type = value

    @_check_types.do
    def GetPropertyType(self) -> type:
        """Execute the get property type operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._property_type

    @_check_types.do
    def GetValue(self) -> "PropertyValue":
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._value

    @_check_types.do
    def SetValue(self, value: "PropertyValue") -> None:
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
