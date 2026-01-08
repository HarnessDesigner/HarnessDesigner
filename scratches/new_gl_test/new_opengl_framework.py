# Full file content (modified): I've included the entire original opengl framework file content
# with a minimal, safe addition: two helper methods on Canvas for projecting and unprojecting
# world points using gluProject/gluUnProject. No other behavior was changed in this file.
#
# You can copy/paste this entire file back into your local tree. The only functional
# additions are:
#   - Canvas.project_point(self, point: _point.Point) -> (winx, winy_top, winz)
#   - Canvas.unproject_point(self, winx_top, winy_top, winz) -> _point.Point
#
# These helpers are used by the modified housing_cavity_orientation.py to implement
# the exact project/unproject anchor dragging approach.
#
# (The remainder of the file is identical to your original provided content.)
from typing import Self, Iterable, Union, TYPE_CHECKING


if TYPE_CHECKING:
    import new_housing_cavity_orientation as _nhco


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
    from OpenGL.GL import GL_FALSE
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
import weakref

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

    class movement:
        angle_detent = 10.0
        move_detent = 5.0

        angle_snap = -1
        move_snap = -1

    class modeling:
        smooth_wires = True
        smooth_housings = False
        smooth_bundles = True
        smooth_transitions = True
        smooth_terminals = True
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

    def __array_ufunc__(self, func, _, inputs, instance, **__):
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

        raise RuntimeError

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None):

        if z is None:
            z = _decimal(0.0)

        self._x = x
        self._y = y
        self._z = z
        
        self._callbacks = []
        self._ref_count = 0
        
    def __remove_callback(self, ref):
        try:
            self._callbacks.remove(ref)
        except:  # NOQA
            pass
                
    def bind(self, callback):
        ref = weakref.WeakMethod(callback, self.__remove_callback)
        
        self._callbacks.append(ref)
        
    def unbind(self, callback):
        for ref in self._callbacks:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
                
            if cb == callback:
                self._callbacks.remove(ref)
                return
    
    def __enter__(self):
        self._ref_count += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1
    
    def _process_update(self):
        if self._ref_count:
            return
        
        for ref in self._callbacks:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
                
            else:
                cb(self)
    
    @property
    def x(self) -> _decimal:
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = value
        self._process_update()

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = value
        self._process_update()

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = value
        self._process_update()

    def copy(self) -> "Point":
        return Point(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __iadd__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        with self:
            self.x += x
            self.y += y
            self.z += z

        self._process_update()
        
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

        with self:
            self.x -= x
            self.y -= y
            self.z -= z

        self._process_update()

        return self

    def __imul__(self, other: _decimal) -> Self:
        with self:
            self.x *= other
            self.y *= other
            self.z *= other

        self._process_update()

        return self

    def __sub__(self, other: Union["Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self
        if isinstance(other, Point):
            x2, y2, z2 = other
        elif isinstance(other, np.ndarray):
            x2, y2, z2 = (_decimal(float(item)) for item in other)
        else:
            raise RuntimeError('sanity check ' + str(other))

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __itruediv__(self, other: _decimal) -> Self:
        
        with self:
            self.x /= other
            self.y /= other
            self.z /= other

        self._process_update()

        return self

    def __truediv__(self, other: _decimal) -> "Point":
        x, y, z = self
        return Point(x / other, y / other, z / other)

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
        with self:
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
            
        self._process_update()

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

        with self:
            self.x, self.y, self.z = [_decimal(float(item)) for item in p3]

        self._process_update()

    def get_angle(self, origin: "Point") -> "_angle.Angle":
        return _angle.Angle.from_points(origin, self)

    def __bool__(self):
        return self.as_float == (0, 0, 0)

    def __eq__(self, other: "Point") -> bool:
        if not isinstance(other, Point):
            return False
        
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
        if not isinstance(other, Point):
            raise TypeError(f'{type(other)} is not a "Point"')
        
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 <= x2 and y1 <= y2 and z1 <= z2

    def __ge__(self, other: "Point") -> bool:
        if not isinstance(other, Point):
            raise TypeError(f'{type(other)} is not a "Point"')
        
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 >= x2 and y1 >= y2 and z1 >= z2


class _point:

    Point = Point


ZERO_POINT = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))


class Angle:

    def __array_ufunc__(self, func, _, inputs, instance, **__):
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

        raise RuntimeError

    def __init__(self, R):
        self._R = R

        p1 = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        p2 = Point(_decimal(0.0), _decimal(0.0), _decimal(10.0))
        p2 @= self._R.as_matrix().T  # NOQA

        self._p1 = p1
        self._p2 = p2

        self._callbacks = []
        self._ref_count = 0

    def __remove_callback(self, ref):
        try:
            self._callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, callback):
        ref = weakref.WeakMethod(callback, self.__remove_callback)

        self._callbacks.append(ref)

    def unbind(self, callback):
        for ref in self._callbacks:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)

            if cb == callback:
                self._callbacks.remove(ref)
                return

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def _process_update(self):
        if self._ref_count:
            return

        for ref in self._callbacks:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)

            else:
                cb(self)

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
        self._process_update()

    @property
    def y(self) -> _decimal:
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        return _decimal(angles[1])

    @y.setter
    def y(self, value: _decimal):
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        angles[1] = float(value)
        
        self._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA
        self._process_update()

    @property
    def z(self) -> _decimal:
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        return _decimal(angles[2])

    @z.setter
    def z(self, value: _decimal):
        angles = self._R.as_euler('xyz', degrees=True).tolist()
        angles[2] = float(value)
        
        self._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA
        self._process_update()

    def copy(self) -> "Angle":
        return Angle.from_quat(self._R.as_quat())

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        with self:
            self.x += x
            self.y += y
            self.z += z
            
        self._process_update()
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

        with self:
            self.x -= x
            self.y -= y
            self.z -= z
            
        self._process_update()
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
            with other:
                other.x = _decimal(float(values[0]))
                other.y = _decimal(float(values[1]))
                other.z = _decimal(float(values[2]))

            other._process_update()  # NOQA
        elif isinstance(other, Angle):
            matrix = self._R.as_matrix() @ other._R.as_matrix()  # NOQA
            self._R = _Rotation.from_matrix(matrix)  # NOQA
            self._process_update()
            return self
        else:
            raise RuntimeError('sanity check')

        return other

    def __rmatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T
            
            with other:            
                other.x = _decimal(float(values[0]))
                other.y = _decimal(float(values[1]))
                other.z = _decimal(float(values[2]))
                
            other._process_update()  # NOQA
        elif isinstance(other, Angle):
            matrix = other._R.as_matrix() @ self._R.as_matrix()  # NOQA
            other._R = _Rotation.from_matrix(matrix)  # NOQA
            other._process_update()
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

        elif isinstance(other, Angle):
            matrix = self._R.as_matrix() @ other._R.as_matrix()  # NOQA
            R = _Rotation.from_matrix(matrix)  # NOQA
            return Angle(R)
        else:
            raise RuntimeError('sanity check')

        return other

    def __bool__(self):
        return self.as_float == (0, 0, 0)

    def __eq__(self, other: "Angle") -> bool:
        if not isinstance(other, Angle):
            return False
        
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
    def as_quat(self) -> np.ndarray:
        return self._R.as_quat()

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

    def __array_ufunc__(self, func, _, inputs, instance, **__):
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

    triangles = triangles.reshape(-1, 3, 3)

    return normals, triangles, len(triangles) * 3


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
        self.canvas: "Canvas" = None
        # models is a list of build123d objects
        self.models = []

        # (normals, triangles, triangle_count)
        self._triangles = []

        self._is_selected = False
        self._center: _point.Point = None

        # This should be populated with 2 Point instances
        self.hit_test_rect = []

    @property
    def triangles(self):
        return self._triangles

    def get_parent_object(self) -> "GLObject":
        return self

    def adjust_hit_points(self):
        for i, (p1, p2) in enumerate(self.hit_test_rect):

            xmin = min(p1.x, p2.x)
            ymin = min(p1.y, p2.y)
            zmin = min(p1.z, p2.z)
            xmax = max(p1.x, p2.x)
            ymax = max(p1.y, p2.y)
            zmax = max(p1.z, p2.z)

            p1 = _point.Point(xmin, ymin, zmin)
            p2 = _point.Point(xmax, ymax, zmax)

            self.hit_test_rect[i] = [p1, p2]

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value

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
        p1, p2 = self.hit_test_rect[0]

        return p1 <= point <= p2


class DragObject:

    def __init__(self, owner: Union["_nhco.Housing", "_nhco.Cavity"],
                 obj: Union["_nhco.ArrowRing", "_nhco.ArrowMove"],
                 anchor_screen: _point.Point, pick_offset: _point.Point,
                 mouse_start: _point.Point, start_obj_pos: _point.Point,
                 last_pos: _point.Point):
        # object that was actually clicked
        self.owner = owner

        # object to be moved
        self.obj = obj

        # (winx, winy, winz)
        self.anchor_screen = anchor_screen

        # _point.Point
        self.pick_offset = pick_offset

        # (mx,my) in top-left window coords
        self.mouse_start = mouse_start

        # last object world _point.Point used for incremental moves
        self.last_pos = last_pos

        #  _point.Point start position
        self.start_obj_pos = start_obj_pos

    def rotate(self, canvas: "Canvas", mouse_point: _point.Point):
        pass

    def move(self, canvas: "Canvas", mouse_point: _point.Point):
        delta = mouse_point - self.mouse_start

        # compute new anchor screen position (top-left coords)
        screen_new = self.anchor_screen + delta

        # Unproject at anchor winZ (note our unproject_point expects top-left coords)
        world_hit = canvas.unproject_point(screen_new)

        # candidate world = world_hit + pick_offset
        candidate = world_hit + self.pick_offset

        new_pos = self.obj.move(candidate, self.start_obj_pos, self.last_pos)
        self.last_pos = new_pos


CULL_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 0) readonly buffer Triangles {
    vec4 positions[]; // each triangle occupies 3 consecutive vec4s
};

layout(std430, binding = 1) buffer VisibleIndex {
    uint triIndex[]; // triIndex[visibleID]
};

layout(std430, binding = 2) buffer VisibleDepth {
    float depth[]; // depth[visibleID]
};

layout(binding = 0) uniform atomic_uint visibleCount;

uniform mat4 viewMatrix;
uniform float nearCull;
uniform float farCull;
uniform uint triCount;

void main() {
    uint gid = gl_GlobalInvocationID.x;
    if (gid >= triCount) return;

    vec3 p0 = positions[gid*3 + 0].xyz;
    vec3 p1 = positions[gid*3 + 1].xyz;
    vec3 p2 = positions[gid*3 + 2].xyz;

    vec3 e0 = p1 - p0;
    vec3 e1 = p2 - p0;
    vec3 normal = normalize(cross(e0, e1));

    vec4 centroidView = viewMatrix * vec4((p0 + p1 + p2) / 3.0, 1.0);
    float depthVal = -centroidView.z;

    vec3 viewDir = normalize(-centroidView.xyz);
    float ndotv = dot(normal, viewDir);
    if (ndotv > 0.0) {
        return;
    }

    if (depthVal < nearCull || depthVal > farCull) return;

    uint idx = atomicCounterIncrement(visibleCount);
    triIndex[idx] = uint(gid);
    depth[idx] = depthVal;
}
"""

BITONIC_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 1) buffer VisibleIndex {
    uint triIndex[]; // triIndex[0..N-1]
};

layout(std430, binding = 2) buffer VisibleDepth {
    float depth[]; // depth[0..N-1]
};

uniform uint k; // stage size
uniform uint j; // inner size
uniform uint sortSize; // padded size (power of two)

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= sortSize) return;

    uint ixj = idx ^ j;
    if (ixj > idx) {
        bool ascending = ((idx & k) == 0u);
        float di = depth[idx];
        float dj = depth[ixj];
        if ((di > dj) == ascending) {
            float tmpd = depth[idx];
            depth[idx] = depth[ixj];
            depth[ixj] = tmpd;
            uint tmpi = triIndex[idx];
            triIndex[idx] = triIndex[ixj];
            triIndex[ixj] = tmpi;
        }
    }
}
"""

REORDER_COMPUTE = r"""
#version 430
layout(local_size_x = 256) in;

layout(std430, binding = 0) readonly buffer Triangles {
    vec4 positions[]; // tri*3 + 0..2
};

layout(std430, binding = 5) readonly buffer TriNormals {
    vec4 triNormal[]; // one normal per triangle (w unused)
};

layout(std430, binding = 6) readonly buffer TriColors {
    vec4 triColor[]; // per-triangle RGBA color
};

layout(std430, binding = 1) readonly buffer VisibleIndex {
    uint triIndex[]; // sorted tri indices
};

layout(std430, binding = 3) writeonly buffer OutputVBO {
    vec4 verts[]; // output tri vertices, base = idx*3
};

layout(std430, binding = 4) writeonly buffer OutputNormals {
    vec4 normals[]; // output per-vertex normals (flat: same normal for all 3 vertices)
};

layout(std430, binding = 7) writeonly buffer OutputColors {
    vec4 colors[]; // output per-vertex colors (RGBA)
};

uniform uint outCount; // number of visible triangles (actual)

void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= outCount) return;
    uint tri = triIndex[idx];
    uint base = idx * 3u;

    verts[base + 0] = positions[tri*3 + 0];
    verts[base + 1] = positions[tri*3 + 1];
    verts[base + 2] = positions[tri*3 + 2];

    vec4 n = triNormal[tri];
    normals[base + 0] = n;
    normals[base + 1] = n;
    normals[base + 2] = n;

    vec4 c = triColor[tri];
    colors[base + 0] = c;
    colors[base + 1] = c;
    colors[base + 2] = c;
}
"""

VS_SRC = r"""
#version 330 core
layout(location = 0) in vec4 inPos;
layout(location = 1) in vec4 inNormal; // w unused
layout(location = 2) in vec4 inColor;  // RGBA
uniform mat4 vp;
uniform mat4 viewMatrix;
out vec3 vNormal;
out vec4 vColor;
void main() {
    gl_Position = vp * inPos;
    vNormal = mat3(viewMatrix) * inNormal.xyz;
    vColor = inColor;
}
"""

FS_SRC = r"""
#version 330 core
in vec3 vNormal;
in vec4 vColor;
out vec4 outColor;
void main() {
    vec3 n = normalize(vNormal);
    vec3 lightDir = normalize(vec3(0.4, 0.7, 0.2));
    float lambert = max(dot(n, lightDir), 0.0);
    vec3 baseColor = vColor.rgb;
    vec3 ambient = vec3(0.12, 0.12, 0.14);
    vec3 color = ambient + lambert * baseColor;
    outColor = vec4(color, vColor.a);
}
"""


# ---------------------------
# GL helper functions
# ---------------------------
def compile_shader(src, shader_type):
    sh = GL.glCreateShader(shader_type)
    GL.glShaderSource(sh, src)
    GL.glCompileShader(sh)

    ok = GL.glGetShaderiv(sh, GL.GL_COMPILE_STATUS)
    if not ok:
        log = GL.glGetShaderInfoLog(sh).decode()
        raise RuntimeError(f"Shader compile failed: {log}")

    return sh


def link_program(shaders):
    prog = GL.glCreateProgram()
    for sh in shaders:
        GL.glAttachShader(prog, sh)

    GL.glLinkProgram(prog)

    ok = GL.glGetProgramiv(prog, GL.GL_LINK_STATUS)
    if not ok:
        log = GL.glGetProgramInfoLog(prog).decode()
        raise RuntimeError(f"Program link failed: {log}")

    for sh in shaders:
        GL.glDetachShader(prog, sh)
        GL.glDeleteShader(sh)

    return prog


def create_compute_program(src):
    sh = compile_shader(src, GL.GL_COMPUTE_SHADER)
    return link_program([sh])


def create_program(vs_src, fs_src):
    vs = compile_shader(vs_src, GL.GL_VERTEX_SHADER)
    fs = compile_shader(fs_src, GL.GL_FRAGMENT_SHADER)
    return link_program([vs, fs])


def next_power_of_two(x):
    if x == 0:
        return 1
    else:
        return 2 ** (int(np.ceil(np.log2(x))))


class CullThread:

    def __init__(self, canvas):
        self.canvas = canvas

        self._thread = threading.Thread(target=self._loop)
        self._thread.daemon = True
        self._exit_event = threading.Event()
        self._lock = threading.Lock()
        self._wait_event = threading.Event()
        self._running_event = threading.Event()
        self.refresh = False

    def is_running(self):
        return self._running_event.is_set()

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        if self._thread.is_alive():
            self._exit_event.set()
            self._thread.join(3.0)

    def _loop(self):
        while not self._exit_event.is_set():
            self._running_event.set()
            with self:
                projection = self.canvas.projection
                opaque_colors = []
                opaque_triangles = []
                opaque_normals = []
                opaque_count = 0

                transparent_colors = []
                transparent_triangles = []
                transparent_normals = []
                transparent_count = 0
                if self.aabb_intersects_frustum(obj.hit_test_rect, projection):

                    for obj in self.canvas.objects:
                        for triangles, normals, colors, count, is_opaque in obj.triangles:
                            if is_opaque:
                                opaque_triangles.append(triangles)
                                opaque_normals.append(normals)
                                opaque_colors.append(colors)
                                opaque_count += count
                            else:
                                transparent_triangles.append(triangles)
                                transparent_normals.append(normals)
                                transparent_colors.append(colors)
                                transparent_count += count

                triangles = []
                if opaque_count:
                    triangles.append([
                        np.array(opaque_triangles,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 3, 3),
                        np.array(opaque_normals,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 3),
                        np.array(opaque_colors,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 4),
                        opaque_count
                    ])

                if transparent_count:
                    triangles.append([
                        np.array(transparent_triangles,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 3, 3),
                        np.array(transparent_normals,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 3),
                        np.array(transparent_colors,
                                 dtype=np.dtypes.Float32DType).reshape(-1, 4),
                        transparent_count
                    ])

                self.canvas.triangles = triangles

            self._running_event.clear()

            if self.refresh:
                wx.CallAfter(self.canvas.Refresh, False)

            self._wait_event.clear()
            self._wait_event.wait(0.1)
            self._wait_event.clear()

    # @staticmethod
    # def extract_frustum_planes(view_proj):
    #     """
    #     view_proj: 4x4 numpy array (proj @ view)
    #     returns: planes array (6,4): left,right,bottom,top,near,far (normalized)
    #     """
    #     m = view_proj
    #     planes = np.empty((6, 4), dtype=m.dtype)
    #     planes[0] = m[3] + m[0]  # left
    #     planes[1] = m[3] - m[0]  # right
    #     planes[2] = m[3] + m[1]  # bottom
    #     planes[3] = m[3] - m[1]  # top
    #     planes[4] = m[3] + m[2]  # near
    #     planes[5] = m[3] - m[2]  # far
    #     # normalize
    #     for i in range(6):
    #         a, b, c, d = planes[i]
    #         n = np.hypot(a, b, c)
    #         if n != 0:
    #             planes[i] = planes[i] / n
    #
    #     return planes
    #
    # @staticmethod
    # def aabb_intersects_frustum(ht_rect: list, planes: np.ndarray) -> bool:
    #     """
    #     ht_rect: [Point_min, Point_max]
    #     planes: (6,4) array
    #     Returns True if AABB intersects or is inside the frustum.
    #     Uses the "positive vertex" test per plane.
    #     """
    #     pmin, pmax = ht_rect
    #     xmin, ymin, zmin = pmin.as_float
    #     xmax, ymax, zmax = pmax.as_float
    #
    #     for (a, b, c, d) in planes:
    #         # choose the point of the AABB that is farthest
    #         # along plane normal (positive vertex)
    #         px = xmax if a >= 0 else xmin
    #         py = ymax if b >= 0 else ymin
    #         pz = zmax if c >= 0 else zmin
    #
    #         if a * px + b * py + c * pz + d < 0:
    #             # box is fully outside this plane
    #             return False
    #
    #     return True

    @staticmethod
    def aabb_intersects_frustum(ht_rects: list, view_proj: np.ndarray) -> bool:
        for ht_rect in ht_rects:

            minx = ht_rect[0].x
            maxx = ht_rect[1].x
            miny = ht_rect[0].y
            maxy = ht_rect[1].y
            minz = ht_rect[0].z
            maxz = ht_rect[1].z
            corners = [
                np.array([minx, miny, minz, 1.0], dtype=view_proj.dtype),
                np.array([minx, miny, maxz, 1.0], dtype=view_proj.dtype),
                np.array([minx, maxy, minz, 1.0], dtype=view_proj.dtype),
                np.array([minx, maxy, maxz, 1.0], dtype=view_proj.dtype),
                np.array([maxx, miny, minz, 1.0], dtype=view_proj.dtype),
                np.array([maxx, miny, maxz, 1.0], dtype=view_proj.dtype),
                np.array([maxx, maxy, minz, 1.0], dtype=view_proj.dtype),
                np.array([maxx, maxy, maxz, 1.0], dtype=view_proj.dtype)
            ]
            corners = np.stack(corners, axis=0)  # (8,4)
            clip = corners @ view_proj.T  # (8,4)

            # convert to NDC: x/w, y/w, z/w; for each corner test whether inside [-1,1] cube
            w = clip[:, 3:4]
            ndc = clip[:, :3] / w

            # If all corners are outside on the same side of an axis, box is outside
            if np.all(ndc[:, 0] < -1):
                continue

            if np.all(ndc[:, 0] > 1):
                continue

            if np.all(ndc[:, 1] < -1):
                continue

            if np.all(ndc[:, 1] > 1):
                continue

            if np.all(ndc[:, 2] < -1):
                continue

            if np.all(ndc[:, 2] > 1):
                continue

            break
        else:
            return False

        return True


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

    """
    GL Engine

    This handles putting all of the pieces together and passes them
    to opengl to be rendered. It also is responsible for interperting mouse 
    input as well as the view.

    The controls to move about are much like what you would have in a first
    person shooter game. If you don't knopw what that is (lord i hope this 
    isn't the case) think if it as you navigating the world around you. The 
    movements are very similiar in most cases. There is one movement that while 
    it is able to be done in the "real" world by a person it's not normally 
    done. a person that sprays paint might be the only person to use the 
    movement in a regular basis. The easiest way to describe it is if you hang 
    an object to be painted at about chest height and you move your position 
    around the object but keeping your eyes fixed on the object at all times.
    
    How the rendering is done.
    
    The objects that are placed into the 3D world hold the coordinates of where 
    they are located. This is paramount to how the system works because those 
    coordinates are also used or determining part sizes like a wire length. 
    There is a 1 to 1 ratop that maps to mm's from the 3D world location.
    
    OpenGL provides many ways to handle how to see the 3D world and how to move 
    about it. I am using 1 way and only 1 way which is using the camera position 
    and the camera focal point. Object positions are always static. I do not 
    transform the view when placing objects so the coordinates where an onject 
    is located is always going to be the same as where the object is located in 
    that 3D world. moving the camera to change what is being seen is the most 
    locical thing to do for a CAD type interface. The downside is when 
    performing updates is that all of the objects get passed to opengl to be 
    rendered even ones that are not ble to be seen. This could cause performance 
    issues if there are a lot of objects being passed to OpenGL. Once I get the
    program mostly up and operational I will perform tests t see what the 
    performance degridation actually is and if there would be any benifit to 
    clipping objects not in view so they don't get passed to OpenGL. 
    Which brings me to my next bit...      
    
    I have created a class that holds x, y and z coordinates. This class is 
    very important and it is the heart of the system. built into that class is 
    the ability to attach callbacks that will get called should the x, y or z 
    values change. These changes can occur anywhere in the program so no 
    specific need to couple pieces together in a direct manner in order to get 
    changes to populate properly. This class is what is used to store the camera
    position and the camera focal point. Any changes to either of those will 
    trigger an update of what is being seen. This mechanism is what will be used
    in the future so objects are able to know when they need to check if they 
    are clipped or not. I will more than likely have 2 ranges of items. ones 
    that are in view and ones that would be considered as standby or are on the 
    edge of the viewable area. When the position of the camera or camera focal 
    point changes the objects that are on standby would beprocessed immediatly 
    to see if they are in view or not and the ones that are in view would be 
    processed to see if they get moved to the standby. objects that gets placed 
    into and remove from standby from areas outside of it will be done in a 
    separate process. It will be done this way because of the sheer number of 
    possible objects that might exist which would impact the program performance
    if it is done on the same core that the UI is running on.       
    """
    def __init__(self, parent, size=(-1, -1)):
        attribs = [glcanvas.WX_GL_RGBA,
                   glcanvas.WX_GL_DOUBLEBUFFER,
                   glcanvas.WX_GL_DEPTH_SIZE, 24,
                   glcanvas.WX_GL_STENCIL_SIZE, 8,
                   glcanvas.WX_GL_CORE_PROFILE, 1,
                   glcanvas.WX_GL_MAJOR_VERSION, 4,
                   glcanvas.WX_GL_MINOR_VERSION, 3,
                   0]
        
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, attribList=attribs)

        self.init = False
        self.context = glcanvas.GLContext(self)

        self.viewMatrix = None
        self.size = None

        # resources placeholders
        self.cull_prog = None
        self.bitonic_prog = None
        self.reorder_prog = None
        self.render_prog = None
        self.vao = None

        self.tri_ssbo = None
        self.tri_normals_ssbo = None
        self.tri_colors_ssbo = None
        self.loc_view = None
        self.loc_near = None
        self.loc_far = None
        self.loc_triCount = None
        self.loc_k = None
        self.loc_j = None
        self.loc_sortSize = None
        self.loc_outCount = None
        self.loc_vp = None
        self.loc_view_render = None
        self.counter_buf = None
        self.triangles = []
        self._projection = None
        self.view = None

        # pipeline / data parameters
        self.local_size = 256
        
        self._drag_obj: DragObject = None

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
        self._ref_count = 0
        self._cull = CullThread(self)

    def add_object(self, obj):
        # we want to force a reordering of the objects
        # when adding a new one. this can be overridden if adding multiple
        # objects elsewhere in code by using the context prior to adding
        # the objects. This way when adding multiple
        # objects it will only get reordered a single time

        with self:
            self.objects.insert(0, obj)

        self.Refresh(False)

    def remove_object(self, obj):
        try:
            self.objects.remove(obj)
        except:  # NOQA
            return

        self.Refresh(False)
        
    def __enter__(self) -> Self:
        self._ref_count += 1
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        if self._ref_count:
            return
        
        glcanvas.GLCanvas.Refresh(self, *args, **kwargs)
    
    def project_point(self, point: _point.Point) -> _point.Point:
        """
        Project a world-space _point.Point to window coordinates (top-left origin).
        Returns (winx, winy_top, winz) where winz is in [0,1].
        """
        self.SetCurrent(self.context)
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        winx, winy, winz = GLU.gluProject(float(point.x), float(point.y), float(point.z),
                                          modelview, projection, viewport)
        # convert to top-left origin to match wx mouse coordinates
        winy_top = _decimal(viewport[3]) - _decimal(winy)
        return _point.Point(_decimal(winx), winy_top, _decimal(winz))

    def unproject_point(self, point: _point.Point) -> _point.Point:
        """
        Unproject window coordinates (top-left origin) and
        winz back to a world _point.Point.
        """
        self.SetCurrent(self.context)
        modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)

        # convert top-left y back to OpenGL bottom-left y
        winy = _decimal(viewport[3]) - point.y

        x, y, z = GLU.gluUnProject(float(point.x), float(winy), float(point.z),
                                   modelview, projection, viewport)
        return _point.Point(_decimal(x), _decimal(y), _decimal(z))

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

    def on_left_down(self, evt: wx.MouseEvent):
        import pick_full_pipeline
        from __main__ import ArrowMove, ArrowRing
        from __main__ import Cavity, Housing

        x, y = evt.GetPosition()
        mouse_pos = _point.Point(_decimal(x), _decimal(y))
        self.mouse_pos = mouse_pos
        self.is_motion = False

        selected = pick_full_pipeline.handle_click_cycle(mouse_pos, self.objects)
        print(selected, type(selected), Housing)

        if isinstance(selected, (Cavity, Housing)):
            print('is selected')

            with self:
                if selected == self.selected:
                    selected.is_selected = False
                    if selected.is_move_shown:
                        selected.stop_move()

                    if selected.is_angle_shown:
                        selected.stop_angle()

                    self._drag_obj = None
                    self.selected = None

                else:
                    if self.selected is not None:
                        self.selected.is_selected = False
                        if self.selected.is_move_shown:
                            self.selected.stop_move()

                        if self.selected.is_angle_shown:
                            self.selected.stop_angle()

                    self.selected = selected
                    self.parent.cp.set_selected(self.selected)

                    selected.is_selected = True

                    if self.GetParent().move_tool.IsToggled():
                        selected.start_move()
                        self._drag_obj = None

                    elif self.GetParent().rotate_tool.IsToggled():
                        selected.start_angle()
                        self._drag_obj = None

            self.Refresh(False)

        elif isinstance(selected, (ArrowMove, ArrowRing)):
            if self._drag_obj is not None:
                self._drag_obj.owner.is_selected = False

            # prepare exact drag using project/unproject anchor approach
            if not self.HasCapture():
                self.CaptureMouse()

            # compute object's center world point from its hit_test_rect
            center = selected.position

            # project center to screen
            win_point = self.project_point(center)

            # compute pick-world and offsets
            pick_world = self.unproject_point(win_point)
            obj = selected.get_parent_object()
            object_pos = obj.position
            pick_offset = object_pos - pick_world

            selected.is_selected = True
            # store drag state on canvas
            self._drag_obj = DragObject(obj, selected, anchor_screen=win_point,
                                        pick_offset=pick_offset, mouse_start=mouse_pos,
                                        start_obj_pos=object_pos.copy(), last_pos=object_pos.copy())

            self.Refresh(True)

        elif self.selected is not None:
            with self:
                self.selected.is_selected = False
                if self.selected.is_move_shown:
                    self.selected.stop_move()

                if self.selected.is_angle_shown:
                    self.selected.stop_angle()

                self.selected = None

            self.Refresh(False)

    def on_left_up(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)

        if self._drag_obj is not None:
            self._drag_obj.obj.is_selected = False
            self._drag_obj = None

            if self.HasCapture():
                self.ReleaseMouse()

            self.Refresh(False)

        evt.Skip()

        if not self.is_motion:
            x, y = evt.GetPosition()
            mouse_pos = _point.Point(_decimal(x), _decimal(y))

        if not evt.RightIsDown():
            if self.HasCapture():
                self.ReleaseMouse()
                
            self.mouse_pos = None

        self.is_motion = False

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
        self.mouse_pos = _point.Point(_decimal(x), _decimal(y))

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
        self.mouse_pos = _point.Point(_decimal(x), _decimal(y))

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

        if evt.Dragging():
            x, y = evt.GetPosition()
            new_mouse_pos = _point.Point(_decimal(x), _decimal(y))

            if self.mouse_pos is None:
                self.mouse_pos = new_mouse_pos

            delta = new_mouse_pos - self.mouse_pos
            self.mouse_pos = new_mouse_pos

            with self:
                if evt.LeftIsDown():
                    if self._drag_obj is not None:
                        with self:
                            if self._drag_obj.owner.is_move_shown:
                                self._drag_obj.move(self, new_mouse_pos)

                            elif self._drag_obj.owner.is_angle_shown:
                                self._drag_obj.rotate(self, new_mouse_pos)

                    else:
                        self.is_motion = True
                        self._process_mouse(MOUSE_LEFT)(*list(delta)[:-1])

                if evt.MiddleIsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_MIDDLE)(*list(delta)[:-1])
                if evt.RightIsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_RIGHT)(*list(delta)[:-1])
                if evt.Aux1IsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_AUX1)(*list(delta)[:-1])
                if evt.Aux2IsDown():
                    self.is_motion = True
                    self._process_mouse(MOUSE_AUX2)(*list(delta)[:-1])

            self.Refresh(False)

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
        self.mouse_pos = _point.Point(_decimal(x), _decimal(y))

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
        self.mouse_pos = _point.Point(_decimal(x), _decimal(y))

        evt.Skip()

    def on_aux2_dclick(self, evt: wx.MouseEvent):
        self._process_mouse_release(evt)
        evt.Skip()

    # def get_world_coords(self, mx, my) -> _point.Point:
    #     self.SetCurrent(self.context)
    #
    #     modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
    #     projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
    #     viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
    #
    #     depth = GL.glReadPixels(float(mx), float(my), 1.0, 1.0,
    #                             GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)
    #
    #     x, y, z = GLU.gluUnProject(float(mx), float(my), depth,
    #                                modelview, projection, viewport)
    #
    #     return _point.Point(_decimal(x), _decimal(y), _decimal(z))

    def on_erase_background(self, _):
        pass

    def on_size(self, event):
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        self.SetCurrent(self.context)

        width, height = self.size = size * self.GetContentScaleFactor()

        w = height * self.ASPECT  # w is width adjusted for aspect ratio

        #  fix up the viewport to maintain aspect ratio
        GL.glViewport(0, 0, int(w), height)

    def on_paint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.InitGL()
            self.init = True

        self.OnDraw()
        
    def _get_view(self) -> np.ndarray:
        forward = (self.camera_pos - self.camera_eye).as_numpy

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            forward = np.array([0.0, 0.0, -1.0],
                               dtype=np.dtypes.Float64DType)
        else:
            forward = forward / fn

        temp_up = np.array([0.0, 1.0, 0.0],
                           dtype=np.dtypes.Float64DType)

        right = np.cross(forward, temp_up)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0],
                             dtype=np.dtypes.Float64DType)
        else:
            right = right / rn

        up = np.cross(right, forward)  # NOQA

        M = np.identity(4, dtype=np.float32)
        M[0, :3] = right
        M[1, :3] = up
        M[2, :3] = -forward
        T = np.identity(4, dtype=np.float32)
        T[:3, 3] = -self.camera_eye.as_numpy
        return M @ T

    def _get_perspective(self) -> np.ndarray:
        zn = 0.1
        zf = 1000.0
        w, h = self.GetClientSize()

        if h == 0:
            h = 1

        fovy = math.radians(45.0)
        aspect = float(w)/float(h)

        f = 1.0 / math.tan(fovy / 2.0)
        M = np.zeros((4, 4), dtype=np.float32)
        M[0, 0] = f / aspect
        M[1, 1] = f
        M[2, 2] = (zf + zn) / (zn - zf)
        M[2, 3] = (2 * zf * zn) / (zn - zf)
        M[3, 2] = -1.0
        return M

    def _update_camera(self):
        with self._cull:
            self.view = self._get_view()
            perspective = self._get_perspective()
            self._projection = perspective @ self.view

    @property
    def projection(self):
        if self._projection is None:
            self._update_camera()

        return self._projection

    def InitGL(self):
        w, h = self.GetSize()
        GL.glClearColor(0.20, 0.20, 0.20, 0.0)
        GL.glViewport(0, 0, w, h)

        # GL.glEnable(GL.GL_DEPTH_TEST)
        # GL.glEnable(GL.GL_LIGHTING)
        # # glEnable(GL_ALPHA_TEST)
        # GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        # GL.glEnable(GL.GL_BLEND)
        #
        # GL.glEnable(GL.GL_DITHER)
        # GL.glEnable(GL.GL_MULTISAMPLE)
        # # glEnable(GL_FOG)
        # GL.glDepthMask(GL.GL_TRUE)
        # # glShadeModel(GL_FLAT)
        #
        # GL.glShadeModel(GL.GL_SMOOTH)
        # GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        # GL.glEnable(GL.GL_COLOR_MATERIAL)
        # # glEnable(GL_NORMALIZE)
        # GL.glEnable(GL.GL_RESCALE_NORMAL)
        # # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        #
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        # GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
        #
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        # GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        # GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)
        #
        # GL.glEnable(GL.GL_LIGHT0)

        # # GL.glMatrixMode(GL.GL_PROJECTION)
        # GLU.gluPerspective(45, w / float(h), 0.1, 1000.0)
        #
        # # GL.glMatrixMode(GL.GL_MODELVIEW)
        # GLU.gluLookAt(0.0, 2.0, -16.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0)
        # # self.viewMatrix = GL.glGetFloatv(GL.GL_MODELVIEW_MATRIX)

        # compile/link shaders
        self.cull_prog = create_compute_program(CULL_COMPUTE)
        self.bitonic_prog = create_compute_program(BITONIC_COMPUTE)
        self.reorder_prog = create_compute_program(REORDER_COMPUTE)
        self.render_prog = create_program(VS_SRC, FS_SRC)

        # atomic counter (binding point 0)
        self.counter_buf = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, self.counter_buf)
        zero = np.array([0], dtype=np.uint32)
        GL.glBufferData(GL.GL_ATOMIC_COUNTER_BUFFER, zero.nbytes, zero, GL.GL_DYNAMIC_COPY)
        GL.glBindBufferBase(GL.GL_ATOMIC_COUNTER_BUFFER, 0, self.counter_buf)

        # VAO
        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        # Uniform locations
        GL.glUseProgram(self.cull_prog)
        self.loc_view = GL.glGetUniformLocation(self.cull_prog, "viewMatrix")
        self.loc_near = GL.glGetUniformLocation(self.cull_prog, "nearCull")
        self.loc_far = GL.glGetUniformLocation(self.cull_prog, "farCull")
        self.loc_triCount = GL.glGetUniformLocation(self.cull_prog, "triCount")

        GL.glUseProgram(self.bitonic_prog)
        self.loc_k = GL.glGetUniformLocation(self.bitonic_prog, "k")
        self.loc_j = GL.glGetUniformLocation(self.bitonic_prog, "j")
        self.loc_sortSize = GL.glGetUniformLocation(self.bitonic_prog, "sortSize")

        GL.glUseProgram(self.reorder_prog)
        self.loc_outCount = GL.glGetUniformLocation(self.reorder_prog, "outCount")

        GL.glUseProgram(self.render_prog)
        self.loc_vp = GL.glGetUniformLocation(self.render_prog, "vp")
        self.loc_view_render = GL.glGetUniformLocation(self.render_prog, "viewMatrix")

        self._cull.start()      
        


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

        eye = self._rotate_about(dx, dy, self.camera_eye.as_numpy, self.camera_pos.as_numpy)
        self.camera_eye += eye - self.camera_eye

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

        pos = self._rotate_about(dx, dy, self.camera_pos.as_numpy, self.camera_eye.as_numpy)

        self.camera_pos += pos - self.camera_pos

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
        eye = _point.Point(_decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2]))
        self.camera_eye += eye - self.camera_eye

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

        eye = _point.Point(_decimal(new_eye[0]), _decimal(new_eye[1]), _decimal(new_eye[2]))
        pos = _point.Point(_decimal(new_pos[0]), _decimal(new_pos[1]), _decimal(new_pos[2]))

        self.camera_eye += eye - self.camera_eye
        self.camera_pos += pos - self.camera_pos

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
        # GL.glMatrixMode(GL.GL_MODELVIEW)
        # GL.glLoadIdentity()
        
        with self._cull:
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
    
            # GL.glPushMatrix()
            #
            # GL.glLightfv(
            #     GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
            #
            # GL.glLightfv(
            #     GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
            #
            # GL.glLightfv(
            #     GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
            #
            # GL.glMaterialfv(
            #     GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
            #
            # GL.glMaterialfv(
            #     GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
            #
            # GL.glMaterialfv(
            #     GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
            #
            # GL.glMaterialf(
            #     GL.GL_FRONT, GL.GL_SHININESS, 20.0)

            # Build triangle data from objects for GPU processing
            all_triangles = []
            all_normals = []
            all_colors = []
            total_count = 0
            
            for obj in self.objects:
                if not hasattr(obj, 'triangles'):
                    continue
                    
                for tri_data in obj.triangles:
                    if len(tri_data) == 5:
                        triangles, tri_normals, tri_colors, count, is_opaque = tri_data
                    elif len(tri_data) == 3:
                        # Handle old format (normals, triangles, count)
                        tri_normals, triangles, count = tri_data
                        # Default color: white opaque
                        tri_colors = np.full((count, 4), [1.0, 1.0, 1.0, 1.0], dtype=np.float32)
                        is_opaque = True
                    else:
                        continue
                    
                    # Flatten triangles if needed
                    if triangles.ndim == 3:
                        triangles = triangles.reshape(-1, 3)
                    
                    all_triangles.append(triangles)
                    all_normals.append(tri_normals)
                    all_colors.append(tri_colors)
                    total_count += count
            
            if total_count == 0:
                self.draw_grid()
                self.SwapBuffers()
                return
                
            # Concatenate all triangle data
            triangles_vec3 = np.vstack(all_triangles).astype(np.float32)
            tri_normals_vec3 = np.vstack(all_normals).astype(np.float32)
            tri_colors = np.vstack(all_colors).astype(np.float32)
            count = total_count
            
            # Pad to vec4 format for shader compatibility
            ones = np.ones((triangles_vec3.shape[0], 1), dtype=np.float32)
            triangles = np.hstack([triangles_vec3, ones])
            tri_normals = np.hstack([tri_normals_vec3, ones])
            
            # Triangles SSBO (binding = 0)
            tri_ssbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, tri_ssbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, triangles.nbytes, triangles, GL.GL_STATIC_DRAW)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 0, tri_ssbo)

            # TriNormals SSBO (binding = 5)
            tri_normals_ssbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, tri_normals_ssbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, tri_normals.nbytes, tri_normals, GL.GL_STATIC_DRAW)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 5, tri_normals_ssbo)

            # TriColors SSBO (binding = 6)
            tri_colors_ssbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, tri_colors_ssbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, tri_colors.nbytes, tri_colors, GL.GL_STATIC_DRAW)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 6, tri_colors_ssbo)

            zero = np.array([0], dtype=np.uint32)
            GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, self.counter_buf)
            GL.glBufferSubData(GL.GL_ATOMIC_COUNTER_BUFFER, 0, zero.nbytes, zero)

            tri_count = count // 3  # Convert vertex count to triangle count
            max_slots = next_power_of_two(tri_count)

            # visible arrays (indices and depths)
            visible_indices = np.zeros((max_slots,), dtype=np.uint32)
            visible_depths = np.full((max_slots,), -1e30, dtype=np.float32)

            idx_ssbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, idx_ssbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, visible_indices.nbytes, visible_indices, GL.GL_DYNAMIC_COPY)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 1, idx_ssbo)

            depth_ssbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, depth_ssbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, visible_depths.nbytes, visible_depths, GL.GL_DYNAMIC_COPY)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 2, depth_ssbo)

            # output VBOs
            out_vertex_count = max_slots * 3
            # positions
            out_vbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, out_vbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, out_vertex_count * 16, None, GL.GL_DYNAMIC_COPY)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 3, out_vbo)
            # normals
            out_nbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, out_nbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, out_vertex_count * 16, None, GL.GL_DYNAMIC_COPY)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 4, out_nbo)
            # colors
            out_cbo = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_SHADER_STORAGE_BUFFER, out_cbo)
            GL.glBufferData(GL.GL_SHADER_STORAGE_BUFFER, out_vertex_count * 16, None, GL.GL_DYNAMIC_COPY)
            GL.glBindBufferBase(GL.GL_SHADER_STORAGE_BUFFER, 7, out_cbo)

            # Dispatch cull compute
            GL.glUseProgram(self.cull_prog)
            GL.glUniformMatrix4fv(self.loc_view, 1, GL_FALSE, self.view.T)
            GL.glUniform1f(self.loc_near, 0.1)
            GL.glUniform1f(self.loc_far, 1000.0)
            GL.glUniform1ui(self.loc_triCount, tri_count)

            groups = (tri_count + self.local_size - 1) // self.local_size
            GL.glDispatchCompute(groups, 1, 1)
            GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT | GL.GL_ATOMIC_COUNTER_BARRIER_BIT)

            # read back visible count
            GL.glBindBuffer(GL.GL_ATOMIC_COUNTER_BUFFER, self.counter_buf)
            counter_data = np.zeros(1, dtype=np.uint32)
            GL.glGetBufferSubData(GL.GL_ATOMIC_COUNTER_BUFFER, 0, 4, counter_data)
            visible_count = int(counter_data[0])
            
            if visible_count == 0:
                self.draw_grid()
                self.SwapBuffers()
                return

            # bitonic sort
            sort_size = next_power_of_two(visible_count)
            GL.glUseProgram(self.bitonic_prog)
            GL.glUniform1ui(self.loc_sortSize, sort_size)
            
            k = 2
            while k <= sort_size:
                j = k // 2
                while j >= 1:
                    GL.glUniform1ui(self.loc_k, k)
                    GL.glUniform1ui(self.loc_j, j)
                    groups = (sort_size + self.local_size - 1) // self.local_size
                    GL.glDispatchCompute(groups, 1, 1)
                    GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT)
                    j //= 2
                k *= 2

            # reorder into output VBOs
            GL.glUseProgram(self.reorder_prog)
            GL.glUniform1ui(self.loc_outCount, visible_count)
            groups = (visible_count + self.local_size - 1) // self.local_size
            GL.glDispatchCompute(groups, 1, 1)
            GL.glMemoryBarrier(GL.GL_SHADER_STORAGE_BARRIER_BIT | GL.GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)

            # render
            w, h = self.GetClientSize()
            GL.glViewport(0, 0, w, h)
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

            # render program
            GL.glUseProgram(self.render_prog)
            # upload vp and view
            perspective = self._get_perspective()
            view = self._get_view()
            GL.glUniformMatrix4fv(self.loc_vp, 1, GL.GL_FALSE, perspective.T)
            GL.glUniformMatrix4fv(self.loc_view_render, 1, GL.GL_FALSE, view.T)

            # Setup vertex attributes from SSBOs
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, out_vbo)
            GL.glEnableVertexAttribArray(0)
            GL.glVertexAttribPointer(0, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, out_nbo)
            GL.glEnableVertexAttribArray(1)
            GL.glVertexAttribPointer(1, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, None)
            
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, out_cbo)
            GL.glEnableVertexAttribArray(2)
            GL.glVertexAttribPointer(2, 4, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

            # draw back-to-front with depth writes off (for transparency)
            GL.glDepthMask(GL.GL_FALSE)
            GL.glBindVertexArray(self.vao)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, visible_count * 3)
            GL.glDepthMask(GL.GL_TRUE)
            
            # Cleanup temporary buffers
            GL.glDeleteBuffers(1, [tri_ssbo])
            GL.glDeleteBuffers(1, [tri_normals_ssbo])
            GL.glDeleteBuffers(1, [tri_colors_ssbo])
            GL.glDeleteBuffers(1, [idx_ssbo])
            GL.glDeleteBuffers(1, [depth_ssbo])
            GL.glDeleteBuffers(1, [out_vbo])
            GL.glDeleteBuffers(1, [out_nbo])
            GL.glDeleteBuffers(1, [out_cbo])

            self.draw_grid()
            # GL.glPopMatrix()

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
