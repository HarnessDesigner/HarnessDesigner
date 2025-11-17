
from typing import Self, Callable, Iterable, Union
import weakref
import numpy as np
from scipy.spatial.transform import Rotation as _Rotation


from ..wrappers.decimal import Decimal as _decimal
from . import rotation as _rotation
from .constants import TEN_0, ZERO_1
from . import point as _point


def _round_down(val: _decimal) -> _decimal:
    return _decimal(int(val * TEN_0)) * ZERO_1


class Angle:

    @property
    def project_id(self) -> int | None:
        if self._db_obj is None:
            return None

        return self._db_obj.project_id

    @property
    def point_id(self) -> int | None:
        if self._db_obj is None:
            return None

        return self._db_obj.db_id

    def add_to_db(self, table) -> int:
        self._db_obj = table.insert(self.x, self.y, self.z)
        self._instances[self._db_obj.db_id] = weakref.ref(self, PointMeta._remove_instance)  # NOQA
        self.Bind(self._db_obj)
        return self._db_obj.db_id

    def __init__(self, x: _decimal | np.ndarray, y: _decimal | None = None, z: _decimal | None = None, db_obj=None):
        self._db_obj = db_obj

        if isinstance(x, np.ndarray):
            self._q = x
            self._x = None
            self._y = None
            self._z = None

        else:
            self._q = None

            if z is None:
                z = _decimal(0.0)

            self._x = _round_down(x)
            self._y = _round_down(y)
            self._z = _round_down(z)

        self.__callbacks = []
        self.__cb_disabled_count = 0

    def __enter__(self):
        self.__cb_disabled_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__cb_disabled_count -= 1
        self.__do_callbacks()

    def Bind(self, cb: Callable[["Angle"], None]) -> bool:
        for ref in self.__callbacks[:]:
            if ref() is None:
                self.__callbacks.remove(ref)
            elif ref() == cb:
                return False
        else:
            self.__callbacks.append(weakref.WeakMethod(cb, self.__remove_ref))

        return True

    def Unbind(self, cb: Callable[["Angle"], None]) -> None:
        for ref in self.__callbacks[:]:
            if ref() is None:
                self.__callbacks.remove(ref)
            elif ref() == cb:
                self.__callbacks.remove(ref)
                break

    def __remove_ref(self, ref):
        if ref in self.__callbacks:
            self.__callbacks.remove(ref)

    @property
    def x(self) -> _decimal:
        if self._x is None:
            R = _Rotation.from_quat(self._q)
            xyz = R.as_euler('xyz', True)
            return _decimal(float(xyz[0]))

        return self._x

    @x.setter
    def x(self, value: _decimal):
        if self._x is None:
            R = _Rotation.from_euler('xyz', [_round_down(value), self._y, self._z], degrees=True)
            self._q = R.as_quat()
        else:
            self._x = _round_down(value)

        self.__do_callbacks()

    @property
    def y(self) -> _decimal:
        if self._y is None:
            R = _Rotation.from_quat(self._q)
            xyz = R.as_euler('xyz', True)
            return _decimal(float(xyz[1]))

        return self._y

    @y.setter
    def y(self, value: _decimal):
        if self._y is None:
            R = _Rotation.from_euler('xyz', [self._z, _round_down(value), self._z], degrees=True)
            self._q = R.as_quat()
        else:
            self._y = _round_down(value)

        self.__do_callbacks()

    @property
    def z(self) -> _decimal:
        if self._z is None:
            R = _Rotation.from_quat(self._q)
            xyz = R.as_euler('xyz', True)
            return _decimal(float(xyz[2]))

        return self._z

    @z.setter
    def z(self, value: _decimal):
        if self._z is None:
            R = _Rotation.from_euler('xyz', [self._z, self._y, _round_down(value)], degrees=True)
            self._q = R.as_quat()
        else:
            self._z = _round_down(value)

        self.__do_callbacks()

    def copy(self) -> "Angle":
        return Angle(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __do_callbacks(self):
        if self.__cb_disabled_count != 0:
            return

        for ref in self.__callbacks[:]:
            func = ref()
            if func is None:
                self.__callbacks.remove(ref)
            else:
                func(self)

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)
        with self:
            self.x += x
            self.y += y
            self.z += z

        self.__do_callbacks()

        return self

    def __add__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        x1, y1, z1 = self
        if isinstance(other, Angle):
            x2, y2, z2 = other
        else:
            x2, y2, z2 = (_decimal(float(item)) for item in other)

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Angle(x, y, z)

    def __isub__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        with self:
            self.x -= x
            self.y -= y
            self.z -= z

        self.__do_callbacks()

        return self

    def __sub__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        x1, y1, z1 = self
        if isinstance(other, Angle):
            x2, y2, z2 = other
        else:
            x2, y2, z2 = (_decimal(float(item)) for item in other)

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Angle(x, y, z)

    def __rmatmul__(self, other: np.ndarray | _point.Point) -> np.ndarray:
        if self._x is None:
            R = _Rotation.from_quat(self._q)
        else:
            R = _Rotation.from_euler('xyz', self.as_float, True)

        if isinstance(other, np.ndarray):
            other @= R.as_matrix()
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ R.as_matrix()
            with other:
                other.x = _decimal(float(values[0]))
                other.y = _decimal(float(values[1]))

            other.z = _decimal(float(values[2]))
        return other

    def __matmul__(self, other: np.ndarray | _point.Point) -> np.ndarray:
        if self._x is None:
            R = _Rotation.from_quat(self._q)
        else:
            R = _Rotation.from_euler('xyz', self.as_float, True)

        if isinstance(other, np.ndarray):
            other = other @ R.as_matrix()
        elif isinstance(other, _point.Point):
            other = other.copy()
            values = other.as_numpy @ R.as_matrix()
            with other:
                other.x = _decimal(float(values[0]))
                other.y = _decimal(float(values[1]))

            other.z = _decimal(float(values[2]))

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
    def as_float(self) -> tuple[float, float, float] | tuple[float, float, float, float]:
        return float(self._x), float(self._y), float(self._z)

    @property
    def as_int(self) -> tuple[int, int, int]:
        return int(self._x), int(self._y), int(self._z)

    @property
    def as_numpy(self) -> np.ndarray:
        if self._q is None:
            return np.array(self.as_float, dtype=np.dtypes.Float64DType)

        return self._q

    def __iter__(self) -> Iterable[_decimal]:
        if self._q is None:
            return iter([self._x, self._y, self._z])

        return iter([_decimal(float(item)) for item in self._q])

    def __str__(self) -> str:
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'

    @property
    def quat(self) -> list[float]:
        if self._q is None:
            R = _Rotation.from_euler('xyz', self.as_float, True)
            quat = R.as_quat()
        else:
            quat = self._q

        return [float(item) for item in quat]

    @classmethod
    def from_quat(cls, q: list[float] | np.ndarray) -> "Angle":
        if not isinstance(q, np.ndarray):
            q = np.array(q, dtype=np.dtypes.Float64DType)

        return Angle(q)

    @classmethod
    def from_points(cls, p1: _point.Point, p2: _point.Point) -> "Angle":
        a = p1.as_numpy
        b = p2.as_numpy

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        EPS = 1e-12

        if na < EPS or nb < EPS:
            raise ValueError("Zero-length vector")

        a = a / na
        b = b / nb

        dot = np.dot(a, b)
        if dot > 1.0 - EPS:
            return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.dtypes.Float64DType)

        if dot < -1.0 + EPS:
            abs_a = np.abs(a)
            if abs_a[0] < abs_a[1] and abs_a[0] < abs_a[2]:
                orth = np.array([1.0, 0.0, 0.0], dtype=np.dtypes.Float64DType)
            elif abs_a[1] < abs_a[2]:
                orth = np.array([0.0, 1.0, 0.0], dtype=np.dtypes.Float64DType)
            else:
                orth = np.array([0.0, 0.0, 1.0], dtype=np.dtypes.Float64DType)

            axis = np.cross(a, orth)  # NOQA
            axis = axis / np.linalg.norm(axis)

            return np.array([0.0, axis[0], axis[1], axis[2]], dtype=np.dtypes.Float64DType)

        axis = np.cross(a, b)  # NOQA
        s = math.sqrt((1.0 + dot) * 2.0)
        invs = 1.0 / s
        q = np.array([0.5 * s, axis[0] * invs, axis[1] * invs, axis[2] * invs], dtype=np.dtypes.Float64DType)
        q = q / np.linalg.norm(q)

        # w, x, y, z = q
        return cls(q)
