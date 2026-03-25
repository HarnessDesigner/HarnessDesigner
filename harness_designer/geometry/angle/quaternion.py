from typing import Self, TYPE_CHECKING

import math
import numpy as np
from ..decimal import Decimal as _d
from .. import point as _point


ONE = _d(1.0)
TWO = _d(2.0)


class Quaternion:

    def __normalize(self):
        norm = _d(np.linalg.norm(self._data))

        w, x, y, z = self.as_decimal

        w /= norm
        x /= norm
        y /= norm
        z /= norm

        self._data[0] = w
        self._data[1] = x
        self._data[2] = y
        self._data[3] = z

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__normalize()

    def __init__(self, w=None, x=None, y=None, z=None, q=None):
        if q is None:
            self._data = np.array([w, x, y, z], dtype=np.float64)
        else:
            self._data = q

        self.__normalize()

    @property
    def w(self) -> float:
        return float(self._data[0])

    @w.setter
    def w(self, value: [float, _d]):
        self._data[0] = value

    @property
    def x(self) -> float:
        return float(self._data[1])

    @x.setter
    def x(self, value: [float, _d]):
        self._data[1] = value

    @property
    def y(self) -> float:
        return float(self._data[2])

    @y.setter
    def y(self, value: [float, _d]):
        self._data[2] = value

    @property
    def z(self) -> float:
        return float(self._data[3])

    @z.setter
    def z(self, value: [float, _d]):
        self._data[3] = value

    @property
    def as_numpy(self):
        return self._data

    @property
    def as_float(self):
        return self._data.tolist()

    @property
    def as_decimal(self):
        w, x, y, z = self.as_float
        return _d(w), _d(x), _d(y), _d(z)

    def __isub__(self, other: "Quaternion") -> Self:
        if not isinstance(other, Quaternion):
            raise TypeError

        new_q = self.__sub__(other).as_numpy

        with self:
            self._data[0] = new_q[0]
            self._data[1] = new_q[1]
            self._data[2] = new_q[2]
            self._data[3] = new_q[3]
        return self

    def __sub__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            raise TypeError

        return self.__mul(-other, self)

    @staticmethod
    def __mul(qa: "Quaternion", qb: "Quaternion") -> "Quaternion":
        wb, xb, yb, zb = qb.as_decimal
        wa, xa, ya, za = qa.as_decimal
        q = np.array([wb * wa - xb * xa - yb * ya - zb * za,
                      wb * xa + xb * wa + yb * za - zb * ya,
                      wb * ya - xb * za + yb * wa + zb * xa,
                      wb * za + xb * ya - yb * xa + zb * wa], dtype=float)

        return Quaternion(q=q)

    def __iadd__(self, other: "Quaternion") -> Self:
        if not isinstance(other, Quaternion):
            raise TypeError

        new_q = self.__add__(other).as_numpy

        with self:
            self._data[0] = new_q[0]
            self._data[1] = new_q[1]
            self._data[2] = new_q[2]
            self._data[3] = new_q[3]

        return self

    def __add__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            raise TypeError

        diff = self.__sub__(other)
        return self.__mul(diff, self)

    def __itruediv__(self, other: "Quaternion") -> Self:
        if isinstance(other, (int, float)):
            other = np.array([other, other, other, other], dtype=np.float64)
        elif not isinstance(other, Quaternion):
            raise TypeError
        else:
            other = other.as_numpy

        w1, x1, y1, z1 = self.as_decimal
        w2, x2, y2, z2 = [_d(item) for item in other.tolist()]

        def _div(v1, v2):
            try:
                return v1 / v2
            except ZeroDivisionError:
                return 0.0

        with self:
            self._data[0] = _div(w1, w2)
            self._data[1] = _div(x1, x2)
            self._data[2] = _div(y1, y2)
            self._data[3] = _div(z1, z2)

        return self

    def __truediv__(self, other: "Quaternion") -> "Quaternion":
        if isinstance(other, (int, float)):
            other = np.array([other, other, other, other], dtype=np.float64)
        elif not isinstance(other, Quaternion):
            raise TypeError
        else:
            other = other.as_numpy

        w1, x1, y1, z1 = self.as_decimal
        w2, x2, y2, z2 = [_d(item) for item in other.tolist()]

        def _div(v1, v2):
            try:
                return v1 / v2
            except ZeroDivisionError:
                return 0.0

        w = _div(w1, w2)
        x = _div(x1, x2)
        y = _div(y1, y2)
        z = _div(z1, z2)

        return Quaternion(w, x, y, z)

    def __array_ufunc__(self, func, method, inputs, instance, out=None, **kwargs):  # NOQA
        if func == np.matmul:
            w, x, y, z = self.as_float

            # Vectorized quaternion rotation formula
            qvec = np.array([x, y, z], dtype=np.float64)

            t = np.cross(qvec, inputs)
            result = inputs + 2.0 * w * t + 2.0 * np.cross(qvec, t)

            if out is None:
                return result
            else:
                inputs[:] = result
                return inputs

        raise RuntimeError

    def __matmul__(self, other: _point.Point | np.ndarray) -> _point.Point | np.ndarray:
        w, x, y, z = self.as_float

        # Vectorized quaternion rotation formula
        qvec = np.array([x, y, z], dtype=np.float64)

        if isinstance(other, _point.Point):
            array = other.as_numpy

            t = np.cross(qvec, array)
            result = array + 2.0 * w * t + 2.0 * np.cross(qvec, t)

            return _point.Point(*result)
        else:
            t = np.cross(qvec, other)
            result = other + 2.0 * w * t + 2.0 * np.cross(qvec, t)
            return result

    def __rmatmul__(self, other: _point.Point | np.ndarray) -> _point.Point | np.ndarray:
        w, x, y, z = self.as_float

        # Vectorized quaternion rotation formula
        qvec = np.array([x, y, z], dtype=np.float64)

        if isinstance(other, _point.Point):
            array = other.as_numpy

            t = np.cross(qvec, array)
            result = array + 2.0 * w * t + 2.0 * np.cross(qvec, t)

            with other:
                other.x = float(result[0])
                other.y = float(result[1])

            other.z = float(result[2])
        else:
            t = np.cross(qvec, other)
            result = other + 2.0 * w * t + 2.0 * np.cross(qvec, t)
            other[:] = result

        return other

    def __iter__(self):
        return iter(self._data.tolist())

    def conj(self) -> "Quaternion":
        w, x, y, z = self._data.tolist()
        return Quaternion(w, -x, -y, -z)

    def __neg__(self) -> "Quaternion":
        q = self._data

        return Quaternion(*[float(item) for item in self.conj() / np.dot(q, q)])

    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> "Quaternion":
        rx, ry, rz = [_d(item) for item in np.deg2rad([x, y, z])]
        qx = cls(math.cos(rx / TWO), math.sin(rx / TWO), 0.0, 0.0)
        qy = cls(math.cos(ry / TWO), 0.0, math.sin(ry / TWO), 0.0)
        qz = cls(math.cos(rz / TWO), 0.0, 0.0, math.sin(rz / TWO))

        q = cls.__mul(qz, cls.__mul(qx, qy))  # qy ⊗ qx ⊗ qz
        return cls(*q.as_float)

    @property
    def as_euler(self) -> tuple[float, float, float]:
        w, x, y, z = self.as_float

        # Rotation matrix elements from quaternion
        # r00 = ONE - TWO * (y * y + z * z)
        # r01 = TWO * (x * y - w * z)
        r02 = TWO * (x * z + w * y)

        r10 = TWO * (x * y + w * z)
        r11 = ONE - TWO * (x * x + z * z)
        r12 = TWO * (y * z - w * x)

        # r20 = TWO * (x * z - w * y)
        # r21 = TWO * (y * z + w * x)
        r22 = ONE - TWO * (x * x + y * y)

        # For q = Ry(yaw) * Rx(pitch) * Rz(roll):
        # pitch (about X)
        pitch = np.arcsin(np.clip(-float(r12), -1.0, 1.0))

        # yaw (about Y) and roll (about Z)
        # (use atan2 for stable quadrant handling)
        yaw = np.arctan2(float(r02), float(r22))
        roll = np.arctan2(float(r10), float(r11))

        return tuple(float(item) for item in np.rad2deg([pitch, yaw, roll]))

    @property
    def as_matrix(self) -> np.ndarray:
        w, x, y, z = self.as_decimal

        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z

        m1 = [ONE - TWO * (yy + zz), TWO * (xy - wz), TWO * (xz + wy)]
        m2 = [TWO * (xy + wz), ONE - TWO * (xx + zz), TWO * (yz - wx)]
        m3 = [TWO * (xz - wy), TWO * (yz + wx), ONE - TWO * (xx + yy)]

        return np.array([[float(item) for item in m1],
                         [float(item) for item in m2],
                         [float(item) for item in m3]
                         ], dtype=np.float64)

    @classmethod
    def from_axis_angle(cls, axis, angle):
        """
        Create quaternion from axis-angle representation

        Args:
            axis: 3D vector (list, tuple, or numpy array) representing rotation axis
            angle: rotation angle in radians

        Returns:
            Quaternion representing the rotation
        """
        # Convert axis to numpy array and normalize
        axis = np.array(axis, dtype=np.float32)
        axis_length = np.linalg.norm(axis)

        # Handle zero-length axis (no rotation)
        if axis_length < 1e-8:
            return cls(1.0, 0.0, 0.0, 0.0)  # Identity quaternion

        axis = axis / axis_length  # Normalize axis

        # Calculate quaternion components
        half_angle = angle / 2.0
        sin_half = math.sin(half_angle)
        cos_half = math.cos(half_angle)

        return cls(
            cos_half,  # w (scalar) first
            axis[0] * sin_half,  # x
            axis[1] * sin_half,  # y
            axis[2] * sin_half  # z
        )
