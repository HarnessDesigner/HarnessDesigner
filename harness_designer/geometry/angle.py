
from typing import Self, Callable, Iterable, Union, TYPE_CHECKING
import weakref
import math
import numpy as np
from scipy.spatial.transform import Rotation as _Rotation

from ..wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from . import point as _point


class AngleMeta(type):
    _instances = {}

    @classmethod
    def _remove_instance(cls, ref):
        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, R, db_obj=None):
        if db_obj is not None:
            if db_obj.db_id in cls._instances:
                instance = cls._instances[db_obj.db_id]
            else:
                instance = super().__call__(R, db_obj)
                cls._instances[db_obj.db_id] = weakref.ref(instance, cls._remove_instance)
        else:
            instance = super().__call__(R, db_obj)

        return instance


class Angle(metaclass=AngleMeta):

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

    def __init__(self, R, db_obj=None):
        self._db_obj = db_obj
        self._R = R

        p1 = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        p2 = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(10.0))
        p2 @= self._R.as_matrix().T  # NOQA

        self._p1 = p1
        self._p2 = p2

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

    @staticmethod
    def __rotate_euler(c1: _decimal, c2: _decimal, c3: _decimal, c4: _decimal, angle: _decimal) -> tuple[_decimal, _decimal]:
        angle = _decimal(math.radians(angle))

        qx = c1 + _decimal(math.cos(angle)) * (c3 - c1) - _decimal(math.sin(angle)) * (c4 - c2)
        qy = c2 + _decimal(math.sin(angle)) * (c3 - c1) + _decimal(math.cos(angle)) * (c4 - c2)
        return qx, qy

    @staticmethod
    def __get_euler(c1: _decimal, c2: _decimal, c3: _decimal, c4: _decimal) -> _decimal:
        theta1 = _decimal(math.atan2(c2, c1))
        theta2 = _decimal(math.atan2(c4, c3))
        return _decimal(math.degrees((theta2 - theta1) % _decimal(2) * _decimal(math.pi)))

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

        self.__do_callbacks()

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

    def __rmatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T

            with other:
                other.x = _decimal(float(values[0]))
                other.y = _decimal(float(values[1]))
                other.z = _decimal(float(values[2]))
        else:
            raise RuntimeError('sanity check')

        return other

    def __matmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        from . import point

        if isinstance(other, np.ndarray):
            other = other @ self._R.as_matrix().T
        elif isinstance(other, point.Point):
            other = other.copy()
            values = other.as_numpy @ self._R.as_matrix().T
            with other:
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
        return self._R.as_matrix().T

    @property
    def as_quat(self) -> np.ndarray:
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
                   z: float | _decimal, db_obj=None) -> "Angle":

        R = _Rotation.from_euler('xyz', (float(x), float(y), float(z)),
                                 degrees=True)  # NOQA
        return cls(R, db_obj)

    @classmethod
    def from_quat(cls, q: list[float, float, float, float] | np.ndarray,
                  db_obj=None) -> "Angle":

        R = _Rotation.from_quat(q)  # NOQA
        return cls(R, db_obj)

    @classmethod
    def from_points(cls, p1: "_point.Point", p2: "_point.Point",
                    db_obj=None) -> "Angle":  # NOQA

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
        return cls(R, db_obj)
