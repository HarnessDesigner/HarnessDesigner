from typing import Union, Self, Iterable

import math
import weakref
import numpy as np
from scipy.spatial.transform import Rotation as _Rotation


try:
    from ..wrappers.wrap_decimal import Decimal as _decimal
    from .. import debug as _debug

except ImportError:
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA
    import debug as _debug  # NOQA

from . import point as _point


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

    def __init__(self, R=None, order: str = 'XYZ'):

        if R is None:
            R = _Rotation.from_quat([0.0, 0.0, 0.0, 1.0])  # NOQA

        self._R = R
        self.order = order

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
        return Angle(R, self.order)

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

    @classmethod
    def _quat_to_euler(cls, quat: np.ndarray,
                       order: str = 'XYZ') -> tuple[_decimal, _decimal, _decimal]:
        c = quat[0]
        d = quat[1]
        e = quat[2]
        f = quat[3]
        g = c + c
        h = d + d
        k = e + e
        a = c * g
        l = c * h  # NOQA
        c = c * k
        m = d * h
        d = d * k
        e = e * k
        g = f * g
        h = f * h
        f = f * k

        matrix = np.array([1 - (m + e), l + f, c - h, 0,
                           l - f, 1 - (a + e), d + g, 0,
                           c + h, d - g, 1 - (a + m), 0],
                          dtype=np.float64)

        return cls._matrix_to_euler(matrix, order)

    @staticmethod
    def _matrix_to_euler(matrix: np.ndarray,
                         order: str) -> tuple[_decimal, _decimal, _decimal]:

        def clamp(a_, b_, c_):
            return max(b_, min(c_, a_))

        a = matrix[0]
        f = matrix[4]
        g = matrix[8]
        h = matrix[1]
        k = matrix[5]
        l = matrix[9]  # NOQA
        m = matrix[2]
        n = matrix[6]
        e = matrix[10]

        if order.lower() == "xyz":
            y = math.asin(clamp(g, -1, 1))
            if 0.99999 > abs(g):
                x = math.atan2(-l, e)
                z = math.atan2(-f, a)
            else:
                x = math.atan2(n, k)
                z = 0
        elif order.lower() == "yxz":
            x = math.asin(-clamp(l, -1, 1))
            if 0.99999 > abs(l):
                y = math.atan2(g, e)
                z = math.atan2(h, k)
            else:
                y = math.atan2(-m, a)
                z = 0
        else:
            raise ValueError

        return _decimal(math.degrees(x)), _decimal(math.degrees(y)), _decimal(math.degrees(z))

    @staticmethod
    def _euler_to_quat(x, y, z, order='XYZ'):
        x = _decimal(math.radians(float(x)))
        y = _decimal(math.radians(float(y)))
        z = _decimal(math.radians(float(z)))

        d2 = _decimal(2.0)
        x_half = x / d2
        y_half = y / d2
        z_half = z / d2

        c = math.cos(x_half)
        d = math.cos(y_half)
        e = math.cos(z_half)
        f = math.sin(x_half)
        g = math.sin(y_half)
        h = math.sin(z_half)

        if order.lower() == 'xyz':
            x = f * d * e + c * g * h
            y = c * g * e - f * d * h
            z = c * d * h + f * g * e
            w = c * d * e - f * g * h
        elif order.lower() == 'yxz':
            x = f * d * e + c * g * h
            y = c * g * e - f * d * h
            z = c * d * h - f * g * e
            w = c * d * e + f * g * h
        else:
            raise ValueError

        quat = np.array([float(x), float(y), float(z), float(w)], dtype=np.float32)
        return quat

    @property
    def x(self) -> _decimal:
        quat = self._R.as_quat()
        angles = self._quat_to_euler(quat, self.order)
        return angles[0]

    @x.setter
    def x(self, value: _decimal):
        quat = self._R.as_quat()
        angles = list(self._quat_to_euler(quat, self.order))
        angles[0] = value

        quat = self._euler_to_quat(*(angles + [self.order]))

        self._R = _Rotation.from_quat(quat)  # NOQA
        self._process_update()

    @property
    def y(self) -> _decimal:
        quat = self._R.as_quat()
        angles = self._quat_to_euler(quat, self.order)
        return angles[1]

    @y.setter
    def y(self, value: _decimal):
        quat = self._R.as_quat()
        angles = list(self._quat_to_euler(quat, self.order))
        angles[1] = value

        quat = self._euler_to_quat(*(angles + [self.order]))

        self._R = _Rotation.from_quat(quat)  # NOQA
        self._process_update()

    @property
    def z(self) -> _decimal:
        quat = self._R.as_quat()
        angles = self._quat_to_euler(quat, self.order)
        return angles[2]

    @z.setter
    def z(self, value: _decimal):
        quat = self._R.as_quat()
        angles = list(self._quat_to_euler(quat, self.order))
        angles[2] = value

        quat = self._euler_to_quat(*(angles + [self.order]))

        self._R = _Rotation.from_quat(quat)  # NOQA
        self._process_update()

    def copy(self) -> "Angle":
        return Angle.from_quat(self._R.as_quat(), self.order)
    #
    # def __radd__(self, other: Union["Angle", np.ndarray]) -> Self:
    #     if isinstance(other, Angle):
    #         x, y, z = other
    #         x += self.x
    #         y += self.y
    #         z += self.z
    #         angles = (float(x), float(y), float(z))
    #
    #         if angles in self._EULER_MAPPING:
    #             other._R = _Rotation.from_quat(self._EULER_MAPPING[angles])  # NOQA
    #         else:
    #             other._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA
    #
    #         other._process_update()  # NOQA
    #     elif isinstance(other, np.ndarray):
    #         if other.shape == (3, 3):
    #             m = self.as_matrix
    #             other += m
    #
    #         elif other.shape == (3,):
    #             angles = np.array(self.as_float, dtype=np.dtypes.Float64DType)
    #             other += angles
    #         else:
    #             raise TypeError(f'Unsopported type {type(other)} {other.shape}')
    #     else:
    #         raise TypeError(f'Unsopported type {type(other)}')
    #
    #     return other

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        tx, ty, tz = self

        tx += x
        ty += y
        tz += z

        quat = self._euler_to_quat(tx, ty, tz, self.order)
        self._R = _Rotation.from_quat(quat)  # NOQA
        self._process_update()
        return self

    def __add__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        tx, ty, tz = self

        tx += x
        ty += y
        tz += z
        quat = self._euler_to_quat(tx, ty, tz, self.order)
        return self.from_quat(quat, self.order)

    #
    # def __rsub__(self, other: Union["Angle", np.ndarray]) -> Self:
    #     if isinstance(other, Angle):
    #         x, y, z = other
    #         x -= self.x
    #         y -= self.y
    #         z -= self.z
    #         angles = (float(x), float(y), float(z))
    #
    #         if angles in self._EULER_MAPPING:
    #             other._R = _Rotation.from_quat(self._EULER_MAPPING[angles])  # NOQA
    #         else:
    #             other._R = _Rotation.from_euler('xyz', angles, degrees=True)  # NOQA
    #
    #         other._process_update()  # NOQA
    #     elif isinstance(other, np.ndarray):
    #         if other.shape == (3, 3):
    #             m = self.as_matrix
    #             other -= m
    #
    #         elif other.shape == (3,):
    #             angles = np.array(self.as_float, dtype=np.dtypes.Float64DType)
    #             other -= angles
    #         else:
    #             raise TypeError(f'Unsopported type {type(other)} {other.shape}')
    #     else:
    #         raise TypeError(f'Unsopported type {type(other)}')
    #
    #     return other

    def __isub__(self, other: Union["Angle", np.ndarray]) -> Self:
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        tx, ty, tz = self

        tx -= x
        ty -= y
        tz -= z
        quat = self._euler_to_quat(tx, ty, tz, self.order)
        self._R = _Rotation.from_quat(quat)  # NOQA
        self._process_update()
        return self

    def __sub__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        if isinstance(other, Angle):
            x, y, z = other
        else:
            x, y, z = (_decimal(float(item)) for item in other)

        tx, ty, tz = self

        tx -= x
        ty -= y
        tz -= z
        quat = self._euler_to_quat(tx, ty, tz, self.order)
        return self.from_quat(quat, self.order)

    def __rmatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T

            x = _decimal(float(values[0]))
            y = _decimal(float(values[1]))
            z = _decimal(float(values[2]))
            quat = self._euler_to_quat(x, y, z, self.order)
            other._R = _Rotation.from_quat(quat)  # NOQA
            other._process_update()  # NOQA

        elif isinstance(other, Angle):
            matrix = other._R.as_matrix() @ self._R.as_matrix()  # NOQA
            other._R = _Rotation.from_matrix(matrix)  # NOQA
            other._process_update()
        else:
            raise RuntimeError('sanity check')

        return other

    @_debug.timeit
    def __imatmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other @= self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T

            x = _decimal(float(values[0]))
            y = _decimal(float(values[1]))
            z = _decimal(float(values[2]))

            with other:
                other.x = x
                other.y = y
                other.z = z

            other._process_update()  # NOQA

        elif isinstance(other, Angle):
            matrix = self._R.as_matrix() @ other._R.as_matrix()  # NOQA
            self._R = _Rotation.from_matrix(matrix)  # NOQA
            self._process_update()
            return self
        else:
            raise RuntimeError('sanity check')

        return other

    @_debug.timeit
    def __matmul__(self, other: Union[np.ndarray, "_point.Point"]) -> np.ndarray:
        if isinstance(other, np.ndarray):
            other = other @ self._R.as_matrix().T
        elif isinstance(other, _point.Point):
            values = other.as_numpy @ self._R.as_matrix().T
            x = _decimal(float(values[0]))
            y = _decimal(float(values[1]))
            z = _decimal(float(values[2]))

            other = _point.Point(x, y, z)
        elif isinstance(other, Angle):
            matrix = self._R.as_matrix() @ other._R.as_matrix()  # NOQA
            R = _Rotation.from_matrix(matrix)  # NOQA
            other = Angle(R, self.order)
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
        return str(f'X: {self.x}, Y: {self.y}, Z: {self.z}')

    @property
    def as_quat(self) -> np.ndarray:
        return self._R.as_quat()

    @classmethod
    def from_matrix(cls, matrix: np.ndarray):
        R = _Rotation.from_matrix(matrix)  # NOQA
        return cls(R)

    @classmethod
    def from_euler(cls, x: float | _decimal, y: float | _decimal,
                   z: float | _decimal, order: str = 'XYZ') -> "Angle":

        quat = cls._euler_to_quat(x, y, z, order)
        R = _Rotation.from_quat(quat)  # NOQA
        ret = cls(R, order)
        return ret

    @classmethod
    def from_quat(cls, q: list[float, float, float, float] | np.ndarray,
                  order: str = 'XYZ') -> "Angle":

        R = _Rotation.from_quat(q)  # NOQA
        return cls(R, order)

    @classmethod
    def from_points(cls, p1: "_point.Point", p2: "_point.Point", order: str = 'XYZ') -> "Angle":
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

        if order.lower() == 'xyz':
            rot = np.column_stack((right, true_up, forward_world))
        elif order.lower() == 'yxz':
            rot = np.column_stack((true_up, right, forward_world))
        else:
            raise ValueError

        R = _Rotation.from_matrix(rot)  # NOQA
        return cls(R, order)
