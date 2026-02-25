from typing import Self

import math
import numpy as np


ONE = 1.0
TWO = 2.0


class Quaternion:

    def __normalize(self):
        q = np.array([self.w, self.x, self.y, self.z], dtype=np.float64)
        nq = q / np.linalg.norm(q)
        self.w, self.x, self.y, self.z = [float(item) for item in nq]

    def __init__(self, w, x, y, z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

        self.__normalize()

    @property
    def as_numpy(self):
        return np.array([self.w, self.x, self.y, self.z], dtype=np.float64)

    @property
    def as_float(self):
        return [self.w, self.x, self.y, self.z]

    def __isub__(self, other: "Quaternion") -> Self:
        if not isinstance(other, Quaternion):
            raise TypeError

        self.w, self.x, self.y, self.z = list(self.__sub__(other))
        self.__normalize()
        return self

    def __sub__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            raise TypeError

        return self.__mul(-other, self)

    @staticmethod
    def __mul(qa: "Quaternion", qb: "Quaternion") -> "Quaternion":
        wb, xb, yb, zb = qb.as_float
        wa, xa, ya, za = qa.as_float
        q = np.array([wb * wa - xb * xa - yb * ya - zb * za,
                      wb * xa + xb * wa + yb * za - zb * ya,
                      wb * ya - xb * za + yb * wa + zb * xa,
                      wb * za + xb * ya - yb * xa + zb * wa], dtype=float)
        return Quaternion(*[float(item) for item in q])

    def __iadd__(self, other: "Quaternion") -> Self:
        if not isinstance(other, Quaternion):
            raise TypeError

        self.w, self.x, self.y, self.z = self.__add__(other)
        self.__normalize()

        return self

    def __add__(self, other: "Quaternion") -> "Quaternion":
        if not isinstance(other, Quaternion):
            raise TypeError

        diff = self.__sub__(other)
        return self.__mul(diff, self)

    def __itruediv__(self, other: "Quaternion") -> Self:
        if isinstance(other, (float, int)):
            q = Quaternion(*[float(item) for item in self.as_numpy / other])

            self.w, self.x, self.y, self.z = list(q)
            self.__normalize()
            return self

        if not isinstance(other, Quaternion):
            raise TypeError

        q1 = self.as_numpy
        q2 = other.as_numpy

        q = q1 / q2

        self.w, self.x, self.y, self.z = [float(item) for item in q]
        self.__normalize()

        return self

    def __truediv__(self, other: "Quaternion") -> "Quaternion":
        if isinstance(other, (float, int)):
            return Quaternion(*[float(item) for item in self.as_numpy / other])

        if not isinstance(other, Quaternion):
            raise TypeError

        q1 = self.as_numpy
        q2 = other.as_numpy

        q = q1 / q2
        return Quaternion(*[float(item) for item in q])

    def __iter__(self):
        return iter([self.w, self.x, self.y, self.z])

    def conj(self) -> "Quaternion":
        w, x, y, z = list(self)
        return Quaternion(w, -x, -y, -z)

    def __neg__(self) -> "Quaternion":
        q = self.as_numpy
        return Quaternion(*[float(item) for item in self.conj() / np.dot(q, q)])

    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> "Quaternion":
        rx, ry, rz = [float(item) for item in np.deg2rad([x, y, z])]
        qx = cls(math.cos(rx / TWO), math.sin(rx / TWO), 0.0, 0.0)
        qy = cls(math.cos(ry / TWO), 0.0, math.sin(ry / TWO), 0.0)
        qz = cls(math.cos(rz / TWO), 0.0, 0.0, math.sin(rz / TWO))

        q = cls.__mul(qz, cls.__mul(qx, qy))  # qy ⊗ qx ⊗ qz
        return cls(*[float(item) for item in q])

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
        w, x, y, z = self.as_float

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
