from typing import Self, Callable, Iterable, Union
import weakref
import numpy as np

from ..wrappers.decimal import Decimal as _decimal
from . import rotation as _rotation
from .constants import TEN_0, ZERO_1


def _round_down(val: _decimal) -> _decimal:
    return _decimal(int(val * TEN_0)) * ZERO_1


class PointMeta(type):
    _instances = {}

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, x: _decimal, y: _decimal, z: _decimal | None = None, db_obj=None):
        if db_obj is not None:
            if db_obj.db_id in cls._instances:
                instance = cls._instances[db_obj.db_id]
            else:
                instance = super().__call__(x, y, z, db_obj)
                cls._instances[db_obj.db_id] = weakref.ref(instance, cls._remove_instance)
        else:
            instance = super().__call__(x, y, z, db_obj)

        return instance


class Point(metaclass=PointMeta):
    _instances = {}

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

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None, db_obj=None):
        self._db_obj = db_obj

        if z is None:
            z = _decimal(0.0)

        self._x = _round_down(x)
        self._y = _round_down(y)
        self._z = _round_down(z)

        self.__callbacks = []
        self.__cb_disabled_count = 0
        self.__objects = []

    def add_object(self, obj):
        if obj not in self.__objects:
            self.__objects.append(obj)

    def remove_object(self, obj):
        try:
            self.__objects.remove(obj)
        except ValueError:
            pass

    @property
    def objects(self):
        for obj in self.__objects:
            yield obj

    def __enter__(self):
        self.__cb_disabled_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__cb_disabled_count -= 1
        self.__do_callbacks()

    def Bind(self, cb: Callable[["Point"], None]) -> bool:
        for ref in self.__callbacks[:]:
            if ref() is None:
                self.__callbacks.remove(ref)
            elif ref() == cb:
                return False
        else:
            self.__callbacks.append(weakref.WeakMethod(cb, self.__remove_ref))

        return True

    def Unbind(self, cb: Callable[["Point"], None]) -> None:
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
        return self._x

    @x.setter
    def x(self, value: _decimal):
        self._x = _round_down(value)
        self.__do_callbacks()

    @property
    def y(self) -> _decimal:
        return self._y

    @y.setter
    def y(self, value: _decimal):
        self._y = _round_down(value)
        self.__do_callbacks()

    @property
    def z(self) -> _decimal:
        return self._z

    @z.setter
    def z(self, value: _decimal):
        self._z = _round_down(value)
        self.__do_callbacks()

    def copy(self) -> "Point":
        return Point(_decimal(self._x), _decimal(self._y), _decimal(self._z))

    def __do_callbacks(self):
        if self.__cb_disabled_count != 0:
            return

        for ref in self.__callbacks[:]:
            func = ref()
            if func is None:
                self.__callbacks.remove(ref)
            else:
                func(self)

    def __iadd__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)
        with self:
            self.x += x
            self.y += y
            self.z += z

        self.__do_callbacks()

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

        self.__do_callbacks()

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
        with self:
            self.x /= other
            self.y /= other
            self.z /= other

        self.__do_callbacks()

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

    def get_angle(self, origin: "Point") -> "Angle":
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


ZERO_POINT = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))

from . import angle as _angle  # NOQA