
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
    from scipy.spatial.transform import Rotation as _Rotation
except ImportError:
    raise ImportError('the scipy library is needed to run this code. '
                      '`pip install scipy`')

from OpenGL import GLU
from OCP.gp import gp_Vec, gp
from OCP.TopAbs import TopAbs_REVERSED
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from wx import glcanvas
import threading
from decimal import Decimal as _Decimal
import numpy as np
import math


import pick_full_pipeline


MOUSE_NONE = 0x00000000
MOUSE_LEFT = 0x00000001
MOUSE_MIDDLE = 0x00000002
MOUSE_RIGHT = 0x00000004
MOUSE_AUX1 = 0x00000008
MOUSE_AUX2 = 0x00000010
MOUSE_WHEEL = 0x00000020

MOUSE_REVERSE_X_AXIS = 0x80000000
MOUSE_REVERSE_Y_AXIS = 0x40000000
MOUSE_REVERSE_WHEEL_AXIS = 0x20000000


# ********************* CONFIG SETTINGS *********************

class Config:
    class modeling:
        smooth_wires = True
        smooth_housings = False
        smooth_bundles = True
        smooth_transitions = True
        smooth_terminals = False
        smooth_cpa_locks = False
        smooth_tpa_locks = False
        smooth_boots = True
        smooth_covers = False
        smooth_splices = False
        smooth_markers = True
        smooth_seals = False

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
        sensitivity = 0.4

    class pan_tilt:
        mouse = MOUSE_LEFT
        up_key = ord('o')
        down_key = ord('l')
        left_key = ord('k')
        right_key = ord(';')
        sensitivity = 0.2

    class truck_pedistal:
        mouse = MOUSE_RIGHT | MOUSE_REVERSE_X_AXIS
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
        mouse = MOUSE_WHEEL  # | MOUSE_REVERSE_WHEEL_AXIS
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

        self._x = x
        self._y = y
        self._z = z

    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = value

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = value

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = value

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

    def __imul__(self, other: _decimal) -> Self:
        self.x *= other
        self.y *= other
        self.z *= other

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

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
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

        angle = _angle.Angle.from_points(origin, self)
        angle.x = x_angle
        angle.y = y_angle
        angle.z = z_angle

        p1 = self
        p2 = origin
        p3 = p1 - p2
        p3 @= angle
        p3 += p2

        self.x, self.y, self.z = [_decimal(float(item)) for item in p3]

    def get_angle(self, origin: "Point") -> "_angle.Angle":
        return _angle.Angle.from_points(origin, self)

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


class _point:

    Point = Point


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

    @property
    def inverse(self):
        R = self._R.inv()
        return Angle(R)

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

    def __imatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T
            other.x = _decimal(float(values[0]))
            other.y = _decimal(float(values[1]))

            other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __rmatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T
            other.x = _decimal(float(values[0]))
            other.y = _decimal(float(values[1]))
            other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __matmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other = other @ self._R.as_matrix().T
        elif isinstance(other, _point.Point):
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
    def from_matrix(cls, matrix: np.ndarray):
        R = _Rotation.from_matrix(matrix)  # NOQA
        return cls(R)

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
    def from_points(cls, p1: "_point.Point", p2: "_point.Point") -> "Angle":
        # the sign for all of the verticies in the array needs to be flipped in
        # order to handle the -Z axis being near
        p1 = -p1.as_numpy
        p2 = -p2.as_numpy

        f = p2 - p1

        fn = np.linalg.norm(f)
        if fn < 1e-6:
            return cls.from_euler(0.0, 0.0, 0.0)

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
        return cls(R)


class _angle:

    Angle = Angle


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

    def __init__(self, p1: _point.Point,
                 p2: _point.Point | None = None,
                 length: _decimal | None = None,
                 angle: _angle.Angle | None = None):

        self._p1 = p1

        if p2 is None:
            if None in (length, angle):
                raise ValueError('If an end point is not supplied '
                                 'then the "length", "x_angle", "y_angle" and '
                                 '"z_angle" parameters need to be supplied')

            p2 = _point.Point(length, _decimal(0.0), _decimal(0.0))
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
    def p1(self) -> _point.Point:
        return self._p1

    @property
    def p2(self) -> _point.Point:
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

    def get_angle(self, origin: _point.Point) -> _angle.Angle:
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

    def set_angle(self, angle: _angle.Angle, origin: _point.Point) -> None:
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

    def point_from_start(self, distance: _decimal) -> _point.Point:
        line = Line(self._p1.copy(), None,
                    distance, self.get_angle(self._p1))

        return line.p2

    @property
    def center(self) -> _point.Point:
        x = (self._p1.x + self._p2.x) * ZERO_5
        y = (self._p1.y + self._p2.y) * ZERO_5
        z = (self._p1.z + self._p2.z) * ZERO_5
        return _point.Point(x, y, z)

    def __iter__(self) -> Iterable[_point.Point]:
        return iter([self._p1, self._p2])

    def get_rotated_line(self, angle: _decimal, pivot: _point.Point) -> "Line":
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

        line = self.get_rotated_line(_decimal(180), _point.Point(x, y, _decimal(0.0)))
        line._p1, line._p2 = line._p2, line._p1

        return line

    @staticmethod
    def _rotate_point(origin: _point.Point, point: _point.Point, angle: _decimal) -> _point.Point:
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
        return _point.Point(qx, qy)


class _line:

    Line = Line


# wires are constructed along the positive Z axis
#             y+
#             |  Z+
#             | /
# x+ ------ center ------ x-
#           / |
#         Z-  |
#             Y-

def get_triangles(ocp_mesh):
    loc = TopLoc_Location()
    mesh = BRepMesh_IncrementalMesh(theShape=ocp_mesh.wrapped, theLinDeflection=0.001,
                                    isRelative=True, theAngDeflection=0.1, isInParallel=True)

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

    return (np.array(normals, dtype=np.dtypes.Float64DType).reshape(-1, 3),
            np.array(triangles, dtype=np.dtypes.Float64DType),
            triangle_count)


def get_smooth_triangles(ocp_mesh):
    loc = TopLoc_Location()
    BRepMesh_IncrementalMesh(theShape=ocp_mesh.wrapped, theLinDeflection=0.001,
                             isRelative=True, theAngDeflection=0.1, isInParallel=True)

    ocp_mesh_vertices = []
    triangles = []
    offset = 0
    for facet in ocp_mesh.faces():
        if not facet:
            continue

        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA

        if not poly_triangulation:
            continue

        trsf = loc.Transformation()

        node_count = poly_triangulation.NbNodes()
        for i in range(1, node_count + 1):
            gp_pnt = poly_triangulation.Node(i).Transformed(trsf)
            pnt = (gp_pnt.X(), gp_pnt.Y(), gp_pnt.Z())
            ocp_mesh_vertices.append(pnt)

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
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    norms = np.where(norms <= eps, 1.0, norms)
    return v / norms


def compute_face_normals(v0, v1, v2):
    return np.cross(v1 - v0, v2 - v0)


def compute_vertex_normals(vertices: np.ndarray, faces: np.ndarray,
                           method: str = "angle") -> np.ndarray:

    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]

    face_normals = compute_face_normals(v0, v1, v2)  # (F,3)

    N = vertices.shape[0]
    accum = np.zeros((N, 3), dtype=np.dtypes.Float64DType)

    if method == "area":
        # area-weighted accumulation
        # (face_normals magnitude ~ 2 * area * unit_normal)
        np.add.at(accum, faces[:, 0], face_normals)
        np.add.at(accum, faces[:, 1], face_normals)
        np.add.at(accum, faces[:, 2], face_normals)

    elif method == "angle":
        # angle-weighted accumulation
        # edges for corner angles
        e0 = v1 - v0
        e1 = v2 - v1
        e2 = v0 - v2

        def corner_angle(a, b):
            na = np.linalg.norm(a, axis=1)
            nb = np.linalg.norm(b, axis=1)
            denom = na * nb
            denom = np.where(denom == 0, 1.0, denom)
            cosang = np.sum(a * b, axis=1) / denom
            cosang = np.clip(cosang, -1.0, 1.0)
            return np.arccos(cosang)

        ang0 = corner_angle(-e2, e0)
        ang1 = corner_angle(-e0, e1)
        ang2 = corner_angle(-e1, e2)

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
    v_normals = compute_vertex_normals(vertices, faces, method=method)  # (N,3)

    positions_flat = vertices[faces].reshape(-1, 3)
    normals_flat = v_normals[faces].reshape(-1, 3)

    return (np.ascontiguousarray(normals_flat, dtype=np.dtypes.Float64DType),
            np.ascontiguousarray(positions_flat, dtype=np.dtypes.Float64DType))


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


class GLObject:
    """
    Base class for objects that are to be rendered

    This class needs to be subclassed
    """

    def __init__(self):
        # models is a list of build123d objects
        self.models = []

        # (normals, triangles, triangle_count)
        self.triangles = []

        self.is_selected = False

        # a color for each item in the trinagles array
        try:
            _ = self.colors
        except AttributeError:
            self.colors = []

        # This should be populated with 2 Point instances
        self.hit_test_rect = []

    @staticmethod
    def get_housing_triangles(model):
        if Config.modeling.smooth_housings:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_bundle_triangles(model):
        if Config.modeling.smooth_bundles:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_transition_triangles(model):
        if Config.modeling.smooth_transitions:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_terminal_triangles(model):
        if Config.modeling.smooth_terminals:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_cpa_lock_triangles(model):
        if Config.modeling.smooth_cpa_locks:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_tpa_lock_triangles(model):
        if Config.modeling.smooth_tpa_locks:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_boot_triangles(model):
        if Config.modeling.smooth_boots:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_cover_triangles(model):
        if Config.modeling.smooth_covers:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_splice_triangles(model):
        if Config.modeling.smooth_splices:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_wire_marker_triangles(model):
        if Config.modeling.smooth_markers:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_seal_triangles(model):
        if Config.modeling.smooth_seals:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    @staticmethod
    def get_wire_triangles(model):
        if Config.modeling.smooth_wires:
            return get_smooth_triangles(model)
        else:
            return get_triangles(model)

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self.hit_test_rect

        return p1 <= point <= p2


'''
Common camera movement terms
                                                          
                                 DOLLY
                                                                                
                              -==-                                              
                         .+=:       .=                                          
                       +........-.     +        :+-.   :=:                      
                     *............::     .    *-----.      ::                   
                    -...............:     :+...........-     -                  
                    =...............:: :-+...............:.    -                
                    =...............::--*.................:-    -               
                    +...............::.+..................:::   :                   
                     =.................+ .................::::   :              
                      -................=:..................:::.. :               
                        =.............-+=...................:.. :               
                         =+.........:*:-=*...................-..                
                          *... ====-------+:................:+                  
                          *.....:::.    .:--*:.............=                    
                .-*#%%#*  #.............:::.  .+-.......-=                      
        =*#%#######%%=    =.....................:- .  .                         
        #**################:.....................:  ::+=-:-  .+-                
        #*******###########-.....................- -+....:   = *                
       .****%###*##########......................--:-...:   =  *                
       -#**    .#%#####*###=:::..................-*+-::::   .  =                
       .-           .:*%#####**#=:...............-**-:--.  *  -       :.        
                            +%######*++-.........=-=%-:-:..+  #:     -**+       
                                   :#%####**#-...=#####*--:+ #******#****#      
                                         :#%####**########%%#**************:    
                                               -%#*###***********************   
                                                     :#%####*****************#  
                                                           .*%##%**********##*# 
                                                               #******#**##-    
                                                              **#***#=          
                                                             -#+.               
                            
                                 PEDISTAL
                                            **                                  
                                         ******=                                
                                      ***********.                              
                                  .#***************                             
                                     .=##***********=                           
                                       -#********#%#*#                          
                                       -#*******-...:=-=-                       
                                       =#*****.....::::-    -                   
                                  +----+#***:......::::::    :                  
                                :------+#**=.......::::::     -                 
                                =:-----+#*+........:::::.:    :                 
                               -.:-----##*+........:::..:     :                 
                               .::-----+#**=.......:::.:     -                  
                                -:-----+#**#+.........-....:-                   
                                 :=:::-*#*+##%+-..::-----=:                     
                                 -...::+#.....::: ::::::.                       
                                 :...:-+#....::-:     -: :-:-=.                 
                                 -...:-+#....::-:  +::  -...   =                
                                 -...:-*#....::-:.+:-  +    .  :.               
                                 -...:-+#.....:-:-*-=::+    .  ..               
                                 :..::-+#...:::----*--:+.      +                
                                     . =#+-....:--:::-#:=.   :-                               
                                       -#*********                              
                                       -#********* .-+:                         
                                       -#************.                          
                                  #%#**************=                            
                                    =*************                              
                                       -********:                               
                                          :***=                                 
                                   
                                                     
                                   TRUCK
                                                           
                                     .::-.                                      
                                .-+       :                                     
                                -..+       -                                    
                                -...+       .                                   
                                :...::      -                                                              
                                 :....:      +                                  
                                 -....=:++-:.    .                              
                                  =...:-.=:        :                            
                                 - :..::..:+        .                           
                                 :- :.::....=       .                           
                                  :- =+-.....:       -   .**#+.                 
                                  -.:  +.....=             ******#=             
                                  =.:: .......-       #***************-         
                                  -..-. =.....=       +***************          
                                  ::..-  :....=       -***************          
                                :+##...- :....-       **********##***.          
            :*:         .-+#*********...-.:...=      .****#*=:   :#*#           
           =***  .-+*****************+...  .:.= .:*##+-.          .*=           
          ****************************+.:  -=:...--                             
         ******************************-: +:....    -                           
        **************************=.    -.=::    :==-=                          
      -********************+-            .=   =       *                         
       :#************=.                   - +.  .    -                          
          .*#*****                         +       =                            
              +#**+                          :--.                               
                 -#.                                                            
                                       
                           PAN
                           
                      *=+-      -                                               
                     %....+     -##--::.. :-                                    
                     =....:+   :....#        -                                  
                    .-.....:- -......+        -                                 
                     :......*=........*        :                                
                     =......==........:=       .                                
                     #......:-........:#        -                                      
                      #......+.........:*       .                                                     
                       #....+::.........#       :                               
                       =*-.=--#.........*       =                                     
                       +..:+:  --.......=      :                                
                       *.....:#  *.....%  ...=                                  
                       *........==-%-=*+=:.-                                    
                       *.........+         -                                    
                       *.........+         -                                    
                       #.........+  .*:+=    .*                                 
                        :+.......+ ==+:  *-:.   -                               
                          ==.....* @=: #-        -                              
                            +-...* ** +:         ..            :=+**:           
                              #:.*.:=.+.     .   +     *##*************#=       
                                #*.-*:= .  .    =       .-=+#**************#*.  
                                 .   :+        =           ***************+***# 
                                       --..:=-           -**************#       
                                                       =****************#       
                         -                          =******************#        
                     =#*#*                     -*#********************#         
                 =*****##:.          .:-=**#************************#+          
             -******************************************************            
           ******************************************************=              
           ************************************************#***.                
           +*******************************************#**#=                    
           -*******************************************:                        
            ********************************++**+-                              
            #**#    .:=+***##***###*+++-:.                                      
            *#*                                                                 
            -+                                                       
                       
                        TILT           
                                                              .=.               
                                                         :+####:                
                                                    -*#######+                  
                                                  *#########%:                  
                                --::::-=:        =#############:                
                .----.       ::.....::.:.::-.    +##############*               
             .-:....:.:-:-. -............::: =  .*################.             
            =..........:-  =.............:::. =.=##################=            
           =...........::-+..............:::- :++##%*###############=           
          -............:::=.................- .=#%:  +###############=          
          -............:::=.................: :*=     =*##############:         
          -..............:+................-  :=       :*#############%         
          -.............:---..............-  .+         :*#############*        
           -...........::---=............-..:+           =*############%        
            =:........-:---+ .=.......--:--+              +#############=       
              =+==++*++==--:::....- -:-#:                 -*#############       
              -...................-    +  ==+*-            *############%       
              -...................-   ---  =..:*           *############%       
              -...................-.-::::  ::----          +############%.      
              -...................-+*---..-. =::=          +############%.      
              :...................-*+:---:-: --:=          *############%       
              -...................--**--+::*.:-=:         .*############%       
              :...................-----*=+--+ :=          =*############*       
                     ... ........                        .+############%.       
                                                        -*#############*         
                                               ..      =*##############          
                                               :*#   +##############%.          
                                                +###*##############%            
                                                =#################%             
                                                .*###############*                    
                                                 +#############*                 
                                                 .*###########                   
                                                    :+#######*                  
                                                          :+###+                

'''


class Canvas(glcanvas.GLCanvas):
    def __init__(self, parent, size=(-1, -1)):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size)

        self.init = False
        self.context = glcanvas.GLContext(self)

        self.viewMatrix = None
        self.size = None

        self.WIDTH = size[0]
        self.HEIGHT = size[1]
        self.ASPECT = float(self.WIDTH) / self.HEIGHT  # desired aspect ratio

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

        self.camera_pos = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height),
                                       _decimal(0.0))

        self.camera_eye = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height + 0.5),
                                       _decimal(75.0))

        self.camera_angle = _angle.Angle.from_points(self.camera_pos, self.camera_eye)

        self.camera_position_angle = _angle.Angle.from_points(
            _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)), self.camera_pos)

        self._grid = None
        self.is_motion = False
        self.mouse_pos = None
        self.selected = None
        self.objects = []

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

        pan_tilt = Config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            remove_from_queue(self._process_look_key, key)
            return

        truck_pedistal = Config.truck_pedistal
        key = _process_key_event(keycode, truck_pedistal.up_key,
                                 truck_pedistal.down_key, truck_pedistal.left_key,
                                 truck_pedistal.right_key)
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

        pan_tilt = Config.pan_tilt
        key = _process_key_event(keycode, pan_tilt.up_key, pan_tilt.down_key,
                                 pan_tilt.left_key, pan_tilt.right_key)
        if key is not None:
            add_to_queue(self._process_look_key, key)
            return

        truck_pedistal = Config.truck_pedistal
        key = _process_key_event(keycode, truck_pedistal.up_key,
                                 truck_pedistal.down_key, truck_pedistal.left_key,
                                 truck_pedistal.right_key)
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
            if key == Config.pan_tilt.up_key:
                dy += 1.0
            elif key == Config.pan_tilt.down_key:
                dy -= 1.0
            elif key == Config.pan_tilt.left_key:
                dx -= 1.0
            elif key == Config.pan_tilt.right_key:
                dx += 1.0

        self.pan_tilt(_decimal(dx) * _decimal(factor),
                      _decimal(dy) * _decimal(factor))

    def _process_pan_key(self, factor, *keys):
        dx = 0.0
        dy = 0.0

        for key in keys:
            if key == Config.truck_pedistal.up_key:
                dy -= 3.0
            elif key == Config.truck_pedistal.down_key:
                dy += 3.0
            elif key == Config.truck_pedistal.left_key:
                dx -= 3.0
            elif key == Config.truck_pedistal.right_key:
                dx += 3.0

        self.truck_pedistal(_decimal(dx) * _decimal(factor),
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
        self.camera_pos = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height),
                                       _decimal(0.0))

        self.camera_eye = _point.Point(_decimal(0.0),
                                       _decimal(Config.settings.eye_height + 0.5),
                                       _decimal(75.0))

        self.camera_angle = _angle.Angle.from_points(self.camera_pos, self.camera_eye)

        self.camera_position_angle = _angle.Angle.from_points(
            _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)), self.camera_pos)

        self.Refresh(False)

    def _process_mouse(self, code):
        for config, func in (
            (Config.walk, self.walk),
            (Config.truck_pedistal, self.truck_pedistal),
            (Config.reset, self.reset),
            (Config.rotate, self.rotate),
            (Config.pan_tilt, self.pan_tilt),
            (Config.zoom, self.zoom)
        ):
            if config.mouse is None:
                continue

            if config.mouse & code:
                return func

        def _do_nothing_func(_, __):
            pass

        return _do_nothing_func

    def on_left_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        if not self.is_motion:
            x, y = evt.GetPosition()

            selected = pick_full_pipeline.handle_click_cycle(x, y, self.objects)
            if selected is not None:
                if self.selected is not None and selected != self.selected:
                    self.selected.is_selected = False

                self.selected = selected
                selected.is_selected = True
                self.Refresh(False)

            elif self.selected is not None:
                self.selected.is_selected = False
                self.selected = None
                self.Refresh(False)

            # p = self.get_world_coords(x, y)
            #
            # for obj in self.objects:
            #     if obj.hit_test(p):
            #         if self.selected is not None and obj != self.selected:
            #             self.selected.is_selected = False
            #
            #         self.selected = obj
            #         obj.is_selected = True
            #         self.Refresh(False)
            #         break
            # else:
            #     if self.selected is not None:
            #         self.selected.is_selected = False
            #         self.selected = None
            #         self.Refresh(False)

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
                self._process_mouse(MOUSE_LEFT)(dx, dy)
            if evt.MiddleIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_MIDDLE)(dx, dy)
            if evt.RightIsDown():
                self.is_motion = True
                self._process_mouse(MOUSE_RIGHT)(dx, dy)
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

    def get_world_coords(self, mx, my) -> _point.Point:
        self.SetCurrent(self.context)

        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        depth = GL.glReadPixels(float(mx), float(my), 1.0, 1.0,
                                GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)

        x, y, z = GLU.gluUnProject(float(mx), float(my), depth,
                                   modelview, projection, viewport)

        return _point.Point(_decimal(x), _decimal(y), _decimal(z))

    def on_erase_background(self, _):
        pass

    def on_size(self, event):
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        self.SetCurrent(self.context)

        width, height = self.size = size * self.GetContentScaleFactor()

        w = height * self.ASPECT  # w is width adjusted for aspect ratio
        left = (width - w) / 2.0
        print(left, w, height)



        GL.glViewport(0, 0, int(w), height)  #  fix up the viewport to maintain aspect ratio
        GL.glMatrixMode(GL.GL_PROJECTION)
        # GL.glLoadIdentity()
        GL.glOrtho(0, self.WIDTH, self.HEIGHT, 0, -1.0, 1.0)  # only the window is changing, not the camera
        GL.glMatrixMode(GL.GL_MODELVIEW)

        # self.Refresh(False)

    def on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.InitGL()
            self.init = True

        self.OnDraw()

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

    def rotate(self, dx, dy):
        """
        Moves the camera position keeping the focused point locked.
        """

        sens = _decimal(Config.rotate.sensitivity)

        if Config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        dx *= sens
        dy *= sens

        self.camera_eye = self._rotate_about(
            dx, dy, self.camera_eye.as_numpy, self.camera_pos.as_numpy)

        self.Refresh(False)

    @staticmethod
    def _rotate_about(dx, dy, p1, p2):
        """
        Moves the camera position keeping the focused point locked.
        """
        # This is a constant that can be adjusted. This is a hard limit
        # to prevent gimbal lock from occuring when looking straight up or
        # straight down. You can set it to a smaller number but do not increase
        # it past 89.9 otherwise gimbal lock can occur.
        max_pitch = 89.9

        offset = p1 - p2
        dist = np.linalg.norm(offset)

        if dist < 1e-6:
            return

        up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        def _rodrigues(v, k, angle_rad):
            k = k / np.linalg.norm(k)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)  # NOQA
            return ((v * cos_a) + (np.cross(k, v) * sin_a) +  # NOQA
                    (k * (np.dot(k, v)) * (1.0 - cos_a)))

        yaw_offset = _rodrigues(offset, up, math.radians(dx))
        yaw_offset_n = np.linalg.norm(yaw_offset)

        if yaw_offset_n < 1e-6:
            return

        yaw_dir = yaw_offset / yaw_offset_n

        horiz_len = math.hypot(yaw_dir[0], yaw_dir[2])
        cur_pitch_deg = _decimal(
            math.degrees(math.atan2(yaw_dir[1], horiz_len))
            )

        desired_pitch = cur_pitch_deg + dy
        if desired_pitch > max_pitch or desired_pitch < -max_pitch:
            # block pitch movement entirely (yaw still applies)
            dy = 0.0

        if abs(dy) < 1e-6:
            final_offset = yaw_dir * dist
        else:
            right = np.cross(yaw_dir, up)  # NOQA
            rn = np.linalg.norm(right)
            if rn < 1e-6:
                final_offset = yaw_dir * dist
            else:
                right = right / rn
                rotated = _rodrigues(yaw_offset, right, math.radians(dy))

                rnorm = np.linalg.norm(rotated)
                if rnorm < 1e-6:
                    final_offset = yaw_dir * dist
                else:
                    # explicitly restore original distance to avoid shrink/grow
                    final_offset = rotated * (dist / rnorm)

        new_point = p2 + final_offset

        return _point.Point(_decimal(
            new_point[0]), _decimal(new_point[1]), _decimal(new_point[2]))

    def pan_tilt(self, dx, dy):
        """
        Moves the camera position keeping the focused point locked.

        Pan and Tilt camera movements.
        """
        sens = _decimal(Config.pan_tilt.sensitivity)

        if Config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        dx *= sens
        dy *= sens

        self.camera_pos = self._rotate_about(
            dx, dy, self.camera_pos.as_numpy, self.camera_eye.as_numpy)

        self.Refresh(False)

    def zoom(self, delta, *_):
        """
        This has a similiar movement appearance as Dolly except there are hard
        limits as to how far it is able to move where as Dolly does not.
        This also doesn't change the camera position at all. It simply shinks
        or expands the distance between the focal point and the camera position.
        """
        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            raise RuntimeError('this should never happen')

        step = delta * _decimal(Config.zoom.sensitivity)
        move = (forward / fn) * float(step)

        # If moving would invert eye and pos, prevent crossing pos
        if delta > 0 and np.linalg.norm(forward) - np.linalg.norm(move) <= 0.1:
            return

        new_eye = eye + move

        self.camera_eye.x = _decimal(new_eye[0])
        self.camera_eye.y = _decimal(new_eye[1])
        self.camera_eye.z = _decimal(new_eye[2])

        self.Refresh(False)

    def walk(self, dx, dy):
        """
        This movement is a bit tricky to explain in terms of camera movement.
        If you think about what you do as a person when you walk this will
        mimick as close as I could get to that movement. so basically if you
        want to walk straight forward and back you get that from this function.
        That is the same as a Dolly camera movement.

        if you go left and right the movement you get is as if you are turning
        on the ball of your foot. This is comparable to the "Pan" movement of a
        camera.

        If you hold left or right and press up or down at the same time you get
        a combination of the 2 above movements. kind of like what it would be
        like when you walk in an arc to either left or right.
        """
        look_dx = dx

        if Config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        if dy == 0.0:
            self.pan_tilt(look_dx * _decimal(6.0), _decimal(0.0))
            return

        sens = _decimal(Config.walk.sensitivity)

        dx *= sens
        dy *= sens

        eye = self.camera_eye.as_numpy
        pos = self.camera_pos.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        forward = forward / fn

        forward_ground = np.array([forward[0], 0.0, forward[2]],
                                  dtype=np.dtypes.Float64DType)

        gf = np.linalg.norm(forward_ground)
        if gf < 1e-6:
            forward_ground = np.array([0.0, 0.0, -1.0],
                                      dtype=np.dtypes.Float64DType)
        else:
            forward_ground = forward_ground / gf

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

        move = move_dir * (input_mag * Config.walk.speed)

        new_eye = eye + move
        new_pos = pos + move

        self.camera_eye.x = _decimal(new_eye[0])
        self.camera_eye.y = _decimal(new_eye[1])
        self.camera_eye.z = _decimal(new_eye[2])
        self.camera_pos.x = _decimal(new_pos[0])
        self.camera_pos.y = _decimal(new_pos[1])
        self.camera_pos.z = _decimal(new_pos[2])

        self.pan_tilt(look_dx * _decimal(2.0), _decimal(0.0))

    def truck_pedistal(self, dx, dy):
        """
        this is as the function name states. It is a Truck (left right)
        and a Pedistal (up down) movement
        """

        if Config.truck_pedistal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.truck_pedistal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = _decimal(Config.truck_pedistal.sensitivity)
        dx *= sens
        dy *= sens

        move = _point.Point(dx, dy, _decimal(0.0))

        angle = _angle.Angle.from_points(self.camera_pos, self.camera_eye)

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

        for obj in self.objects:
            if obj.is_selected:
                GL.glLightfv(
                    GL.GL_LIGHT0, GL.GL_AMBIENT, [1.0, 1.0, 1.0, 1.0])

                GL.glLightfv(
                    GL.GL_LIGHT0, GL.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

                GL.glMaterialfv(
                    GL.GL_FRONT, GL.GL_AMBIENT, [0.8, 0.8, 0.8, 1.0])

                GL.glMaterialfv(
                    GL.GL_FRONT, GL.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

                GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 100.0)

            for i, (normals, triangles, triangle_count) in enumerate(obj.triangles):
                GL.glColor4f(*obj.colors[i])

                GL.glVertexPointer(3, GL.GL_DOUBLE, 0, triangles)
                GL.glNormalPointer(GL.GL_DOUBLE, 0, normals)

                GL.glDrawArrays(GL.GL_TRIANGLES, 0, triangle_count)

            if obj.is_selected:
                GL.glLightfv(
                    GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])

                GL.glLightfv(
                    GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])

                GL.glLightfv(
                    GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

                GL.glMaterialfv(
                    GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])

                GL.glMaterialfv(
                    GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])

                GL.glMaterialfv(
                    GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])

                GL.glMaterialf(
                    GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

        self.draw_grid()

        GL.glPopMatrix()

        self.SwapBuffers()


if __name__ == '__main__':
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

    app = App()
    app.MainLoop()
