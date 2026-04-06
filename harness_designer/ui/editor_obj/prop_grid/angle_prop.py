from typing import TYPE_CHECKING

from wx import propgrid as wxpg


from . import float_prop as _float_prop

if TYPE_CHECKING:
    from ....geometry import angle as _angle


class Angle3DProperty(wxpg.PGProperty):
    def __init__(self, label, name, value: "_angle.Angle"):
        wxpg.PGProperty.__init__(self, label, name)

        self.AddPrivateChild(_float_prop.FloatProperty(
            "X", 'x', value=value.x, min_value=-999.0,
            max_value=999.0, increment=0.01, units='°'))

        self.AddPrivateChild(_float_prop.FloatProperty(
            "Y", 'y', value=value.y, min_value=-999.0,
            max_value=999.0, increment=0.01, units='°'))

        self.AddPrivateChild(_float_prop.FloatProperty(
            "Z", 'z', value=value.y, min_value=-999.0,
            max_value=999.0, increment=0.01, units='°'))

        self.m_value = value

    def GetClassName(self):
        return self.__class__.__name__

    def DoGetEditorClass(self):
        return None

    def RefreshChildren(self):
        point = self.m_value
        self.Item(0).SetValue(point.x)
        self.Item(1).SetValue(point.y)
        self.Item(1).SetValue(point.z)

    def ChildChanged(self, thisValue, childIndex: int, childValue: float):
        point = self.m_value

        if childIndex == 0:
            point.x = childValue
        elif childIndex == 1:
            point.y = childValue
        elif childIndex == 2:
            point.z = childValue
        else:
            raise AssertionError

        return point


class Angle2DProperty(_float_prop.FloatProperty):
    def __init__(self, label, name, value: "_angle.Angle"):
        self.SetClientData(value)

        value = value.z
        _float_prop.FloatProperty.__init__(self, label, name, value, min_value=-180.0,
                                           max_value=180.0, increment=0.01)

        self.m_value = value

    def GetClassName(self):
        return self.__class__.__name__
