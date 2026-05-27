# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Quaternion math used by :mod:`harness_designer.geometry.angle`."""

from typing import Self

import math
import numpy as np
from ..decimal import Decimal as _d
from .. import point as _point


ONE = _d(1.0)
TWO = _d(2.0)


class Quaternion:
    """Represent a normalized quaternion used for 3D rotations."""

    def __array_ufunc__(self, func, _, inputs,
                        instance, out=None, **__):
        """
        Handle selected NumPy ufuncs for quaternion operations.

        :param func: NumPy ufunc being invoked.
        :type func: object
        :param inputs: Left-hand NumPy input.
        :type inputs: :class:`numpy.ndarray` | None
        :param instance: Operand instance chosen by NumPy dispatch.
        :type instance: :class:`numpy.ndarray` | None
        :param out: Optional output array.
        :type out: tuple[:class:`numpy.ndarray`] | None
        :returns: Quaternion or array result for the supported ufunc.
        :rtype: :class:`Quaternion` | :class:`numpy.ndarray`
        :raises RuntimeError: If the ufunc is unsupported.
        """

        if func == np.matmul:
            if isinstance(instance, Quaternion):
                w, x, y, z = self.as_float

                # Vectorized quaternion rotation formula
                qvec = np.array([x, y, z], dtype=np.float32)
                # __matmul__
                if out is None:
                    t = np.cross(qvec, inputs)
                    result = inputs + 2.0 * w * t + 2.0 * np.cross(qvec, t)

                    return result

                # __imatmul__
                else:
                    out = out[0]
                    
                    shape = out.shape
                    if len(shape) == 1:
                        out = out.reshape(-1, 3)

                    t = np.cross(qvec, out)
                    out += (2.0 * w * t) + (2.0 * np.cross(qvec, t))

                    if len(shape) == 1:
                        out = out.reshape(-1)

                    return out

        if func == np.add:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Quaternion):
                # __add__
                if out is None:
                    # quat array
                    if inputs.shape == (4,):
                        q = Quaternion(q=inputs)
                        q += self
                        return q.as_numpy
                # __iadd__
                else:
                    out = out[0]
                    if out.shape == (4,):
                        q = Quaternion(q=out)
                        q += self
                        out[:] = q.as_numpy
                        return out

        if func == np.subtract:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Quaternion):
                # __sub__
                if out is None:
                    # quat array
                    if inputs.shape == (4,):
                        q = Quaternion(q=inputs)
                        q -= self
                        return q.as_numpy
                # __isub__
                else:
                    out = out[0]
                    if out.shape == (4,):
                        q = Quaternion(q=out)
                        q -= self
                        out[:] = q.as_numpy
                        return out

        raise RuntimeError

    def __normalize(self):
        """
        Normalize the quaternion data in place.

        :returns: ``None``
        :rtype: None
        """

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
        """
        Enter a mutation block before re-normalization.

        :returns: This quaternion instance.
        :rtype: :class:`Quaternion`
        """

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Normalize the quaternion when leaving a mutation block.

        :param exc_type: Exception type, if any.
        :type exc_type: type | None
        :param exc_val: Exception instance, if any.
        :type exc_val: BaseException | None
        :param exc_tb: Traceback, if any.
        :type exc_tb: object
        :returns: ``None``
        :rtype: None
        """

        self.__normalize()

    def __init__(self, w=None, x=None, y=None, z=None, q=None):
        """
        Create and normalize a quaternion.

        :param w: Scalar component when ``q`` is not supplied.
        :type w: float | None
        :param x: X component when ``q`` is not supplied.
        :type x: float | None
        :param y: Y component when ``q`` is not supplied.
        :type y: float | None
        :param z: Z component when ``q`` is not supplied.
        :type z: float | None
        :param q: Existing quaternion array to wrap.
        :type q: :class:`numpy.ndarray` | None
        """

        if q is None:
            self._data = np.array([w, x, y, z], dtype=np.float32)
        else:
            self._data = q

        self.__normalize()

    @property
    def w(self) -> float:
        """
        Return the scalar component.

        :returns: ``w`` component.
        :rtype: float
        """

        return float(self._data[0])

    @w.setter
    def w(self, value: [float, _d]):
        """
        Set the scalar component.

        :param value: New ``w`` value.
        :type value: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """

        self._data[0] = value

    @property
    def x(self) -> float:
        """
        Return the X vector component.

        :returns: ``x`` component.
        :rtype: float
        """

        return float(self._data[1])

    @x.setter
    def x(self, value: [float, _d]):
        """
        Set the X vector component.

        :param value: New ``x`` value.
        :type value: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """

        self._data[1] = value

    @property
    def y(self) -> float:
        """
        Return the Y vector component.

        :returns: ``y`` component.
        :rtype: float
        """

        return float(self._data[2])

    @y.setter
    def y(self, value: [float, _d]):
        """
        Set the Y vector component.

        :param value: New ``y`` value.
        :type value: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """

        self._data[2] = value

    @property
    def z(self) -> float:
        """
        Return the Z vector component.

        :returns: ``z`` component.
        :rtype: float
        """

        return float(self._data[3])

    @z.setter
    def z(self, value: [float, _d]):
        """
        Set the Z vector component.

        :param value: New ``z`` value.
        :type value: float | :class:`~harness_designer.geometry.decimal.Decimal`
        :returns: ``None``
        :rtype: None
        """

        self._data[3] = value

    @property
    def as_numpy(self):
        """
        Return the underlying quaternion array.

        :returns: Raw quaternion data.
        :rtype: :class:`numpy.ndarray`
        """

        return self._data

    @property
    def as_float(self):
        """
        Return the quaternion components as floats.

        :returns: ``[w, x, y, z]`` values.
        :rtype: list[float]
        """

        return self._data.tolist()

    @property
    def as_decimal(self):
        """
        Return the quaternion components as decimals.

        :returns: Decimal ``(w, x, y, z)`` values.
        :rtype: tuple[:class:`~harness_designer.geometry.decimal.Decimal`,
                      :class:`~harness_designer.geometry.decimal.Decimal`,
                      :class:`~harness_designer.geometry.decimal.Decimal`,
                      :class:`~harness_designer.geometry.decimal.Decimal`]
        """

        w, x, y, z = self.as_float
        return _d(w), _d(x), _d(y), _d(z)

    def __isub__(self, other: "Quaternion") -> Self:
        """
        Subtract ``other`` from this quaternion in place.

        :param other: Quaternion to subtract.
        :type other: :class:`Quaternion`
        :returns: This quaternion instance.
        :rtype: Self
        :raises TypeError: If ``other`` is not a :class:`Quaternion`.
        """

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
        """
        Return ``self`` combined with the inverse of ``other``.

        :param other: Quaternion to subtract.
        :type other: :class:`Quaternion`
        :returns: Quaternion difference.
        :rtype: :class:`Quaternion`
        :raises TypeError: If ``other`` is not a :class:`Quaternion`.
        """

        if not isinstance(other, Quaternion):
            raise TypeError

        return self.__mul(-other, self)

    @staticmethod
    def __mul(qa: "Quaternion", qb: "Quaternion") -> "Quaternion":
        """
        Multiply two quaternions.

        :param qa: Left quaternion operand.
        :type qa: :class:`Quaternion`
        :param qb: Right quaternion operand.
        :type qb: :class:`Quaternion`
        :returns: Quaternion product.
        :rtype: :class:`Quaternion`
        """

        wb, xb, yb, zb = qb.as_decimal
        wa, xa, ya, za = qa.as_decimal
        q = np.array([wb * wa - xb * xa - yb * ya - zb * za,
                      wb * xa + xb * wa + yb * za - zb * ya,
                      wb * ya - xb * za + yb * wa + zb * xa,
                      wb * za + xb * ya - yb * xa + zb * wa], dtype=float)

        return Quaternion(q=q)

    def __iadd__(self, other: "Quaternion") -> Self:
        """
        Compose this quaternion with ``other`` in place.

        :param other: Quaternion to add.
        :type other: :class:`Quaternion`
        :returns: This quaternion instance.
        :rtype: Self
        :raises TypeError: If ``other`` is not a :class:`Quaternion`.
        """

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
        """
        Compose this quaternion with ``other``.

        :param other: Quaternion to add.
        :type other: :class:`Quaternion`
        :returns: Combined quaternion.
        :rtype: :class:`Quaternion`
        :raises TypeError: If ``other`` is not a :class:`Quaternion`.
        """

        if not isinstance(other, Quaternion):
            raise TypeError

        diff = self.__sub__(other)
        return self.__mul(diff, self)

    def __itruediv__(self, other: "Quaternion") -> Self:
        """
        Divide quaternion components in place.

        :param other: Scalar or quaternion divisor.
        :type other: :class:`Quaternion` | int | float
        :returns: This quaternion instance.
        :rtype: Self
        :raises TypeError: If ``other`` is an unsupported type.
        """

        if isinstance(other, (int, float)):
            other = np.array(
                [other, other, other, other], dtype=np.float32)

        elif not isinstance(other, Quaternion):
            raise TypeError
        else:
            other = other.as_numpy

        w1, x1, y1, z1 = self.as_decimal
        w2, x2, y2, z2 = [_d(item) for item in other.tolist()]

        def _div(v1, v2):
            """
            Safely divide two scalar values.

            :param v1: Dividend.
            :type v1: :class:`~harness_designer.geometry.decimal.Decimal`
            :param v2: Divisor.
            :type v2: :class:`~harness_designer.geometry.decimal.Decimal`
            :returns: Quotient or ``0.0`` when dividing by zero.
            :rtype: :class:`~harness_designer.geometry.decimal.Decimal` | float
            """

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
        """
        Return a component-wise divided quaternion.

        :param other: Scalar or quaternion divisor.
        :type other: :class:`Quaternion` | int | float
        :returns: New quaternion containing the divided components.
        :rtype: :class:`Quaternion`
        :raises TypeError: If ``other`` is an unsupported type.
        """

        if isinstance(other, (int, float)):
            other = np.array([other, other, other, other], dtype=np.float32)
        elif not isinstance(other, Quaternion):
            raise TypeError
        else:
            other = other.as_numpy

        w1, x1, y1, z1 = self.as_decimal
        w2, x2, y2, z2 = [_d(item) for item in other.tolist()]

        def _div(v1, v2):
            """
            Safely divide two scalar values.

            :param v1: Dividend.
            :type v1: :class:`~harness_designer.geometry.decimal.Decimal`
            :param v2: Divisor.
            :type v2: :class:`~harness_designer.geometry.decimal.Decimal`
            :returns: Quotient or ``0.0`` when dividing by zero.
            :rtype: :class:`~harness_designer.geometry.decimal.Decimal` | float
            """

            try:
                return v1 / v2
            except ZeroDivisionError:
                return 0.0

        w = _div(w1, w2)
        x = _div(x1, x2)
        y = _div(y1, y2)
        z = _div(z1, z2)

        return Quaternion(w, x, y, z)

    def __matmul__(
        self,
        other: _point.Point | np.ndarray
    ) -> _point.Point | np.ndarray:

        """
        Return ``other`` rotated by this quaternion.

        :param other: Point or vector to rotate.
        :type other: :class:`~harness_designer.geometry.point.Point` |
                     :class:`numpy.ndarray`
        :returns: Rotated copy of ``other``.
        :rtype: :class:`~harness_designer.geometry.point.Point` |
                :class:`numpy.ndarray`
        """

        w, x, y, z = self.as_float

        # Vectorized quaternion rotation formula
        qvec = np.array([x, y, z], dtype=np.float32)

        if isinstance(other, _point.Point):
            array = other.as_numpy

            t = np.cross(qvec, array)
            result = array + 2.0 * w * t + 2.0 * np.cross(qvec, t)

            return _point.Point(*result)
        else:
            t = np.cross(qvec, other)
            result = other + 2.0 * w * t + 2.0 * np.cross(qvec, t)
            return result

    def __rmatmul__(
        self,
        other: _point.Point | np.ndarray
    ) -> _point.Point | np.ndarray:

        """
        Rotate ``other`` in place when possible.

        :param other: Point or vector to rotate.
        :type other: :class:`~harness_designer.geometry.point.Point` |
                     :class:`numpy.ndarray`
        :returns: Mutated operand.
        :rtype: :class:`~harness_designer.geometry.point.Point` |
                :class:`numpy.ndarray`
        """

        w, x, y, z = self.as_float

        # Vectorized quaternion rotation formula
        qvec = np.array([x, y, z], dtype=np.float32)

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
        """
        Iterate over ``w, x, y, z``.

        :returns: Iterator over quaternion components.
        :rtype: collections.abc.Iterable[float]
        """

        return iter(self._data.tolist())

    def conj(self) -> "Quaternion":
        """
        Return the quaternion conjugate.

        :returns: Conjugated quaternion.
        :rtype: :class:`Quaternion`
        """

        w, x, y, z = self._data.tolist()
        return Quaternion(w, -x, -y, -z)

    def __neg__(self) -> "Quaternion":
        """
        Return the multiplicative inverse quaternion.

        :returns: Inverse quaternion.
        :rtype: :class:`Quaternion`
        """

        q = self._data

        return Quaternion(*[float(item) for item in self.conj() / np.dot(q, q)])

    @classmethod
    def from_euler(cls, x: float, y: float, z: float) -> "Quaternion":
        """
        Build a quaternion from Euler rotation angles in degrees.

        :param x: Rotation about the X axis.
        :type x: float
        :param y: Rotation about the Y axis.
        :type y: float
        :param z: Rotation about the Z axis.
        :type z: float
        :returns: Quaternion representing the rotation.
        :rtype: :class:`Quaternion`
        """

        rx, ry, rz = [_d(item) for item in np.deg2rad([x, y, z])]
        qx = cls(math.cos(rx / TWO), math.sin(rx / TWO), 0.0, 0.0)
        qy = cls(math.cos(ry / TWO), 0.0, math.sin(ry / TWO), 0.0)
        qz = cls(math.cos(rz / TWO), 0.0, 0.0, math.sin(rz / TWO))

        q = cls.__mul(qz, cls.__mul(qx, qy))  # qy ⊗ qx ⊗ qz
        return cls(*q.as_float)

    @property
    def as_euler(self) -> tuple[float, float, float]:
        """
        Return the quaternion as Euler angles in degrees.

        :returns: ``(x, y, z)`` Euler angles.
        :rtype: tuple[float, float, float]
        """

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
        """
        Return the quaternion as a ``3 x 3`` rotation matrix.

        :returns: Rotation matrix.
        :rtype: :class:`numpy.ndarray`
        """

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
                         ], dtype=np.float32)

    @classmethod
    def from_axis_angle(cls, axis, angle):
        """
        Create quaternion from axis-angle representation


        :param axis: Rotation axis.
        :type axis: list[int | float, int | float, int | float] |
                    :class:`numpy.ndarray`
        :param angle: Rotation angle in radians.
        :type angle: float

        :returns: Quaternion representing the rotation.
        :rtype: :class:`Quaternion`
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
