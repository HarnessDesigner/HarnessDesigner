from typing import Self, Iterable, Union
import weakref
import numpy as np


class PointMeta(type):
    _instances = {}

    @classmethod
    def _remove_ref(cls, ref):
        for key, value in cls._instances.items():
            if value == ref:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, x: float, y: float,
                 z: float | None = None, db_id: str | None = None) -> "Point":

        if db_id is not None:
            if db_id not in cls._instances:
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)

            elif cls._instances[db_id]() is None:
                # Handle edge case where a reference has been removed
                # but the reference object has not yet been removed from
                # the dict. We have to make sure that we delete the key
                # before adding the object again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                instance = super().__call__(x, y, z, db_id)
                cls._instances[db_id] = weakref.ref(instance)
            else:
                instance = cls._instances[db_id]()
        else:
            instance = super().__call__(x, y, z, db_id)

        return instance


class Point(metaclass=PointMeta):

    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = np.array(self.as_float, dtype=np.float64)
                arr @= instance
                x, y, z = arr

                self._x = x
                self._y = y
                self._z = z

                self._process_update()
                return self
            else:
                return inputs @ self.as_numpy

        if func == np.add:
            arr = np.array(self.as_float, dtype=np.float64)

            if isinstance(instance, np.ndarray):
                arr += instance
                x, y, z = arr
                self._x = x
                self._y = y
                self._z = z

                self._process_update()
                return self
            else:
                return inputs + arr

        if func == np.subtract:
            arr = np.array(self.as_float, dtype=np.float64)

            if isinstance(instance, np.ndarray):
                arr -= instance
                x, y, z = arr
                self._x = x
                self._y = y
                self._z = z

                self._process_update()
                return self
            else:
                return inputs + arr

        if func == np.multiply:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr *= instance
                x, y, z = arr
                self._x = x
                self._y = y
                self._z = z
                return self
            else:
                return inputs * self.as_numpy

        raise RuntimeError

    def __init__(self, x: float, y: float,
                 z: float | None = None, db_id: str | None = None):

        self.db_id = db_id

        if z is None:
            self.is2d = True
            z = 0.0
        else:
            self.is2d = False

        self._x = x
        self._y = y
        self._z = z

        self._callbacks = []
        self._ref_count = 0

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def __remove_callback(self, ref):
        try:
            self._callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, callback):
        # we don't explicitly check to see if a callback is already registered
        # what we care about is if a callback is called only one time and that
        # check is done when the callbacks are being done and if there happend
        # to be a duplicate the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(callback, self.__remove_callback)

        self._callbacks.append(ref)

    def unbind(self, callback):
        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb == callback:
                # we don't return after licating a matching callback in the
                # event a callback was registered more than one time. duplicates
                # are also removed aty the time callbacks get called but if an update
                # to a point never occurs we want to make sure that we explicitly
                # unbind all callbacks including duplicates.
                self._callbacks.remove(ref)

    def _process_update(self):
        if self._ref_count:
            return

        used_callbacks = []
        for ref in self._callbacks[:]:
            cb = ref()
            if cb is None:
                self._callbacks.remove(ref)
            elif cb not in used_callbacks:
                cb(self)
                used_callbacks.append(cb)
            else:
                # remove duplicate callbacks since we are
                # iterating over the callbacks
                self._callbacks.remove(ref)

    @property
    def x(self) -> float:
        return float(self._x)

    @x.setter
    def x(self, value: float):
        self._x = value
        self._process_update()

    @property
    def y(self) -> float:
        return float(self._y)

    @y.setter
    def y(self, value: float):
        self._y = value
        self._process_update()

    @property
    def z(self) -> float:
        return float(self._z)

    @z.setter
    def z(self, value: float):
        self._z = value
        self._process_update()

    def copy(self) -> "Point":
        return Point(self.x, self.y, self.z)

    def __iadd__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other.as_float
        else:
            x, y, z = (float(item) for item in other)

        self._x += x
        self._y += y
        self._z += z

        self._process_update()

        return self

    def __add__(self, other: Union["Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self.as_float

        if isinstance(other, Point):
            x2, y2, z2 = other.as_float
        else:
            x2, y2, z2 = (float(item) for item in other)

        x = x1 + x2
        y = y1 + y2
        z = z1 + z2

        return Point(x, y, z)

    def __isub__(self, other: Union["Point", np.ndarray]) -> Self:
        if isinstance(other, Point):
            x, y, z = other.as_float
        else:
            x, y, z = (float(item) for item in other)

        self._x -= x
        self._y -= y
        self._z -= z

        self._process_update()

        return self

    def __sub__(self, other: Union["Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self.as_float

        if isinstance(other, Point):
            x2, y2, z2 = other.as_float
        else:
            x2, y2, z2 = (float(item) for item in other)

        x = x1 - x2
        y = y1 - y2
        z = z1 - z2

        return Point(x, y, z)

    def __imul__(self, other: Union[float, "Point", np.ndarray]) -> Self:
        if isinstance(other, float):
            x = y = z = other
        elif isinstance(other, Point):
            x, y, z = other.as_float
        else:
            x, y, z = (float(item) for item in other)

        self._x *= x
        self._y *= y
        self._z *= z

        self._process_update()

        return self

    def __mul__(self, other: Union[float, "Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self.as_float

        if isinstance(other, float):
            x2 = y2 = z2 = other
        elif isinstance(other, Point):
            x2, y2, z2 = other.as_float
        else:
            x2, y2, z2 = (float(item) for item in other)

        x = x1 * x2
        y = y1 * y2
        z = z1 * z2

        return Point(x, y, z)

    def __itruediv__(self, other: Union[float, "Point", np.ndarray]) -> Self:
        if isinstance(other, float):
            x = y = z = other
        elif isinstance(other, Point):
            x, y, z = other.as_float
        else:
            x, y, z = (float(item) for item in other)

        self._x /= x
        self._y /= y
        self._z /= z

        self._process_update()

        return self

    def __truediv__(self, other: Union[float, "Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self.as_float

        if isinstance(other, float):
            x2 = y2 = z2 = other
        elif isinstance(other, Point):
            x2, y2, z2 = other.as_float
        else:
            x2, y2, z2 = (float(item) for item in other)

        x = x1 / x2
        y = y1 / y2
        z = z1 / z2

        return Point(x, y, z)

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
        arr = self.as_numpy
        o = origin.as_numpy

        arr -= o
        arr @= angle.as_matrix.T
        arr += o

        with self:
            self.x = float(arr[0])
            self.y = float(arr[1])
            self.z = float(arr[2])

        self._process_update()

    def get_angle(self, origin: "Point") -> "_angle.Angle":
        return _angle.Angle.from_points(origin, self)

    def __bool__(self):
        x, y, z = self.as_float

        return x != 0.0 or y != 0.0 or z != 0.0

    def __eq__(self, other: "Point") -> bool:
        x1, y1, z1 = self.as_float
        x2, y2, z2 = other.as_float

        return x1 == x2 and y1 == y2 and z1 == z2

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_float(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z

    @property
    def as_int(self) -> tuple[int, int, int]:
        return int(self._x), int(self._y), int(self._z)

    @property
    def as_numpy(self) -> np.ndarray:
        return np.array(self.as_float, dtype=np.float64)

    def __iter__(self) -> Iterable[float]:
        return iter([self.x, self.y, self.z])

    def __str__(self) -> str:
        return f'X: {self.x}, Y: {self.y}, Z: {self.z}'

    def __le__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 <= x2 and y1 <= y2 and z1 <= z2

    def __ge__(self, other: "Point") -> bool:
        x1, y1, z1 = self
        x2, y2, z2 = other
        return x1 >= x2 and y1 >= y2 and z1 >= z2

    def __neg__(self) -> "Point":
        x = -self.x
        y = -self.y
        z = -self.z

        return Point(x, y, z)

    @property
    def inverse(self) -> "Point":
        x = -self.x
        y = -self.y
        z = -self.z

        return Point(x, y, z)


ZERO_POINT = Point(0.0, 0.0, 0.0)

from . import angle as _angle  # NOQA