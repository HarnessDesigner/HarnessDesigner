from typing import Union, Self, Iterable, TYPE_CHECKING

import numpy as np
import weakref

try:
    from ..wrappers.wrap_decimal import Decimal as _decimal
except ImportError:
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA

if TYPE_CHECKING:
    from ..geometry import angle as _angle


class PointMeta(type):
    _instances = weakref.WeakValueDictionary()

    def __call__(cls, x: _decimal, y: _decimal, z: _decimal | None = None,
                 db_id: int | None = None):

        if db_id is not None:
            if db_id not in cls._instances:
                cls._instances[db_id] = super().__call__(x, y, z, db_id)

            elif cls._instances[db_id] is None:
                # handle edge case where a reference has been removed
                # but it the reference object has not yet been removed from
                # the dict. we have to make sure that we delete the key
                # before adding the obejct again because of the internal
                # mechanics in weakref and not wanting it to remove
                # the newly added reference
                del cls._instances[db_id]
                cls._instances[db_id] = super().__call__(x, y, z, db_id)

            instance = cls._instances[db_id]
        else:
            instance = super().__call__(x, y, z, db_id)

        return instance


class Point(metaclass=PointMeta):

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

        if func == np.multiply:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr *= instance
                x, y, z = arr
                self._x = _decimal(x)
                self._y = _decimal(y)
                self._z = _decimal(z)
                return self
            else:
                return inputs * self.as_numpy

        raise RuntimeError

    def __init__(self, x: _decimal, y: _decimal, z: _decimal | None = None,
                 db_id: int | None = None):

        self.db_id = db_id

        if z is None:
            z = _decimal(0.0)

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
    def inverse(self) -> "Point":
        point = self.copy()

        with point:
            point.x = -point.x
            point.y = -point.y
            point.z = -point.z

        return point

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
        return str(f'X: {self.x}, Y: {self.y}, Z: {self.z}')

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


ZERO_POINT = Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
