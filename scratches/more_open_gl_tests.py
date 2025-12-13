"""
Left mouse click and drag to "look" around.
this is like standing still and moving your head around to "look" around.

Middle click and drag is to rotate about a point.  ** not working currently
This is like tracking a target where the target is always in the center of view.
How far away the targe is, is controlled by the mouse wheel. The target is not
an actual object but a fixed point in 3d space.

Right click and drag is to pan, up down left and right.
This is like side stepping or climbing up and down a ladder.

Mouse wheel is for "zooming".
This is not really zooming as what is being seen is not being scaled.
Because this is a 3d world as we get closer to something it gets larger.
The zooming only increases or decreases the distance from your position to
where your focus is. The focus is a virtual point in the moddle of your
field of view.

Up, down, left and right arrow keys on the keyboard are to walk.
Think of walking, that's what it is like. the up arrow is forward,
down is backward. Left and right are a combination movement. It is a mix of a
look and a pan. After all we do "look" where we are going when we "walk" right?
This does the  same thing. You can press and hold the keys and it can be done
in any combination. They can be pressed in any order and also released in
any order.

Keyboard presses have a ramping feature to it. The default is an increment
of 0.1 every 50 milliseconds. The keystrokes get repeated every 50 milliseconds
which is why the increment takes place at that time. The default is a maximum
of 10.0 for the ramp.. It will not go any higher than the set maximum.

There is a class named "Config" that is just below the imports. This is where
you can change the keys that are used, mouse buttons that are used, input sensitivity
for each of the motion types and the ramping speeds and values as well.
Some of the config settings are not in use yet.
"""


from typing import Self, Iterable, Union


try:
    import wx
except ImportError:
    raise ImportError('the wxPython library is needed to run this code.  '
                      '`pip install wxPython`')

try:
    import build123d
except ImportError:
    raise ImportError('the build123d library is needed to run this code.  '
                      '`pip install build123d`')

try:
    from OpenGL import GL
except ImportError:
    raise ImportError('the PyOpenGL library is needed to run this code.  '
                      '`pip install PyOpenGL`')

try:
    import numpy as np
except ImportError:
    raise ImportError('the numpy library is needed to run this code.  '
                      '`pip install numpy`')

try:
    import python_utils
except ImportError:
    raise ImportError('the python-utils library is needed to run this code. '
                      '`pip install python-utils`')


from OpenGL import GLU
from OCP.gp import gp_Vec, gp
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from wx import glcanvas
import threading
from decimal import Decimal as _Decimal
from scipy.spatial.transform import Rotation as _Rotation
import numpy as np
import math


MOUSE_NONE = 0x00000000
MOUSE_LEFT = 0x00000001
MOUSE_MIDDLE = 0x00000002
MOUSE_RIGHT = 0x00000004
MOUSE_AUX1 = 0x00000008
MOUSE_AUX2 = 0x00000010
MOUSE_WHEEL = 0x00000020


# ********************* CONFIG SETTINGS *********************

class Config:
    class modeling:
        smooth_normals = True
        smooth_weight = 'uniform'  # 'angle', 'area', or 'uniform'

    class keyboard_settings:
        max_speed_factor = 10.0
        speed_factor_increment = 0.1
        start_speed_factor = 1.0

    class settings:
        ground_height = 0.0
        eye_height = 10.0

    class rotate:
        mouse = MOUSE_MIDDLE
        up_key = ord('w')
        down_key = ord('s')
        left_key = ord('a')
        right_key = ord('d')
        sensitivity = 0.1

    class look:
        mouse = MOUSE_LEFT
        up_key = ord('o')
        down_key = ord('l')
        left_key = ord('k')
        right_key = ord(';')
        sensitivity = 0.0002

    class pan:
        mouse = MOUSE_RIGHT
        up_key = ord('8')
        down_key = ord('2')
        left_key = ord('4')
        right_key = ord('6')
        sensitivity = 0.2

    class walk:
        mouse = MOUSE_NONE
        forward_key = wx.WXK_UP
        backward_key = wx.WXK_DOWN
        left_key = wx.WXK_LEFT
        right_key = wx.WXK_RIGHT
        sensitivity = 1.0
        speed = 1.0

    class zoom:
        mouse = MOUSE_WHEEL
        in_key = wx.WXK_ADD
        out_key = wx.WXK_SUBTRACT
        sensitivity = 1.0

    class reset:
        key = wx.WXK_HOME
        mouse = MOUSE_NONE

# ***********************************************************


class Decimal(_Decimal):
    """
    Wrapper around `decimal.Decimal` that allows me to pass floats
    to the constructor instead if having to pass strings
    """

    def __new__(cls, value, *args, **kwargs):
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


_decimal = Decimal

TEN_0 = _decimal(10.0)
ZERO_1 = _decimal(0.1)


def _round_down(val: _decimal) -> _decimal:
    return _decimal(int(val * TEN_0)) * ZERO_1


class Point:

    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr @= instance
                x, y, z = arr

                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs @ self.as_numpy

        if func == np.add:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr += instance
                x, y, z = arr
                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs + self.as_numpy

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr -= instance
                x, y, z = arr
                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs + self.as_numpy

        print('func:', func)
        print()
        print('method:', method)
        print()
        print('inputs:', inputs)
        print()
        print('instance:', instance)
        print()
        print('kwargs:', kwargs)
        print()

        raise RuntimeError

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None):

        if z is None:
            z = _decimal(0.0)

        self._x = _round_down(x)
        self._y = _round_down(y)
        self._z = _round_down(z)

    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = _round_down(value)

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = _round_down(value)

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = _round_down(value)

    def copy(self) -> "Point":
        return Point(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __iadd__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        self.x += x
        self.y += y
        self.z += z

        return self

    def __add__(self, other: Union["Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self
        if isinstance(other, Point):
            x2, y2, z2 = other
        else:
            x2, y2, z2 = (_decimal(float(item)) for item in other)

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Point(x, y, z)

    def __isub__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        self.x -= x
        self.y -= y
        self.z -= z

        return self

    def __sub__(self, other: Union["Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self
        if isinstance(other, Point):
            x2, y2, z2 = other
        else:
            x2, y2, z2 = (_decimal(float(item)) for item in other)

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __itruediv__(self, other: _decimal) -> Self:
        self.x /= other
        self.y /= other
        self.z /= other

        return self

    def __truediv__(self, other: _decimal) -> "Point":
        x, y, z = self
        return Point(x / other, y / other, z / other)

    def set_angle(self, angle: "Angle", origin: "Point"):
        self.x -= origin.x
        self.y -= origin.y
        self.z -= origin.z
        arr = self.as_numpy

        arr @= angle.as_matrix

        self.x = _decimal(arr[0])
        self.y = _decimal(arr[1])
        self.z = _decimal(arr[2])

        self.x += origin.x
        self.y += origin.y
        self.z += origin.z

    def set_x_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(angle, _decimal(0.0), _decimal(0.0), origin)

    def set_y_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), angle, _decimal(0.0), origin)

    def set_z_angle(self, angle: _decimal, origin: "Point") -> None:
        self.set_angles(_decimal(0.0), _decimal(0.0), angle, origin)

    def set_angles(self, x_angle: _decimal, y_angle: _decimal,
                   z_angle: _decimal, origin: "Point") -> None:

        angle = Angle.from_points(origin, self)
        angle.x = x_angle
        angle.y = y_angle
        angle.z = z_angle

        p1 = self
        p2 = origin
        p3 = p1 - p2
        p3 @= angle
        p3 += p2

        self.x, self.y, self.z = [_decimal(float(item)) for item in p3]

    def get_angle(self, origin: "Point") -> "Angle":
        return Angle.from_points(origin, self)

    def __bool__(self):
        return self.as_float == (0, 0, 0)

    def __eq__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other

        return x1 == x2 and y1 == y2 and z1 == z2

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self) -> tuple[float, float, float]:
        return float(self._x), float(self._y), float(self._z)

    @property
    def as_int(self) -> tuple[int, int, int]:
        return int(self._x), int(self._y), int(self._z)

    @property
    def as_numpy(self) -> np.ndarray:
        return np.array(self.as_float, dtype=np.dtypes.Float64DType)

    def __iter__(self) -> Iterable[_decimal]:
        return iter([self._x, self._y, self._z])

    def __str__(self) -> str:
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'

    def __le__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 <= x2 and y1 <= x2 and z1 <= z2

    def __ge__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 >= x2 and y1 >= y2 and z1 >= z2


ZERO_POINT = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))


class Angle:

    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr @= instance
                x, y, z = arr

                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs @ self._R.as_matrix().T

        if func == np.add:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr += instance
                x, y, z = arr
                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs + self.as_numpy

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr -= instance
                x, y, z = arr
                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs + self.as_numpy

        print('func:', func)
        print()
        print('method:', method)
        print()
        print('inputs:', inputs)
        print()
        print('instance:', instance)
        print()
        print('kwargs:', kwargs)
        print()

        raise RuntimeError

    def __init__(self, R):
        self._R = R

        p1 = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        p2 = Point(_decimal(0.0), _decimal(0.0), _decimal(10.0))
        p2 @= self._R.as_matrix().T  # NOQA

        self._p1 = p1
        self._p2 = p2

    @staticmethod
    def __rotate_euler(c1: _decimal, c2: _decimal,
                       c3: _decimal, c4: _decimal,
                       angle: _decimal) -> tuple[_decimal, _decimal]:

        angle = _decimal(math.radians(angle))

        qx = (c1 + _decimal(math.cos(angle)) * (c3 - c1) -
              _decimal(math.sin(angle)) * (c4 - c2))

        qy = (c2 + _decimal(math.sin(angle)) * (c3 - c1) +
              _decimal(math.cos(angle)) * (c4 - c2))

        return qx, qy

    @staticmethod
    def __get_euler(c1: _decimal, c2: _decimal,
                    c3: _decimal, c4: _decimal) -> _decimal:

        theta1 = _decimal(math.atan2(c2, c1))
        theta2 = _decimal(math.atan2(c4, c3))

        return _decimal(
            math.degrees((theta2 - theta1) % _decimal(2) * _decimal(math.pi)))

    @property
    def x(self) -> _decimal:
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        return _decimal(angles[0])

    @x.setter
    def x(self, value: _decimal):
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        angles[0] = float(value)
        self._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA

    @property
    def y(self) -> _decimal:
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        return _decimal(angles[1])

    @y.setter
    def y(self, value: _decimal):
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        angles[1] = float(value)
        self._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA

    @property
    def z(self) -> _decimal:
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        return _decimal(angles[2])

    @z.setter
    def z(self, value: _decimal):
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        angles[2] = float(value)
        self._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA

    def copy(self) -> "Angle":
        return Angle.from_quat(self._R.as_quat())

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        self.x += x
        self.y += y
        self.z += z

        return self

    def __add__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        angle = self.copy()
        angle.x += x
        angle.y += y
        angle.z += z

        return angle

    def __isub__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        self.x -= x
        self.y -= y
        self.z -= z

        return self

    def __sub__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        angle = self.copy()
        angle.x += x
        angle.y += y
        angle.z += z

        return angle

    def __imatmul__(self, other: Union[np.ndarray, Point]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, Point):
            values = other.as_numpy @ self._R.as_matrix().T
            other.x = _decimal(float(values[0]))
            other.y = _decimal(float(values[1]))

            other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __rmatmul__(self, other: Union[np.ndarray, Point]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, Point):
            values = other.as_numpy @ self._R.as_matrix().T
            other.x = _decimal(float(values[0]))
            other.y = _decimal(float(values[1]))
            other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __matmul__(self, other: Union[np.ndarray, Point]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other = other @ self._R.as_matrix().T
        elif isinstance(other, Point):
            other = other.copy()
            values = other.as_numpy @ self._R.as_matrix().T
            other.x = _decimal(float(values[0]))
            other.y = _decimal(float(values[1]))

            other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __bool__(self):
        return self.as_float == (0, 0, 0)

    def __eq__(self, other: "Angle") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other

        return x1 == x2 and y1 == y2 and z1 == z2

    def __ne__(self, other: "Angle") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self) -> tuple[float, float, float]:
        return float(self.x), float(self.y), float(self.z)

    @property
    def as_int(self) -> tuple[int, int, int]:
        return int(self.x), int(self.y), int(self.z)

    @property
    def as_numpy(self) -> np.ndarray:
        return self._R.as_quat()

    @property
    def as_matrix(self) -> np.ndarray:
        return self._R.as_matrix().T

    def __iter__(self) -> Iterable[_decimal]:
        return iter([self.x, self.y, self.z])

    def __str__(self) -> str:
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'

    @property
    def quat(self) -> list[float]:
        return self._R.as_quat().tolist()

    @classmethod
    def from_euler(cls, x: float | _decimal, y: float | _decimal,
                   z: float | _decimal) -> "Angle":

        R = _Rotation.from_euler('xyz', (float(x), float(y), float(z)),
                                 degrees=True)  # NOQA
        return cls(R)

    @classmethod
    def from_quat(cls, q: list[float, float, float, float] | np.ndarray) -> "Angle":
        R = _Rotation.from_quat(q)  # NOQA
        return cls(R)

    @classmethod
    def from_points(cls, p1: Point, p2: Point) -> "Angle":
        # the sign for all of the verticies in the array needs to be flipped in
        # order to handle the -Z axis being near
        p1 = -p1.as_numpy
        p2 = -p2.as_numpy

        f = p2 - p1

        fn = np.linalg.norm(f)
        if fn < 1e-6:
            raise ValueError("p1 and p2 must be different points")

        f = f / fn  # world-space direction of the line

        local_forward = np.array([0.0, 0.0, -1.0],
                                 dtype=np.dtypes.Float64DType)
        nz = np.nonzero(local_forward)[0][0]
        sign = np.sign(local_forward[nz])
        forward_world = f * sign

        up = np.asarray((0.0, 1.0, 0.0),
                        dtype=np.dtypes.Float64DType)

        if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
            up = np.array([0.0, 0.0, 1.0],
                          dtype=np.dtypes.Float64DType)

            if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
                up = np.array([1.0, 0.0, 0.0],
                              dtype=np.dtypes.Float64DType)

        right = np.cross(up, forward_world)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            raise RuntimeError("degenerate right vector")

        right = right / rn

        true_up = np.cross(forward_world, right)  # NOQA

        rot = np.column_stack((right, true_up, forward_world))
        R = _Rotation.from_matrix(rot)  # NOQA
        # q = rot.as_quat()
        # return q.tolist(), R.T
        return cls(R)


ZERO_5 = _decimal(0.5)


class Line:

    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr @= instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])

                return self
            else:
                return inputs @ self.as_numpy

        if func == np.add:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr += instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])
                return self
            else:
                return inputs + self.as_numpy

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr -= instance
                p1, p2 = arr.tolist()

                self._p1.x = _decimal(p1[0])
                self._p1.y = _decimal(p1[1])
                self._p1.z = _decimal(p1[1])

                self._p2.x = _decimal(p2[0])
                self._p2.y = _decimal(p2[1])
                self._p2.z = _decimal(p2[1])
                return self
            else:
                return inputs + self.as_numpy

        print('func:', func)
        print()
        print('method:', method)
        print()
        print('inputs:', inputs)
        print()
        print('instance:', instance)
        print()
        print('kwargs:', kwargs)
        print()

        raise RuntimeError

    def __init__(self, p1: Point,
                 p2: Point | None = None,
                 length: _decimal | None = None,
                 angle: Angle | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, angle):
                raise ValueError('If an end point is not supplied '
                                 'then the "length", "x_angle", "y_angle" and '
                                 '"z_angle" parameters need to be supplied')

            p2 = Point(length, _decimal(0.0), _decimal(0.0))
            p2 @= angle
            p2 += p1

        self._p2 = p2

    @property
    def as_numpy(self) -> np.ndarray:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return np.array([p1, p2], dtype=np.dtypes.Float64DType)

    @property
    def as_float(self) -> tuple[list[float, float, float],
                                list[float, float, float]]:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return p1, p2

    def copy(self) -> "Line":
        p1 = self._p1.copy()
        p2 = self._p2.copy()
        return Line(p1, p2)

    @property
    def p1(self) -> Point:
        return self._p1

    @property
    def p2(self) -> Point:
        return self._p2

    def __len__(self) -> int:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z
        res = math.sqrt(x * x + y * y + z * z)
        return int(round(res))

    def length(self) -> _decimal:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z

        return _decimal(math.sqrt(x * x + y * y + z * z))

    def get_angle(self, origin: Point) -> Angle:
        temp_p1 = self._p1.copy()
        temp_p2 = self._p2.copy()

        if origin == self._p1:
            temp_p2 -= temp_p1
            temp_p1 = ZERO_POINT
        elif origin == self._p2:
            temp_p1 -= temp_p2
            temp_p2 = ZERO_POINT
        else:
            temp_p1 -= origin
            temp_p2 -= origin

        return Angle.from_points(temp_p1, temp_p2)

    def set_angle(self, angle: Angle, origin: Point) -> None:
        if origin == self._p1:
            temp_p2 = self._p2.copy()
            temp_p2 -= origin
            temp_p2 @= angle
            temp_p2 += origin
            diff = temp_p2 - self._p2
            self._p2 += diff

        elif origin == self._p2:
            temp_p1 = self._p1.copy()
            temp_p1 -= origin
            temp_p1 @= angle
            temp_p1 += origin
            diff = temp_p1 - self._p1
            self._p1 += diff
        else:
            temp_p1 = self._p1.copy()
            temp_p2 = self._p2.copy()

            temp_p1 -= origin
            temp_p2 -= origin

            temp_p1 @= angle
            temp_p2 @= angle

            temp_p1 += origin
            temp_p2 += origin

            diff_p1 = temp_p1 - self._p1
            diff_p2 = temp_p2 - self._p2

            self._p1 += diff_p1
            self._p2 += diff_p2

    def point_from_start(self, distance: _decimal) -> Point:
        line = Line(self._p1.copy(), None,
                    distance, self.get_angle(self._p1))

        return line.p2

    @property
    def center(self) -> Point:
        x = (self._p1.x + self._p2.x) * ZERO_5
        y = (self._p1.y + self._p2.y) * ZERO_5
        z = (self._p1.z + self._p2.z) * ZERO_5
        return Point(x, y, z)

    def __iter__(self) -> Iterable[Point]:
        return iter([self._p1, self._p2])

    def get_rotated_line(self, angle: _decimal, pivot: Point) -> "Line":
        """
        This is a 2d function and it only deals with the x and y axis.
        """

        if pivot is None:
            pivot = self.point_from_start(self.length() / _decimal(2.0))

        angle = _decimal(math.radians(angle))

        p1 = self._rotate_point(pivot, self._p1, angle)
        p2 = self._rotate_point(pivot, self._p2, angle)

        return Line(p1, p2)

    def get_parallel_line(self, offset: _decimal) -> "Line":
        """
        This is a 2d function and it only deals with the x and y axis.
        """

        offset /= _decimal(2.0)

        r = _decimal(math.radians(self.get_angle(self._p1).z + _decimal(90)))
        center = self.center
        x, y = center.x, center.y

        x += offset * _decimal(math.cos(r))
        y += offset * _decimal(math.sin(r))

        line = self.get_rotated_line(_decimal(180), Point(x, y, _decimal(0.0)))
        line._p1, line._p2 = line._p2, line._p1

        return line

    @staticmethod
    def _rotate_point(origin: Point, point: Point, angle: _decimal) -> Point:
        """
        This is a 2d function and it only deals with the x and y axis.
        """
        ox, oy = origin.x, origin.y
        px, py = point.x, point.y

        cos = _decimal(math.cos(angle))
        sin = _decimal(math.sin(angle))

        x = px - ox
        y = py - oy

        qx = ox + (cos * x) - (sin * y)
        qy = oy + (sin * x) + (cos * y)
        return Point(qx, qy)


# wires are constructed along the positive Z axis
#             y+
#             |  Z+
#             | /
# x+ ------ center ------ x-
#           / |
#         Z-  |
#             Y-
def create_wire(wire: "Wire"):
    wire_r = wire.diameter / Decimal(2)

    # Create the wire
    cyl = build123d.Cylinder(float(wire_r), float(wire.diameter),
                             align=build123d.Align.NONE)

    sphere1 = build123d.Sphere(wire_r)
    sphere1 = sphere1.move(build123d.Location(
        (0.0, 0.0, float(wire.diameter)), (0, 0, 1)))

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(wire.diameter),
        pitch=float(wire.diameter + wire.diameter * _decimal(0.15)),
        height=float(wire.diameter + wire.diameter * _decimal(0.15)),
        cone_angle=0,
        direction=(1, 0, 0)
    )

    loop_profile = build123d.Circle(float(wire_r))

    swept_cylinder = build123d.sweep(path=loop_helix,
                                     sections=(loop_helix ^ 0) * loop_profile)

    # rotate and position the loop so it align with the cylinder
    swept_cylinder = swept_cylinder.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 90.0)

    swept_cylinder = swept_cylinder.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 9.35)

    swept_cylinder = swept_cylinder.move(
        build123d.Location((0.0, float(wire.diameter), 0.0), (0, 1, 0)))

    # add the loop to the cylinder to make the part
    cyl += swept_cylinder
    cyl += sphere1

    cyl2 = build123d.Cylinder(float(wire_r), float(wire.diameter),
                              align=build123d.Align.NONE)

    sphere2 = build123d.Sphere(wire_r)
    sphere2 = sphere2.move(
        build123d.Location((0.0, 0.0, float(wire.diameter)), (0, 0, 1)))

    wire_axis = cyl2.faces().filter_by(
        build123d.GeomType.CYLINDER)[0].axis_of_rotation

    edges = cyl2.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(
        0, float(wire.diameter / _decimal(3) * _decimal(build123d.MM)))

    stripe_thickness = python_utils.remap(wire.diameter, old_min=1.25, old_max=5.0,
                                          new_min=0.010, new_max=0.025)

    stripe_arc = build123d.Face(edges.offset_2d(
        float(stripe_thickness * Decimal(build123d.MM)), side=build123d.Side.RIGHT))

    twist = build123d.Helix(
        pitch=20.0,
        height=float(wire.diameter),
        radius=float(wire_r),
        center=wire_axis.position,
        direction=wire_axis.direction,
    )

    stripe2 = build123d.sweep(
        stripe_arc,
        build123d.Line(wire_axis.position,
                       float(wire.diameter) * wire_axis.direction),
        binormal=twist
    )

    cyl2 = cyl2.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    sphere2 = sphere2.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    stripe2 = stripe2.rotate(
        build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 180.0)

    cyl2 = cyl2.move(build123d.Location(
        (float(wire.diameter + wire.diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    sphere2 = sphere2.move(build123d.Location(
        (float(wire.diameter + wire.diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    stripe2 = stripe2.move(build123d.Location(
        (float(wire.diameter + wire.diameter * _decimal(0.133)), 0.0, 0.0), (1, 0, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, -float(wire.diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, -float(wire.diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    stripe2 = stripe2.move(build123d.Location(
        (0.0, -float(wire.diameter * _decimal(0.0195)), 0.0), (0, 1, 0)))

    cyl2 = cyl2.move(build123d.Location(
        (0.0, 0.0, -float(wire.diameter * _decimal(0.15))), (0, 0, 1)))

    sphere2 = sphere2.move(build123d.Location(
        (0.0, 0.0, -float(wire.diameter * _decimal(0.15))), (0, 0, 1)))

    stripe2 = stripe2.move(build123d.Location(
        (0.0, 0.0, -float(wire.diameter * _decimal(0.15))), (0, 0, 1)))

    cyl += cyl2
    cyl += sphere2

    wire_axis = cyl.faces().filter_by(
        build123d.GeomType.CYLINDER)[0].axis_of_rotation

    edges = cyl.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(
        0, float(wire.diameter / _decimal(3) * _decimal(build123d.MM)))

    stripe_arc = build123d.Face(edges.offset_2d(
        float(stripe_thickness * Decimal(build123d.MM)), side=build123d.Side.RIGHT))

    twist = build123d.Helix(
        pitch=20.0,
        height=float(wire.diameter),
        radius=float(wire_r),
        center=wire_axis.position,
        direction=wire_axis.direction,
    )

    stripe1 = build123d.sweep(
        stripe_arc,
        build123d.Line(wire_axis.position,
                       float(wire.diameter) * wire_axis.direction),
        binormal=twist
    )

    try:
        bbox = cyl.bounding_box()
        corner1 = Point(*[_decimal(float(item)) for item in bbox.min])
        corner2 = Point(*[_decimal(float(item)) for item in bbox.max])
    except AttributeError:
        bbmin = None
        bbmax = None
        for item in cyl:
            if isinstance(item, build123d.Shape):
                bbox = item.bounding_box()
                corner1 = Point(*[_decimal(float(item)) for item in bbox.min])
                corner2 = Point(*[_decimal(float(item)) for item in bbox.max])
                if bbmin is None or bbmin >= corner1:
                    bbmin = corner1
                if bbmax is None or bbmax <= corner2:
                    bbmax = corner2
        corner1 = bbmin
        corner2 = bbmax

    cn1 = sphere1.center()
    cn2 = sphere2.center()

    cn1 = Point(_decimal(cn1.X), _decimal(cn1.Y), _decimal(cn1.Z))
    cn2 = Point(_decimal(cn2.X), _decimal(cn2.Y), _decimal(cn2.Z))

    return cyl, [stripe1, stripe2], [corner1, corner2], cn1, cn2


def get_triangles(ocp_mesh):
    loc = TopLoc_Location()  # Face locations
    mesh = BRepMesh_IncrementalMesh(
        theShape=ocp_mesh.wrapped,
        theLinDeflection=0.001,
        isRelative=True,
        theAngDeflection=0.1,
        isInParallel=True,
    )

    mesh.Perform()

    triangles = []
    normals = []
    triangle_count = 0

    for facet in ocp_mesh.faces():
        if not facet:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if poly_triangulation is None:
            continue

        trsf = loc.Transformation()

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        for tri in poly_triangulation.Triangles():
            id0, id1, id2 = tri.Get()

            if facet_reversed:
                id1, id2 = id2, id1

            aP1 = poly_triangulation.Node(id0).Transformed(trsf)
            aP2 = poly_triangulation.Node(id1).Transformed(trsf)
            aP3 = poly_triangulation.Node(id2).Transformed(trsf)

            triangles.append([[aP1.X(), aP1.Y(), aP1.Z()],
                              [aP2.X(), aP2.Y(), aP2.Z()],
                              [aP3.X(), aP3.Y(), aP3.Z()]])

            aVec1 = gp_Vec(aP1, aP2)
            aVec2 = gp_Vec(aP1, aP3)
            aVNorm = aVec1.Crossed(aVec2)

            if aVNorm.SquareMagnitude() > gp.Resolution_s():  # NOQA
                aVNorm.Normalize()
            else:
                aVNorm.SetCoord(0.0, 0.0, 0.0)

            for _ in range(3):
                normals.extend([aVNorm.X(), aVNorm.Y(), aVNorm.Z()])

            triangle_count += 3

    return (np.array(normals, dtype=np.dtypes.Float64DType),
            np.array(triangles, dtype=np.dtypes.Float64DType),
            triangle_count)


def get_smooth_triangles(ocp_mesh):
    loc = TopLoc_Location()  # Face locations
    BRepMesh_IncrementalMesh(
        theShape=ocp_mesh.wrapped,
        theLinDeflection=0.001,
        isRelative=True,
        theAngDeflection=0.1,
        isInParallel=True,
    )

    ocp_mesh_vertices = []
    triangles = []
    offset = 0
    for facet in ocp_mesh.faces():
        if not facet:
            continue

        # Triangulate the face
        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()
        # Store the vertices in the triangulated face
        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            ocp_mesh_vertices.append(pnt)

        # Store the triangles from the triangulated faces

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        order = [1, 3, 2] if facet_reversed else [1, 2, 3]
        for tri in poly_triangulation.Triangles():
            triangles.append([tri.Value(i) + offset - 1 for i in order])

        offset += node_count

    ocp_mesh_vertices = np.array(ocp_mesh_vertices, dtype=np.dtypes.Float64DType)
    triangles = np.array(triangles, dtype=np.dtypes.Int32DType)

    normals, triangles = (
        make_per_corner_arrays(ocp_mesh_vertices, triangles, Config.modeling.smooth_weight))

    return normals, triangles, len(triangles)


def _safe_normalize(v, eps=1e-12):
    """Normalize rows of v (shape (...,3)). Avoid divide-by-zero."""
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    norms = np.where(norms <= eps, 1.0, norms)
    return v / norms


def compute_face_normals(v0, v1, v2):
    """Un-normalized face normals (cross product e1 x e2)."""
    return np.cross(v1 - v0, v2 - v0)


def compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray, method: str = "angle") -> np.ndarray:
    """
    Compute per-vertex smooth normals.

    method: "angle" (angle-weighted), "area" (area-weighted), "uniform" (unweighted).
    Returns (N,3) array of normalized vertex normals.
    """
    # Gather triangle corners
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    face_normals = compute_face_normals(v0, v1, v2)  # (F,3)

    N = vertices.shape[0]
    accum = np.zeros((N, 3), dtype=np.dtypes.Float64DType)

    if method == "area":
        # area-weighted accumulation (face_normals magnitude ~ 2*area*unit_normal)
        np.add.at(accum, faces[:, 0], face_normals)
        np.add.at(accum, faces[:, 1], face_normals)
        np.add.at(accum, faces[:, 2], face_normals)

    elif method == "angle":
        # angle-weighted accumulation
        # edges for corner angles
        e0 = v1 - v0  # edge v0->v1
        e1 = v2 - v1  # edge v1->v2
        e2 = v0 - v2  # edge v2->v0

        def corner_angle(a, b):
            # angle between vectors a and b, per-face (F,)
            na = np.linalg.norm(a, axis=1)
            nb = np.linalg.norm(b, axis=1)
            denom = na * nb
            denom = np.where(denom == 0, 1.0, denom)
            cosang = np.sum(a * b, axis=1) / denom
            cosang = np.clip(cosang, -1.0, 1.0)
            return np.arccos(cosang)

        ang0 = corner_angle(-e2, e0)  # angle at v0
        ang1 = corner_angle(-e0, e1)  # angle at v1
        ang2 = corner_angle(-e1, e2)  # angle at v2

        np.add.at(accum, faces[:, 0], face_normals * ang0[:, None])
        np.add.at(accum, faces[:, 1], face_normals * ang1[:, None])
        np.add.at(accum, faces[:, 2], face_normals * ang2[:, None])

    elif method == "uniform":
        # unweighted (each face contributes equally, normalized face normal)
        unit_face = _safe_normalize(face_normals)
        np.add.at(accum, faces[:, 0], unit_face)
        np.add.at(accum, faces[:, 1], unit_face)
        np.add.at(accum, faces[:, 2], unit_face)

    else:
        raise ValueError("method must be 'angle', 'area', or 'uniform'")

    # normalize per-vertex and handle zero-length
    vertex_normals = _safe_normalize(accum)
    zero_mask = np.linalg.norm(accum, axis=1) < 1e-12
    if zero_mask.any():
        # fallback: set zero normals to +Z
        vertex_normals[zero_mask] = np.array([0.0, 0.0, 1.0], dtype=float)

    return vertex_normals


def make_per_corner_arrays(vertices: np.ndarray, faces: np.ndarray, method: str = "area"):
    """
    Given:
      vertices: (N,3) float
      faces: (F,3) int
    Returns:
      positions_flat: (F*3, 3) float32
      normals_flat:   (F*3, 3) float32
    Suitable for glVertexPointer(3, GL_FLOAT, 0, positions_flat) and
    glNormalPointer(GL_FLOAT, 0, normals_flat).
    """
    # compute smooth per-vertex normals
    v_normals = compute_vertex_normals(vertices, faces, method=method)  # (N,3)

    # expand to per-corner arrays (flatten triangles in order)
    positions_flat = vertices[faces].reshape(-1, 3)
    normals_flat = v_normals[faces].reshape(-1, 3)

    # Ensure float32 contiguous arrays for OpenGL
    return (np.ascontiguousarray(normals_flat, dtype=np.dtypes.Float64DType),
            np.ascontiguousarray(positions_flat, dtype=np.dtypes.Float64DType))


class Wire:

    def __init__(self, parent, p1, p2, diameter, color, stripe_color):
        self.parent = parent
        self.p1 = p1
        self.p2 = p2
        self.diameter = diameter
        self.color = color
        self.stripe_color = stripe_color
        self.popup = None

        model, stripes, bbox, start_point, stop_point = create_wire(self)

        self.triangles = []
        self.normals = []
        self.colors = []
        self.is_selected = False

        self.bbox = bbox
        self.angle = Angle.from_points(p1, p2)

        def do(m):
            try:
                if Config.modeling.smooth_normals:
                    nrmals, trs, trs_count = get_smooth_triangles(m)
                else:
                    nrmals, trs, trs_count = get_triangles(m)

                trs -= start_point
                trs @= self.angle
                trs += p1

                self.colors.append(self.color)
                self.triangles.append((nrmals, trs, trs_count))
            except AttributeError:
                for item in model:
                    if isinstance(item, build123d.Shape):
                        do(item)
        do(model)
        bbox[0] -= start_point
        bbox[0] += p1
        bbox[1] -= start_point
        bbox[1] @= self.angle
        bbox[1] += p1

        for stripe in stripes:
            if Config.modeling.smooth_normals:
                normals, tris, tris_count = get_smooth_triangles(stripe)
            else:
                normals, tris, tris_count = get_triangles(stripe)

            tris -= start_point
            tris @= self.angle
            tris += p1

            self.triangles.append((normals, tris, tris_count))
            self.colors.append(self.stripe_color)

    def hit_test(self, p: Point) -> bool:
        p1, p2 = self.bbox

        return p1 <= p <= p2

    @property
    def length(self):
        line = Line(self.p1, self.p2)
        return line.length()

    def popup_window(self, w, h):
        if self.popup is not None:
            return

        self.popup = PopupWindow(self.parent, (w, -1),
                                 (0, 0), self.p1.copy(), self.angle.copy())

        w_h = self.popup.GetBestHeight(w)
        y = h - w_h
        self.popup.SetPosition((0, y))
        self.popup.Show()

        self.popup.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_spin)

    def on_spin(self, evt):
        point = self.popup.GetPoint()
        angle = self.popup.GetAngle()

        point_diff = point - self.p1
        angle_diff = angle - self.angle

        for (normals, tris, tris_count) in self.triangles:
            tris -= self.p1
            tris @= angle_diff
            tris += self.p1
            tris += point_diff

        self.bbox[0] += point_diff
        bb2 = self.bbox[1]
        bb2 -= self.p1
        bb2 @= self.angle
        bb2 += point_diff
        bb2 += self.p1

        self.angle += angle_diff
        self.p1 += point_diff

        self.parent.Refresh(False)
        evt.Skip()


class PopupWindow(wx.Panel):

    def __init__(self, parent, size, pos, point: Point, angle: Angle):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size,
                          pos=pos, style=wx.BORDER_SUNKEN)

        self.point = point
        self.angle = angle

        self.x = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(point.x),
                                   initial=float(point.x), min=-300.0, max=300.0, inc=0.1)

        self.y = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(point.y),
                                   initial=float(point.y), min=-300.0, max=300.0, inc=0.1)

        self.z = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(point.z),
                                   initial=float(point.z), min=-300.0, max=300.0, inc=0.1)

        x_label = wx.StaticText(self, wx.ID_ANY, label='X:')
        y_label = wx.StaticText(self, wx.ID_ANY, label='Y:')
        z_label = wx.StaticText(self, wx.ID_ANY, label='Z:')

        self.angle_x = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(angle.x),
                                         initial=float(angle.x), min=0.0, max=359.9, inc=0.1)

        self.angle_y = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(angle.y),
                                         initial=float(angle.y), min=0.0, max=359.9, inc=0.1)

        self.angle_z = wx.SpinCtrlDouble(self, wx.ID_ANY, value=str(angle.z),
                                         initial=float(angle.z), min=0.0, max=359.9, inc=0.1)

        angle_x_label = wx.StaticText(self, wx.ID_ANY, label='X Angle:')
        angle_y_label = wx.StaticText(self, wx.ID_ANY, label='Y Angle:')
        angle_z_label = wx.StaticText(self, wx.ID_ANY, label='Z Angle:')

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(x_label, 0, wx.LEFT, 10)
        sizer.Add(self.x, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(1)

        sizer.Add(y_label, 0, wx.LEFT, 10)
        sizer.Add(self.y, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(1)

        sizer.Add(z_label, 0, wx.LEFT, 10)
        sizer.Add(self.z, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(5)

        sizer.Add(angle_x_label, 0, wx.LEFT, 10)
        sizer.Add(self.angle_x, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(1)

        sizer.Add(angle_y_label, 0, wx.LEFT, 10)
        sizer.Add(self.angle_y, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(1)

        sizer.Add(angle_z_label, 0, wx.LEFT, 10)
        sizer.Add(self.angle_z, 0, wx.LEFT | wx.RIGHT, 5)
        sizer.AddSpacer(1)

        self.SetSizerAndFit(sizer)

    def GetPoint(self) -> Point:
        return Point(_decimal(self.x.GetValue()),
                     _decimal(self.y.GetValue()),
                     _decimal(self.z.GetValue()))

    def GetAngle(self) -> Angle:
        return Angle.from_euler(self.angle_x.GetValue(),
                                self.angle_y.GetValue(),
                                self.angle_z.GetValue())


KEY_MULTIPLES = {
    wx.WXK_UP: [wx.WXK_UP, wx.WXK_NUMPAD_UP],
    wx.WXK_NUMPAD_UP: [wx.WXK_UP, wx.WXK_NUMPAD_UP],

    wx.WXK_DOWN: [wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN],
    wx.WXK_NUMPAD_DOWN: [wx.WXK_DOWN, wx.WXK_NUMPAD_DOWN],

    wx.WXK_LEFT: [wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT],
    wx.WXK_NUMPAD_LEFT: [wx.WXK_LEFT, wx.WXK_NUMPAD_LEFT],

    wx.WXK_RIGHT: [wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT],
    wx.WXK_NUMPAD_RIGHT: [wx.WXK_RIGHT, wx.WXK_NUMPAD_RIGHT],

    ord('-'): [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],
    wx.WXK_SUBTRACT: [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],
    wx.WXK_NUMPAD_SUBTRACT: [ord('-'), wx.WXK_SUBTRACT, wx.WXK_NUMPAD_SUBTRACT],

    ord('+'): [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],
    wx.WXK_ADD: [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],
    wx.WXK_NUMPAD_ADD: [ord('+'), wx.WXK_ADD, wx.WXK_NUMPAD_ADD],

    ord('/'): [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],
    wx.WXK_DIVIDE: [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],
    wx.WXK_NUMPAD_DIVIDE: [ord('/'), wx.WXK_DIVIDE, wx.WXK_NUMPAD_DIVIDE],

    ord('*'): [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],
    wx.WXK_MULTIPLY: [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],
    wx.WXK_NUMPAD_MULTIPLY: [ord('*'), wx.WXK_MULTIPLY, wx.WXK_NUMPAD_MULTIPLY],

    ord('.'): [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],
    wx.WXK_DECIMAL: [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],
    wx.WXK_NUMPAD_DECIMAL: [ord('.'), wx.WXK_DECIMAL, wx.WXK_NUMPAD_DECIMAL],

    ord('|'): [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],
    wx.WXK_SEPARATOR: [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],
    wx.WXK_NUMPAD_SEPARATOR: [ord('|'), wx.WXK_SEPARATOR, wx.WXK_NUMPAD_SEPARATOR],

    ord(' '): [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],
    wx.WXK_SPACE: [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],
    wx.WXK_NUMPAD_SPACE: [ord(' '), wx.WXK_SPACE, wx.WXK_NUMPAD_SPACE],

    ord('='): [ord('='), wx.WXK_NUMPAD_EQUAL],
    wx.WXK_NUMPAD_EQUAL: [ord('='), wx.WXK_NUMPAD_EQUAL],

    wx.WXK_HOME: [wx.WXK_HOME, wx.WXK_NUMPAD_HOME],
    wx.WXK_NUMPAD_HOME: [wx.WXK_HOME, wx.WXK_NUMPAD_HOME],

    wx.WXK_END: [wx.WXK_END, wx.WXK_NUMPAD_END],
    wx.WXK_NUMPAD_END: [wx.WXK_END, wx.WXK_NUMPAD_END],

    wx.WXK_PAGEUP: [wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP],
    wx.WXK_NUMPAD_PAGEUP: [wx.WXK_PAGEUP, wx.WXK_NUMPAD_PAGEUP],

    wx.WXK_PAGEDOWN: [wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN],
    wx.WXK_NUMPAD_PAGEDOWN: [wx.WXK_PAGEDOWN, wx.WXK_NUMPAD_PAGEDOWN],

    wx.WXK_RETURN: [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER],
    wx.WXK_NUMPAD_ENTER: [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER],

    wx.WXK_INSERT: [wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT],
    wx.WXK_NUMPAD_INSERT: [wx.WXK_INSERT, wx.WXK_NUMPAD_INSERT],

    wx.WXK_TAB: [wx.WXK_TAB, wx.WXK_NUMPAD_TAB],
    wx.WXK_NUMPAD_TAB: [wx.WXK_TAB, wx.WXK_NUMPAD_TAB],

    wx.WXK_DELETE: [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE],
    wx.WXK_NUMPAD_DELETE: [wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE],

    ord('0'): [ord('0'), wx.WXK_NUMPAD0],
    wx.WXK_NUMPAD0: [ord('0'), wx.WXK_NUMPAD0],

    ord('1'): [ord('1'), wx.WXK_NUMPAD1],
    wx.WXK_NUMPAD1: [ord('1'), wx.WXK_NUMPAD1],

    ord('2'): [ord('2'), wx.WXK_NUMPAD2],
    wx.WXK_NUMPAD2: [ord('2'), wx.WXK_NUMPAD2],

    ord('3'): [ord('3'), wx.WXK_NUMPAD3],
    wx.WXK_NUMPAD3: [ord('3'), wx.WXK_NUMPAD3],

    ord('4'): [ord('4'), wx.WXK_NUMPAD4],
    wx.WXK_NUMPAD4: [ord('4'), wx.WXK_NUMPAD4],

    ord('5'): [ord('5'), wx.WXK_NUMPAD5],
    wx.WXK_NUMPAD5: [ord('5'), wx.WXK_NUMPAD5],

    ord('6'): [ord('6'), wx.WXK_NUMPAD6],
    wx.WXK_NUMPAD6: [ord('6'), wx.WXK_NUMPAD6],

    ord('7'): [ord('7'), wx.WXK_NUMPAD7],
    wx.WXK_NUMPAD7: [ord('7'), wx.WXK_NUMPAD7],

    ord('8'): [ord('8'), wx.WXK_NUMPAD8],
    wx.WXK_NUMPAD8: [ord('8'), wx.WXK_NUMPAD8],

    ord('9'): [ord('9'), wx.WXK_NUMPAD9],
    wx.WXK_NUMPAD9: [ord('9'), wx.WXK_NUMPAD9],
}


def _process_key_event(keycode: int, *keys):

    for expected_keycode in keys:
        if expected_keycode is None:
            continue

        expected_keycodes = KEY_MULTIPLES.get(
            expected_keycode,
            [expected_keycode, ord(chr(expected_keycode).upper())]
            if 32 <= expected_keycode <= 126 else
            [expected_keycode]
        )

        if keycode in expected_keycodes:
            return expected_keycode


class Canvas(glcanvas.GLCanvas):
    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        self.context = glcanvas.GLContext(self)

        self.viewMatrix = None
        self.size = None

        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_dclick)

        self.Bind(wx.EVT_MIDDLE_UP, self.on_middle_up)
        self.Bind(wx.EVT_MIDDLE_DOWN, self.on_middle_down)
        self.Bind(wx.EVT_MIDDLE_DCLICK, self.on_middle_dclick)

        self.Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_RIGHT_DCLICK, self.on_right_dclick)

        self.Bind(wx.EVT_MOUSE_AUX1_UP, self.on_aux1_up)
        self.Bind(wx.EVT_MOUSE_AUX1_DOWN, self.on_aux1_down)
        self.Bind(wx.EVT_MOUSE_AUX1_DCLICK, self.on_aux1_dclick)

        self.Bind(wx.EVT_MOUSE_AUX2_UP, self.on_aux2_up)
        self.Bind(wx.EVT_MOUSE_AUX2_DOWN, self.on_aux2_down)
        self.Bind(wx.EVT_MOUSE_AUX2_DCLICK, self.on_aux2_dclick)

        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

        self._running_keycodes = {}
        self._key_event = threading.Event()
        self._key_queue_lock = threading.Lock()
        self._keycode_thread = threading.Thread(target=self._key_loop)
        self._keycode_thread.daemon = True
        self._keycode_thread.start()

        # camera positioning

        #             y+ (up)
        #             |  Z- (forward)
        #             | /
        # x- ------ center ------ x+ (right)
        #           / |
        #         Z+  |
        #             Y-

        # f = np.linalg.norm(camera_pos - camera_eye);
        # temp_up = np.array([0.0, 1.0, 0.0], dtypes=np.dtypes.Float64DType)
        # r = np.linalg.norm(np.cross(temp_up, f))
        # u = np.linalg.norm(np.cross(f, r))
        # t_x = np.dot(positionOfCamera, r)
        # t_y = np.dot(positionOfCamera, u)
        # t_z = np.dot(positionOfCamera, f)
        #
        # lookat_matrix = np.array([[r[0], r[1], r[2], t_x],
        #                           [u[0], u[1], u[2], t_y],
        #                           [f[0], f[1], f[2], t_z],
        #                           [0.0,   0.0,  0.0, 1.0]],
        #                          dtype=np.dtypes.Float64DType)
        #
        # view_matrix = np.array([[r[0], u[0], f[0], 0.0],
        #                         [r[1], u[1], f[1], 0.0],
        #                         [r[2], u[2], f[2], 0.0],
        #                         [-t_x, -t_y, -t_z, 1.0]],
        #                        dtype=np.dtypes.Float64DType)

        self.camera_pos = Point(_decimal(0.0),
                                _decimal(Config.settings.eye_height),
                                _decimal(0.0))

        self.camera_eye = Point(_decimal(0.0),
                                _decimal(Config.settings.eye_height + 0.5),
                                _decimal(75.0))

        self.camera_angle = Angle.from_points(self.camera_pos, self.camera_eye)

        self.camera_position_angle = Angle.from_points(
            Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)), self.camera_pos)

        self.selected = None
        self.wires = []

        self._grid = None
        self.is_motion = False
        self.mouse_pos = None

        t = threading.Thread(target=self.make_wires)
        t.daemon = True
        t.start()

    def _key_loop(self):

        while not self._key_event.is_set():
            with self._key_queue_lock:
                temp_queue = [[func, items['keys'], items['factor']]
                              for func, items in self._running_keycodes.items()]

            for func, keys, factor in temp_queue:
                wx.CallAfter(func, factor, *list(keys))

                if factor < Config.keyboard_settings.max_speed_factor:
                    factor += Config.keyboard_settings.speed_factor_increment

                    with self._key_queue_lock:
                        self._running_keycodes[func]['factor'] = factor

            self._key_event.wait(0.05)

    def on_key_up(self, evt: wx.KeyEvent):
        keycode = evt.GetKeyCode()
        evt.Skip()

        def remove_from_queue(func, k):
            with self._key_queue_lock:
                if func in self._running_keycodes:
                    items = self._running_keycodes.pop(func)
                    keys = list(items['keys'])
                    if k in keys:
                        keys.remove(k)

                    if keys:
                        items['keys'] = set(keys)
                        self._running_keycodes[func] = items

        rot = Config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            remove_from_queue(self._process_rotate_key, key)
            return

        look = Config.look
        key = _process_key_event(keycode, look.up_key, look.down_key,
                                 look.left_key, look.right_key)
        if key is not None:
            remove_from_queue(self._process_look_key, key)
            return

        pan = Config.pan
        key = _process_key_event(keycode, pan.up_key, pan.down_key,
                                 pan.left_key, pan.right_key)
        if key is not None:
            remove_from_queue(self._process_pan_key, key)
            return

        walk = Config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            remove_from_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            remove_from_queue(self._process_zoom_key, key)
            return

    def on_key_down(self, evt: wx.KeyEvent):
        keycode = evt.GetKeyCode()
        evt.Skip()

        def add_to_queue(func, k):
            with self._key_queue_lock:
                if func not in self._running_keycodes:
                    self._running_keycodes[func] = dict(
                        keys=set(),
                        factor=Config.keyboard_settings.start_speed_factor)

                self._running_keycodes[func]['keys'].add(k)

        rot = Config.rotate
        key = _process_key_event(keycode, rot.up_key, rot.down_key,
                                 rot.left_key, rot.right_key)
        if key is not None:
            add_to_queue(self._process_rotate_key, key)
            return

        look = Config.look
        key = _process_key_event(keycode, look.up_key, look.down_key,
                                 look.left_key, look.right_key)
        if key is not None:
            add_to_queue(self._process_look_key, key)
            return

        pan = Config.pan
        key = _process_key_event(keycode, pan.up_key, pan.down_key,
                                 pan.left_key, pan.right_key)
        if key is not None:
            add_to_queue(self._process_pan_key, key)
            return

        walk = Config.walk
        key = _process_key_event(keycode, walk.forward_key, walk.backward_key,
                                 walk.left_key, walk.right_key)
        if key is not None:
            add_to_queue(self._process_walk_key, key)
            return

        zoom = Config.zoom
        key = _process_key_event(keycode, zoom.in_key, zoom.out_key)
        if key is not None:
            add_to_queue(self._process_zoom_key, key)
            return

        key = _process_key_event(keycode, Config.reset.key)
        if key is not None:
            self._process_reset_key(key)
            return

    def _process_rotate_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.rotate.up_key:
                dy += 1.0
            elif key == Config.rotate.down_key:
                dy -= 1.0
            elif key == Config.rotate.left_key:
                dx -= 1.0
            elif key == Config.rotate.right_key:
                dx += 1.0

        self.rotate(_decimal(dx) * _decimal(factor),
                    _decimal(dy) * _decimal(factor))

    def _process_look_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.look.up_key:
                dy += 1.0
            elif key == Config.look.down_key:
                dy -= 1.0
            elif key == Config.look.left_key:
                dx -= 1.0
            elif key == Config.look.right_key:
                dx += 1.0

        self.look(_decimal(dx) * _decimal(factor),
                  _decimal(dy) * _decimal(factor))

    def _process_pan_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.pan.up_key:
                dy -= 3.0
            elif key == Config.pan.down_key:
                dy += 3.0
            elif key == Config.pan.left_key:
                dx -= 3.0
            elif key == Config.pan.right_key:
                dx += 3.0

        self.pan(_decimal(dx) * _decimal(factor),
                 _decimal(dy) * _decimal(factor))

    def _process_walk_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.walk.forward_key:
                dy += 2.0
            elif key == Config.walk.backward_key:
                dy -= 2.0
            elif key == Config.walk.left_key:
                dx += 1.0
            elif key == Config.walk.right_key:
                dx -= 1.0

        self.walk(_decimal(dx) * _decimal(factor),
                  _decimal(dy) * _decimal(factor))

    def _process_zoom_key(self, factor, *keys):
        delta = 0.0

        for key in keys:
            if key == Config.zoom.in_key:
                delta += 1.0
            elif key == Config.zoom.out_key:
                delta -= 1.0

        self.zoom(_decimal(delta) * _decimal(factor))

    def _process_reset_key(self, *_):
        self.reset()

    def reset(self, *_):
        self.camera_pos = Point(_decimal(0.0),
                                _decimal(Config.settings.eye_height),
                                _decimal(0.0))

        self.camera_eye = Point(_decimal(0.0),
                                _decimal(Config.settings.eye_height + 0.5),
                                _decimal(75.0))

        self.camera_angle = Angle.from_points(self.camera_pos, self.camera_eye)

        self.camera_position_angle = Angle.from_points(
            Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)), self.camera_pos)

        self.Refresh(False)

    def _process_mouse(self, code):
        for config, func in (
            (Config.walk, self.walk),
            (Config.pan, self.pan),
            (Config.reset, self.reset),
            (Config.rotate, self.rotate),
            (Config.look, self.look),
            (Config.zoom, self.zoom)
        ):
            if config.mouse is None:
                continue

            if config.mouse == code:
                return func

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def on_left_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        if not self.is_motion:
            x, y = evt.GetPosition()
            p = self.get_world_coords(x, y)

            for wire in self.wires:
                if wire.hit_test(p):
                    if self.selected is not None and wire != self.selected:
                        self.selected.popup.Destroy()
                        self.selected.popup = None
                        self.selected.is_selected = False

                    self.selected = wire
                    wire.is_selected = True
                    w, h = self.GetSize()

                    wire.popup_window(w, h)

                    self.Refresh(False)
                    break
            else:
                if self.selected is not None:
                    self.selected.popup.Destroy()
                    self.selected.popup = None
                    self.selected.is_selected = False
                    self.selected = None
                    self.Refresh(False)

        if not evt.RightIsDown():
            if self.HasCapture():
                self.ReleaseMouse()
            self.mouse_pos = None

        self.is_motion = False

        evt.Skip()

    def on_left_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_left_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_middle_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        evt.Skip()

    def on_middle_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_middle_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_right_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_right_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_right_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_mouse_wheel(self, evt: wx.MouseEvent):
        if evt.GetWheelRotation() > 0:
            self.zoom(_decimal(1.0))
        else:
            self.zoom(-_decimal(1.0))

        self.Refresh(False)
        evt.Skip()

    def on_mouse_motion(self, evt: wx.MouseEvent):
        if self.HasCapture():
            x, y = evt.GetPosition()
            last_x, last_y = self.mouse_pos
            dx = _decimal(x - last_x)
            dy = _decimal(y - last_y)
            self.mouse_pos = [x, y]

            if evt.LeftIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_LEFT)(-dx, -dy)
            if evt.MiddleIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_MIDDLE)(dx, dy)
            if evt.RightIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_RIGHT)(-dx, -dy)
            if evt.Aux1IsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_AUX1)(dx, dy)
            if evt.Aux2IsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_AUX2)(dx, dy)

        evt.Skip()

    def _process_mouse_release(self, evt: wx.MouseEvent):
        if True not in (
            evt.LeftIsDown(),
            evt.MiddleIsDown(),
            evt.RightIsDown(),
            evt.Aux1IsDown(),
            evt.Aux2IsDown()
        ):
            if self.HasCapture():
                self.ReleaseMouse()

    def on_aux1_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux1_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_aux1_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux2_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def on_aux2_down(self, evt: wx.MouseEvent):
        self.is_motion = False

        if not self.HasCapture():
            self.CaptureMouse()

        x, y = evt.GetPosition()
        self.mouse_pos = [x, y]

        evt.Skip()

    def on_aux2_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    def make_wires(self):
        self.wires.append(Wire(self, Point(Decimal(0.0), Decimal(20.0), Decimal(0.0)),
                               Point(Decimal(0.0), Decimal(20.0), Decimal(20.0)),
                               Decimal(0.61), (0.5, 0.0, 0.8, 1.0),
                               (1.0, 0.4, 0.0, 1.0)))

        self.wires.append(Wire(self, Point(Decimal(20.0), Decimal(20.0), Decimal(0.0)),
                               Point(Decimal(20.0), Decimal(20.0), Decimal(20.0)),
                               Decimal(2.29), (0.2, 0.2, 0.2, 1.0),
                               (0.0, 0.0, 1.0, 1.0)))

        self.wires.append(Wire(self, Point(Decimal(40.0), Decimal(20.0), Decimal(0.0)),
                               Point(Decimal(40.0), Decimal(20.0), Decimal(20.0)),
                               Decimal(3.81), (0.2, 0.2, 0.2, 1.0),
                               (0.0, 1.0, 0.0, 1.0)))

        self.wires.append(Wire(self, Point(Decimal(60.0), Decimal(20.0), Decimal(0.0)),
                               Point(Decimal(60.0), Decimal(20.0), Decimal(20.0)),
                               Decimal(6.48), (0.2, 0.2, 0.2, 1.0),
                               (1.0, 0.0, 0.0, 1.0)))

        wx.CallAfter(self.Refresh, False)

    def get_world_coords(self, mx, my) -> Point:
        self.SetCurrent(self.context)

        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        depth = GL.glReadPixels(float(mx), float(my), 1.0, 1.0,
                                GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)

        x, y, z = GLU.gluUnProject(float(mx), float(my), depth,
                                   modelview, projection, viewport)

        return Point(_decimal(x), _decimal(y), _decimal(z))

    def on_erase_background(self, _):
        pass

    def on_size(self, event):
        if self.selected is not None:
            w, h = event.GetSize()
            w_h = self.selected.popup.GetBestHeight(w)
            y = h - w_h
            self.selected.popup.SetPosition((0, y))

        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize() * self.GetContentScaleFactor()
        self.SetCurrent(self.context)
        GL.glViewport(0, 0, size.width, size.height)

    def on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.InitGL()
            self.init = True

        self.OnDraw()

    def rotate(self, dx, dy):
        # Orbit camera_eye around camera_pos.
        # dx/dy are degree deltas (consistent with prior code).
        dx *= _decimal(Config.look.sensitivity)
        dy *= _decimal(Config.look.sensitivity)  # NOQA

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = eye - pos

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        # Yaw around world up (y axis)
        yaw_r = math.radians(dx)
        cos_y = math.cos(yaw_r)
        sin_y = math.sin(yaw_r)  # NOQA
        up = np.array([0.0, 1.0, 0.0], dtype=float)

        # Rodrigues rotation around up
        yaw = (forward * cos_y + np.cross(up, forward) *
               sin_y + up * (np.dot(up, forward) * (1.0 - cos_y)))  # NOQA

        # Pitch around camera right axis (right is cross of forward and up)
        forward = -yaw / np.linalg.norm(yaw)
        right = np.cross(forward, up)  # NOQA
        rn = np.linalg.norm(right)
        if rn < 1e-6:
            # cannot pitch; avoid degenerate
            rotated = yaw
        else:
            right = right / rn
            pitch_rad = math.radians(dy)
            cos_p = math.cos(pitch_rad)
            sin_p = math.sin(pitch_rad)  # NOQA
            rotated = (yaw * cos_p + np.cross(right, yaw) *
                       sin_p + right * (np.dot(right, yaw) * (1.0 - cos_p)))  # NOQA

        new_eye = pos + rotated

        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z
        ) = _decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2])

        self.Refresh(False)

    def InitGL(self):
        w, h = self.GetSize()
        GL.glClearColor(0.20, 0.20, 0.20, 0.0)
        GL.glViewport(0, 0, w, h)

        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LIGHTING)
        # glEnable(GL_ALPHA_TEST)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)

        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        # glEnable(GL_FOG)
        GL.glDepthMask(GL.GL_TRUE)
        # glShadeModel(GL_FLAT)

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        # glEnable(GL_NORMALIZE)
        GL.glEnable(GL.GL_RESCALE_NORMAL)
        # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glEnable(GL.GL_LIGHT0)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(45, w / float(h), 0.1, 1000.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GLU.gluLookAt(0.0, 2.0, -16.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

    def look(self, dx, dy):
        # Orbit camera_pos around camera_eye (opposite of look)
        dx *= _decimal(Config.rotate.sensitivity)
        dy *= _decimal(Config.rotate.sensitivity)

        dx = -dx

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)

        if fn < 1e-6:
            return

        # Yaw around world up
        yaw_rad = math.radians(dx)
        cos_y = math.cos(yaw_rad)
        sin_y = math.sin(yaw_rad)  # NOQA
        up = np.array([0.0, 1.0, 0.0], dtype=np.dtypes.Float64DType)

        k = up
        yaw = (forward * cos_y + np.cross(k, forward) *
               sin_y + k * (np.dot(k, forward) * (1.0 - cos_y)))  # NOQA

        yawn = np.linalg.norm(yaw)
        if yawn < 1e-6:
            return

        # Pitch around right axis (right based on new forward)
        yawn = -yaw / yawn
        right = np.cross(yawn, up)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            yaw_r = yaw
        else:
            right = right / rn
            pitch_rad = math.radians(dy)
            cos_p = math.cos(pitch_rad)
            sin_p = math.sin(pitch_rad)  # NOQA
            k = right
            yaw_r = (yaw * cos_p + np.cross(k, yaw) *
                     sin_p + k * (np.dot(k, yaw) * (1.0 - cos_p)))  # NOQA

        new_pos = eye + yaw_r

        (
            self.camera_pos.x,
            self.camera_pos.y,
            self.camera_pos.z
        ) = _decimal(new_pos[0]), _decimal(new_pos[1]), _decimal(new_pos[2])

        self.Refresh(False)

    def zoom(self, delta, *_):
        # Move camera_eye along forward direction (toward/away from camera_pos)
        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        step = delta * _decimal(Config.zoom.sensitivity)
        move = (forward / fn) * float(step)

        # If moving would invert eye and pos, prevent crossing pos
        if np.linalg.norm(forward) - np.linalg.norm(move) < 1e-6:
            # clamp to a small distance to avoid crossing
            move = forward * (0.999 / np.linalg.norm(forward))

        new_eye = eye + move
        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z
        ) = _decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2])

        self.Refresh(False)

    def walk(self, dx, dy):
        # Use camera forward vector (from eye to pos).
        # Move both camera_pos and camera_eye.
        look_dx = dx

        if dy == 0.0:
            self.look(-look_dx * _decimal(10.0), _decimal(0.0))
            return

        dx *= _decimal(Config.walk.sensitivity)
        dy *= _decimal(Config.walk.sensitivity)

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            # degenerate, nothing to do
            return

        forward = forward / fn

        # Project forward onto XZ (ground) plane so walking does not change height
        forward_ground = np.array([forward[0], 0.0, forward[2]],
                                  dtype=np.dtypes.Float64DType)

        gf = np.linalg.norm(forward_ground)
        if gf < 1e-6:
            # looking straight up/down: fallback to world -Z so walking still works
            forward_ground = np.array([0.0, 0.0, -1.0],
                                      dtype=np.dtypes.Float64DType)
        else:
            forward_ground = forward_ground / gf

        # compute right consistent with pan/OnDraw: right = cross(world_up, forward_ground)
        world_up = np.array([0.0, 1.0, 0.0],
                            dtype=np.dtypes.Float64DType)

        right = np.cross(world_up, forward_ground)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0],
                             dtype=np.dtypes.Float64DType)
        else:
            right = right / rn

        # Build desired move from input
        input_mag = math.sqrt((dx * dx) + (dy * dy))
        if input_mag == 0:
            return

        move_dir = right * float(dx) + forward_ground * float(dy)

        mdn = np.linalg.norm(move_dir)
        if mdn < 1e-6:
            return

        move_dir = move_dir / mdn

        # Make total movement proportional to the original input magnitude
        move = move_dir * (input_mag * Config.walk.speed)

        new_eye = eye + move
        new_pos = pos + move

        (
            self.camera_eye.x,
            self.camera_eye.y,
            self.camera_eye.z,
            self.camera_pos.x,
            self.camera_pos.y,
            self.camera_pos.z
        ) = (
            _decimal(new_eye[0]),
            _decimal(new_eye[1]),
            _decimal(new_eye[2]),
            _decimal(new_pos[0]),
            _decimal(new_pos[1]),
            _decimal(new_pos[2])
        )

        self.look(-(look_dx * _decimal(20.0)), _decimal(0.0))

    def pan(self, dx, dy):
        # Translate both camera_pos and camera_eye in camera's right/up directions
        dx *= _decimal(Config.pan.sensitivity)
        dy *= _decimal(Config.pan.sensitivity)

        dy = -dy

        move = Point(dx, dy, _decimal(0.0))
        angle = Angle.from_points(self.camera_pos, self.camera_eye)

        move @= angle

        self.camera_eye += move
        self.camera_pos += move

        self.Refresh(False)

    @staticmethod
    def draw_grid():
        GRID_SIZE = 1000
        GRID_STEP = 50

        # --- Tiles ---
        TILE_SIZE = GRID_STEP
        HALF = GRID_SIZE
        for x in range(-HALF, HALF, TILE_SIZE):
            for y in range(-HALF, HALF, TILE_SIZE):
                # Alternate coloring for checkerboard effect
                is_even = ((x // TILE_SIZE) + (y // TILE_SIZE)) % 2 == 0
                if is_even:
                    GL.glColor4f(0.8, 0.8, 0.8, 0.4)
                else:
                    GL.glColor4f(0.3, 0.3, 0.3, 0.4)

                GL.glBegin(GL.GL_QUADS)
                GL.glVertex3f(x, 0, y)
                GL.glVertex3f(x, 0, y + TILE_SIZE)
                GL.glVertex3f(x + TILE_SIZE, 0, y + TILE_SIZE)
                GL.glVertex3f(x + TILE_SIZE, 0, y)
                GL.glEnd()

    def OnDraw(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        forward = (self.camera_pos - self.camera_eye).as_numpy

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            forward = np.array([0.0, 0.0, -1.0],
                               dtype=np.dtypes.Float64DType)
        else:
            forward = forward / fn

        temp_up = np.array([0.0, 1.0, 0.0],
                           dtype=np.dtypes.Float64DType)

        right = np.cross(temp_up, forward)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0],
                             dtype=np.dtypes.Float64DType)
        else:
            right = right / rn

        up = np.cross(forward, right)  # NOQA

        un = np.linalg.norm(up)
        if un < 1e-6:
            up = np.array([0.0, 1.0, 0.0],
                          dtype=np.dtypes.Float64DType)
        else:
            up = up / un

        GLU.gluLookAt(self.camera_eye.x, self.camera_eye.y, self.camera_eye.z,
                      self.camera_pos.x, self.camera_pos.y, self.camera_pos.z,
                      up[0], up[1], up[2])

        GL.glPushMatrix()

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

        for wire in self.wires:
            if wire.is_selected:
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [1.0, 1.0, 1.0, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.8, 0.8, 0.8, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
                GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 100.0)

            for i, (normals, triangles, triangle_count) in enumerate(wire.triangles):
                GL.glColor4f(*wire.colors[i])

                GL.glVertexPointer(3, GL.GL_DOUBLE, 0, triangles)
                GL.glNormalPointer(GL.GL_DOUBLE, 0, normals)

                GL.glDrawArrays(GL.GL_TRIANGLES, 0, triangle_count)

            if wire.is_selected:
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
                GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

                GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
                GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

        self.draw_grid()

        GL.glPopMatrix()

        self.SwapBuffers()


class App(wx.App):
    _frame = None
    _canvas: Canvas = None

    def OnInit(self):
        self._frame = wx.Frame(None, wx.ID_ANY, size=(1280, 1024))
        self._canvas = Canvas(self._frame)
        self._frame.Show()

        wx.BeginBusyCursor()
        wx.EndBusyCursor()

        return True


if __name__ == '__main__':
    app = App()
    app.MainLoop()
