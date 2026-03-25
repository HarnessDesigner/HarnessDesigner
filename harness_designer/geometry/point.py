from typing import Self, Iterable, Union
import weakref
import numpy as np

from .decimal import Decimal as _d


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

    def __call__(cls, x: float | _d, y: float | _d,
                 z: float | _d | None = None, db_id: int | str | None = None) -> "Point":

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
                self._data @= instance
                self._process_update()
                return self
            else:
                return inputs @ self._data

        if func == np.add:
            if isinstance(instance, np.ndarray):
                self._data += instance
                self._process_update()
                return self
            else:
                return inputs + self._data

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                self._data -= instance
                self._process_update()

                return self
            else:
                return inputs + self._data

        if func == np.multiply:
            if isinstance(instance, np.ndarray):
                self._data *= instance
                return self
            else:
                return inputs * self._data

        raise RuntimeError

    def __init__(self, x: float | _d, y: float | _d,
                 z: float | _d | None = None, db_id: int | str | None = None):

        self.db_id = db_id

        if z is None:
            self.is2d = True
            z = 0.0
        else:
            self.is2d = False

        self._data = np.ascontiguousarray(np.array([x, y, z], dtype=np.float64))

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
    def x(self) -> _d:
        return _d(self._data[0])

    @x.setter
    def x(self, value: float | _d):
        self._data[0] = value
        self._process_update()

    @property
    def y(self) -> _d:
        return _d(self._data[1])

    @y.setter
    def y(self, value: float | _d):
        self._data[1] = value
        self._process_update()

    @property
    def z(self) -> _d:
        return _d(self._data[2])

    @z.setter
    def z(self, value: float | _d):
        self._data[2] = value
        self._process_update()

    def copy(self) -> "Point":
        return Point(*self._data.tolist())

    @staticmethod
    def __other_to_decimal(other: Union[_d, float, "Point", np.ndarray]) -> tuple[_d, _d, _d]:
        if isinstance(other, np.ndarray):
            x, y, z = [_d(item) for item in other.tolist()]
        elif isinstance(other, Point):
            x, y, z = other.as_decimal
        elif isinstance(other, float):
            x = y = z = _d(other)
        elif isinstance(other, _d):
            x = y = z = other
        else:
            raise TypeError(f'incorrect type "{type(other)}"')

        return x, y, z

    def __iadd__(self, other: Union["Point", np.ndarray, float]) -> Self:
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 + x2
        self._data[1] = y1 + y2
        self._data[2] = z1 + z2

        self._process_update()

        return self

    def __add__(self, other: Union["Point", np.ndarray, float, _d]) -> "Point":
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 + x2, y1 + y2, z1 + z2)

    def __isub__(self, other: Union["Point", np.ndarray, float, _d]) -> Self:
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 - x2
        self._data[1] = y1 - y2
        self._data[2] = z1 - z2

        self._process_update()

        return self

    def __sub__(self, other: Union["Point", np.ndarray, float, _d]) -> "Point":
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 - x2, y1 - y2, z1 - z2)

    def __imul__(self, other: Union[float, "Point", np.ndarray, _d]) -> Self:
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 * x2
        self._data[1] = y1 * y2
        self._data[2] = z1 * z2

        self._process_update()

        return self

    def __mul__(self, other: Union[float, "Point", np.ndarray, _d]) -> "Point":
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 * x2, y1 * y2, z1 * z2)

    def __itruediv__(self, other: Union[float, "Point", np.ndarray, _d]) -> Self:
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        self._data[0] = x1 / x2
        self._data[1] = y1 / y2
        self._data[2] = z1 / z2

        self._process_update()

        return self

    def __truediv__(self, other: Union[_d, float, "Point", np.ndarray]) -> "Point":
        x1, y1, z1 = self.as_decimal
        x2, y2, z2 = self.__other_to_decimal(other)

        return Point(x1 / x2, y1 / y2, z1 / z2)

    def __imatmul__(self, other: ["_angle.Angle", np.ndarray]) -> "Point":
        if isinstance(other, np.ndarray):
            if other.shape[0] == 3:
                angle = _angle.Angle.from_euler(*other.tolist()).as_matrix_numpy
            elif other.shape[0] == 4:
                angle = _angle.Angle.from_quat(*other.tolist()).as_matrix_numpy
            else:
                angle = other
        else:
            angle = other.as_matrix_numpy

        pn = angle @ self.as_numpy

        self._data[0] = pn[0]
        self._data[1] = pn[1]
        self._data[2] = pn[2]

        self._process_update()

        return self

    def set_angle(self, angle: "_angle.Angle", origin: "Point"):
        p = self.copy()

        p -= origin
        p @= angle
        p += origin

        x, y, z = p.as_float
        self._data[0] = x
        self._data[1] = y
        self._data[2] = z

        self._process_update()

    def get_angle(self, origin: "Point") -> "_angle.Angle":
        return _angle.Angle.from_points(origin, self)

    def __bool__(self):
        arr = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        return not all(np.isclose(self._data, arr))

    def __eq__(self, other: "Point") -> bool:
        return all(np.isclose(self._data, other.as_numpy))

    def __ne__(self, other: "Point") -> bool:
        return not self.__eq__(other)

    @property
    def as_decimal(self):
        x, y, z = self.as_float
        return _d(x), _d(y), _d(z)

    @property
    def as_float(self) -> tuple[float, float, float]:
        x, y, z = self._data.tolist()
        return float(x), float(y), float(z)

    @property
    def as_int(self) -> tuple[int, int, int]:
        x, y, z = self.as_float
        return int(x), int(y), int(z)

    @property
    def as_numpy(self) -> np.ndarray:
        return self._data

    def __iter__(self) -> Iterable[float]:
        return iter(self.as_float)

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
        x, y, z = self._data.tolist()
        return Point(-x, -y, -z)

    @property
    def inverse(self) -> "Point":
        return -self


ZERO_POINT = Point(0.0, 0.0, 0.0)

from . import angle as _angle  # NOQA