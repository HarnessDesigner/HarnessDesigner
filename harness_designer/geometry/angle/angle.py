# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Angle wrappers that combine Euler angles and quaternions."""

import math
from typing import Self, Callable, Iterable, Union
import weakref
import numpy as np

from . import quaternion as _quaternion
from .. import point as _point
from ..decimal import Decimal as _d


ONE = 1.0
TWO = 2.0


class AngleMeta(type):
    """Metaclass that reuses :class:`Angle` instances keyed by ``db_id``."""

    _instances = {}

    @classmethod
    def _remove_instance(cls, ref):
        """
        Remove a collected cached angle reference.

        :param ref: Weak reference stored in :attr:`_instances`.
        :type ref: :class:`weakref.ReferenceType`
        :returns: ``None``
        :rtype: None
        """

        for key, value in cls._instances.items():
            if ref == value:
                break
        else:
            return

        del cls._instances[key]

    def __call__(cls, q: _quaternion.Quaternion | None = None,
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | str | None = None):
        """
        Return a cached or new :class:`Angle` instance.

        :param q: Quaternion backing the angle.
        :type q: :class:`~.quaternion.Quaternion` | None
        :param euler_angles: Optional Euler-angle cache.
        :type euler_angles: list[float, float, float] | None
        :param db_id: Optional cache key.
        :type db_id: int | str | None
        :returns: Shared or new angle instance.
        :rtype: :class:`Angle`
        """

        if db_id is not None:
            if db_id in cls._instances:
                instance = cls._instances[db_id]()
            else:
                instance = None

            if instance is None:
                instance = super().__call__(q, euler_angles, db_id)
                cls._instances[db_id] = weakref.ref(instance, cls._remove_instance)
        else:
            instance = super().__call__(q, euler_angles, db_id)

        return instance


class Angle(metaclass=AngleMeta):
    """Represent an orientation using quaternion and Euler-angle forms."""

    def __array_ufunc__(self, func, method, inputs, instance, out=None, **kwargs):  # NOQA
        """
        Handle selected NumPy ufuncs involving an angle.

        :param func: NumPy ufunc being invoked.
        :type func: object
        :param method: Ufunc method name.
        :type method: str
        :param inputs: Left-hand NumPy input.
        :type inputs: :class:`numpy.ndarray` | None
        :param instance: Operand instance chosen by NumPy dispatch.
        :type instance: :class:`numpy.ndarray` | None
        :param out: Optional output array.
        :type out: tuple[:class:`numpy.ndarray`] | None
        :param kwargs: Additional ufunc keyword arguments.
        :type kwargs: dict
        :returns: Angle-compatible NumPy result.
        :rtype: :class:`numpy.ndarray` | :class:`~.quaternion.Quaternion` | :class:`Angle`
        :raises RuntimeError: If the ufunc is unsupported.
        """

        if func == np.matmul:
            if isinstance(instance, Angle):
                # __matmul__
                if out is None:
                    return inputs @ self._q
                # __imatmul__
                else:
                    out = out[0]
                    out @= self._q
                    return out

        if func == np.add:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Angle):
                # __add__
                if out is None:
                    # euler angle array
                    if inputs.shape == (3,):
                        # arr = np.array(self.as_float, dtype=np.float32)
                        angle = self.from_euler(*inputs.tolist())
                        angle += self
                        return angle.as_euler_numpy
                    # quat array
                    elif inputs.shape == (4,):
                        angle = self.from_quat(inputs.tolist())
                        angle += self
                        return angle.as_quat_numpy
                    # we assume this is a matrix array
                    else:
                        angle = self.from_matrix(inputs)
                        angle += self
                        return angle.as_matrix_numpy
                # __iadd__
                else:
                    out = out[0]

                    # euler angle array
                    if out.shape == (3,):
                        # arr = np.array(self.as_float, dtype=np.float32)
                        angle = self.from_euler(*out.tolist())
                        angle += self
                        out[:] = angle.as_euler_numpy
                        return out
                    # quat array
                    elif out.shape == (4,):
                        angle = self.from_quat(out.tolist())
                        angle += self
                        out[:] = angle.as_quat_numpy
                        return out

                    # we assume this is a matrix array
                    else:
                        angle = self.from_matrix(out)
                        angle += self
                        out[:] = angle.as_matrix_numpy
                        return out

        if func == np.subtract:
            # numpy array is left hand and class instance is right hand
            if isinstance(instance, Angle):
                # __sub__
                if out is None:
                    # euler angle array
                    if inputs.shape == (3,):
                        # arr = np.array(self.as_float, dtype=np.float32)
                        angle = self.from_euler(*inputs.tolist())
                        angle -= self
                        return angle.as_euler_numpy
                    # quat array
                    elif inputs.shape == (4,):
                        angle = self.from_quat(inputs.tolist())
                        angle -= self
                        return angle.as_quat_numpy
                    # we assume this is a matrix array
                    else:
                        angle = self.from_matrix(inputs)
                        angle += self
                        return angle.as_matrix_numpy

                # __isub__
                else:
                    out = out[0]

                    # euler angle array
                    if out.shape == (3,):
                        # arr = np.array(self.as_float, dtype=np.float32)
                        angle = self.from_euler(*out.tolist())
                        angle -= self
                        out[:] = angle.as_euler_numpy
                        return out
                    # quat array
                    elif out.shape == (4,):
                        angle = self.from_quat(out.tolist())
                        angle -= self
                        out[:] = angle.as_quat_numpy
                        return out

                    # we assume this is a matrix array
                    else:
                        angle = self.from_matrix(out)
                        angle -= self
                        out[:] = angle.as_matrix_numpy
                        return out

        raise RuntimeError

    def __init__(self, q: _quaternion.Quaternion | None = None, 
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | str | None = None):
        """
        Create an angle.

        :param q: Quaternion representation. Identity is used when omitted.
        :type q: :class:`~.quaternion.Quaternion` | None
        :param euler_angles: Optional cached Euler angles in degrees.
        :type euler_angles: list[float, float, float] | None
        :param db_id: Optional shared-instance identifier.
        :type db_id: int | str | None
        """

        self.db_id = db_id

        if q is None:
            q = _quaternion.Quaternion(1.0, 0.0, 0.0, 0.0)

        self._q = q

        if euler_angles is None:
            self.__euler_angles = None
        else:
            self.__euler_angles = np.array(euler_angles, dtype=np.float32)

        self.__callbacks = []
        self._ref_count = 0

        self._matrix = self._q.as_matrix

    def __enter__(self):
        """
        Enter a batched update block.

        :returns: This angle instance.
        :rtype: :class:`Angle`
        """

        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Leave a batched update block.

        :param exc_type: Exception type, if any.
        :type exc_type: type | None
        :param exc_val: Exception value, if any.
        :type exc_val: BaseException | None
        :param exc_tb: Traceback, if any.
        :type exc_tb: object
        :returns: ``None``
        :rtype: None
        """

        self._ref_count -= 1

    def __remove_callback(self, ref):
        """
        Remove a dead callback reference.

        :param ref: Callback weak reference.
        :type ref: :class:`weakref.WeakMethod`
        :returns: ``None``
        :rtype: None
        """

        try:
            self.__callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, cb: Callable[["Angle"], None]) -> bool:
        """
        Register a callback to run after updates.

        :param cb: Bound method receiving this angle.
        :type cb: collections.abc.Callable[[ :class:`Angle` ], None]
        :returns: ``True`` after registration.
        :rtype: bool
        """

        # We don't explicitly check to see if a callback is already registered.
        # What we care about is if a callback is called only one time and that
        # check is done when the callbacks are being executed. If there happens
        # to be a duplicate, the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(cb, self.__remove_callback)
        self.__callbacks.append(ref)
        return True

    def unbind(self, cb: Callable[["Angle"], None]) -> None:
        """
        Remove all registrations for a callback.

        :param cb: Previously registered callback.
        :type cb: collections.abc.Callable[[ :class:`Angle` ], None]
        :returns: ``None``
        :rtype: None
        """

        for ref in self.__callbacks[:]:
            callback = ref()
            if callback is None:
                self.__callbacks.remove(ref)
            elif callback == cb:
                # We don't return after locating a matching callback in the
                # event a callback was registered more than one time. Duplicates
                # are also removed at the time callbacks get called but if an update
                # to an angle never occurs we want to make sure that we explicitly
                # unbind all callbacks including duplicates.
                self.__callbacks.remove(ref)

    def _process_update(self):
        """
        Notify bound callbacks unless batching is active.

        :returns: ``None``
        :rtype: None
        """

        if self._ref_count:
            return

        for ref in self.__callbacks[:]:
            cb = ref()
            if cb is None:
                self.__callbacks.remove(ref)
            else:
                cb(self)

    @property
    def inverse(self) -> "Angle":
        """
        Return the inverse rotation.

        :returns: Inverse angle.
        :rtype: :class:`Angle`
        """

        q = -self._q
        return Angle(q)
    
    def __neg__(self) -> "Angle":
        """
        Return the inverse rotation.

        :returns: Inverse angle.
        :rtype: :class:`Angle`
        """

        q = -self._q
        return Angle(q)

    @property
    def x(self) -> float:
        """
        Return the cached X Euler angle or ``nan`` when UNKNOWN.

        :returns: X-axis rotation in degrees, or ``nan`` when the Euler cache is unavailable.
        :rtype: float
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles.tolist()[0]

    @x.setter
    def x(self, value: float):
        """
        Set the cached X Euler angle and update the quaternion.

        :param value: New X-axis rotation in degrees.
        :type value: float
        :returns: ``None``
        :rtype: None
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[0] = value
        
        q = _quaternion.Quaternion.from_euler(*self.__euler_angles)
        self.__update_quat(q)

        self._process_update()

    def __update_quat(self, q):
        """
        Copy quaternion component values into the cached quaternion.

        :param q: Source quaternion.
        :type q: :class:`~.quaternion.Quaternion`
        :returns: ``None``
        :rtype: None
        """

        self._q.w = q.w
        self._q.x = q.x
        self._q.y = q.y
        self._q.z = q.z
        self.__update_matrix()

    @property
    def y(self) -> float:
        """
        Return the cached Y Euler angle or ``nan`` when UNKNOWN.

        :returns: Y-axis rotation in degrees, or ``nan`` when the Euler cache is unavailable.
        :rtype: float
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles.tolist()[1]

    @y.setter
    def y(self, value: float):
        """
        Set the cached Y Euler angle and update the quaternion.

        :param value: New Y-axis rotation in degrees.
        :type value: float
        :returns: ``None``
        :rtype: None
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[1] = value
        q = _quaternion.Quaternion.from_euler(*self.__euler_angles)

        self.__update_quat(q)
        self._process_update()

    @property
    def z(self) -> float:
        """
        Return the cached Z Euler angle or ``nan`` when UNKNOWN.

        :returns: Z-axis rotation in degrees, or ``nan`` when the Euler cache is unavailable.
        :rtype: float
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles.tolist()[2]

    @z.setter
    def z(self, value: float):
        """
        Set the cached Z Euler angle and update the quaternion.

        :param value: New Z-axis rotation in degrees.
        :type value: float
        :returns: ``None``
        :rtype: None
        """

        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[2] = value

        q = _quaternion.Quaternion.from_euler(*self.__euler_angles.tolist())

        self.__update_quat(q)
        self._process_update()

    def copy(self) -> "Angle":
        """
        Return a copy of this angle.

        :returns: New angle with the same quaternion and cached Euler data when available.
        :rtype: :class:`Angle`
        """

        if self.__euler_angles is not None:
            return Angle.from_quat(self._q.as_numpy.tolist(), euler_angles=self.__euler_angles.tolist())
        else:
            return Angle.from_quat(self._q.as_numpy.tolist())

    @staticmethod
    def __get_quat_from_other(other: Union["Angle", np.ndarray | _quaternion.Quaternion]) -> _quaternion.Quaternion:
        """
        Convert supported operands into a quaternion.

        :param other: Angle-like operand.
        :type other: :class:`Angle` | :class:`numpy.ndarray` | :class:`~.quaternion.Quaternion`
        :returns: Converted quaternion.
        :rtype: :class:`~.quaternion.Quaternion`
        :raises ValueError: If a NumPy array has an unsupported shape.
        :raises TypeError: If ``other`` is an unsupported type.
        """

        if isinstance(other, Angle):
            quat = other.as_quat_numpy
            quat = _quaternion.Quaternion(q=quat)

        elif isinstance(other, np.ndarray):
            if other.shape == (4,):
                w, x, y, z = (float(item) for item in other)
                quat = _quaternion.Quaternion(w, x, y, z)
            elif other.shape == (3,):
                x, y, z = (float(item) for item in other)
                quat = _quaternion.Quaternion.from_euler(x, y, z)
            else:
                raise ValueError('array dimension is incorrect')
        elif isinstance(other, _quaternion.Quaternion):
            quat = other
        else:
            raise TypeError(f'invalid type "{type(other)}"')

        return quat

    def __update_matrix(self):
        """
        Refresh the cached rotation matrix from the quaternion.

        :returns: ``None``
        :rtype: None
        """

        matrix = self._q.as_matrix

        for i in range(3):
            for j in range(3):
                self._matrix[i][j] = matrix[i][j]

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        """
        Compose this angle with ``other`` in place.

        :param other: Angle-like operand.
        :type other: :class:`Angle` | :class:`numpy.ndarray`
        :returns: This angle instance.
        :rtype: Self
        """

        if isinstance(other, Angle):
            x2, y2, z2 = other.x, other.y, other.z
            if math.nan not in (x2, y2, z2) and self.__euler_angles is not None:
                x1, y1, z1 = [_d(item) for item in self.__euler_angles.tolist()]
                x2, y2, z2 = [_d(item) for item in (x2, y2, z2)]

                x1 += x2
                y1 += y2
                z1 += z2

                self.__euler_angles[0] = float(x1)
                self.__euler_angles[1] = float(y1)
                self.__euler_angles[2] = float(z1)

                q = _quaternion.Quaternion.from_euler(*self.__euler_angles.tolist())

                self.__update_quat(q)
                self._process_update()
                return

        self._q += self.__get_quat_from_other(other)
        self.__update_matrix()
        self._process_update()
        return self

    def __add__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        """
        Return the composition of this angle with ``other``.

        :param other: Angle-like operand.
        :type other: :class:`Angle` | :class:`numpy.ndarray`
        :returns: Combined angle.
        :rtype: :class:`Angle`
        """

        if isinstance(other, Angle):
            x2, y2, z2 = other.x, other.y, other.z
            if math.nan not in (x2, y2, z2) and self.__euler_angles is not None:
                x1, y1, z1 = [_d(item) for item in self.__euler_angles.tolist()]
                x2, y2, z2 = [_d(item) for item in (x2, y2, z2)]

                x = x1 + x2
                y = y1 + y2
                z = z1 + z2

                return self.from_euler(float(x), float(y), float(z))

        q = self._q + self.__get_quat_from_other(other)

        return self.from_quat(q)

    def __isub__(self, other: Union["Angle", np.ndarray]) -> Self:
        """
        Subtract ``other`` from this angle in place.

        :param other: Angle-like operand.
        :type other: :class:`Angle` | :class:`numpy.ndarray`
        :returns: This angle instance.
        :rtype: Self
        """

        if isinstance(other, Angle):
            x2, y2, z2 = other.x, other.y, other.z
            if math.nan not in (x2, y2, z2) and self.__euler_angles is not None:
                x1, y1, z1 = [_d(item) for item in self.__euler_angles.tolist()]
                x2, y2, z2 = [_d(item) for item in (x2, y2, z2)]

                x1 -= x2
                y1 -= y2
                z1 -= z2

                self.__euler_angles[0] = float(x1)
                self.__euler_angles[1] = float(y1)
                self.__euler_angles[2] = float(z1)

                q = _quaternion.Quaternion.from_euler(*self.__euler_angles.tolist())

                self.__update_quat(q)
                self._process_update()
                return

        self._q -= self.__get_quat_from_other(other)
        self.__update_matrix()
        self._process_update()
        return self

    def __sub__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        """
        Return this angle minus ``other``.

        :param other: Angle-like operand.
        :type other: :class:`Angle` | :class:`numpy.ndarray`
        :returns: Angle difference.
        :rtype: :class:`Angle`
        """

        if isinstance(other, Angle):
            x2, y2, z2 = other.x, other.y, other.z
            if math.nan not in (x2, y2, z2) and self.__euler_angles is not None:
                x1, y1, z1 = [_d(item) for item in self.__euler_angles.tolist()]
                x2, y2, z2 = [_d(item) for item in (x2, y2, z2)]

                x = x1 - x2
                y = y1 - y2
                z = z1 - z2

                return self.from_euler(float(x), float(y), float(z))

        q = self._q - self.__get_quat_from_other(other)
        return self.from_quat(q)

    def __rmatmul__(self, other: Union[np.ndarray, _point.Point]) -> np.ndarray | _point.Point:
        """
        Apply this angle to ``other`` in place when supported.

        :param other: Vector or point to rotate.
        :type other: :class:`numpy.ndarray` | :class:`~harness_designer.geometry.point.Point`
        :returns: Rotated operand.
        :rtype: :class:`numpy.ndarray` | :class:`~harness_designer.geometry.point.Point`
        """

        other @= self._q
        return other

        # if isinstance(other, np.ndarray):
        #     if other.ndim == 1:
        #         result = self._matrix @ other
        #         other[:] = result
        #     else:
        #         other[:] = (self._matrix @ other.T).T
        # elif isinstance(other, _point.Point):
        #     values = self._matrix @ other.as_numpy
        #
        #     x = float(values[0])
        #     y = float(values[1])
        #     z = float(values[2])
        #
        #     with other:
        #         other.x = x
        #         other.y = y
        #
        #     other.z = z
        # else:
        #     raise RuntimeError('sanity check')
        #
        # return other

    def __matmul__(self, other: Union[np.ndarray, _point.Point]) -> np.ndarray | _point.Point:
        """
        Return ``other`` rotated by this angle.

        :param other: Vector or point to rotate.
        :type other: :class:`numpy.ndarray` | :class:`~harness_designer.geometry.point.Point`
        :returns: Rotated copy of ``other``.
        :rtype: :class:`numpy.ndarray` | :class:`~harness_designer.geometry.point.Point`
        """

        other = other @ self._q
        return other

        # if isinstance(other, np.ndarray):
        #     if other.ndim == 1:
        #         return self._matrix @ other
        #     else:
        #         return (self._matrix @ other.T).T
        # elif isinstance(other, _point.Point):
        #     values = self._matrix @ other.as_numpy
        #     x = float(values[0])
        #     y = float(values[1])
        #     z = float(values[2])
        #
        #     other = _point.Point(x, y, z)
        # else:
        #     raise RuntimeError('sanity check')
        #
        # return other

    def __bool__(self):
        """
        Return whether this angle is not the identity rotation.

        :returns: ``True`` when the quaternion differs from identity.
        :rtype: bool
        """

        arr = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        return not all(np.isclose(self.as_quat_numpy, arr))

    def __eq__(self, other: "Angle") -> bool:
        """
        Return whether this angle matches ``other``.

        :param other: Angle to compare against.
        :type other: :class:`Angle`
        :returns: ``True`` when the quaternions are numerically equal.
        :rtype: bool
        """

        other = other.as_quat_numpy
        return all(np.isclose(other, self.as_quat_numpy))

    def __ne__(self, other: "Angle") -> bool:
        """
        Return whether this angle differs from ``other``.

        :param other: Angle to compare against.
        :type other: :class:`Angle`
        :returns: ``True`` when the quaternions are not numerically equal.
        :rtype: bool
        """

        return not self.__eq__(other)

    @property
    def as_euler_numpy(self) -> np.ndarray:
        """
        Return cached Euler angles as a NumPy array.

        :returns: Cached Euler values.
        :rtype: :class:`numpy.ndarray`
        """

        return self.__euler_angles

    @property
    def as_euler_float(self) -> list[float, float, float]:
        """
        Return cached Euler angles as floats.

        :returns: ``[x, y, z]`` Euler values.
        :rtype: list[float, float, float]
        """

        return self.__euler_angles.tolist()

    @property
    def as_quat_numpy(self) -> np.ndarray:
        """
        Return quaternion components as a NumPy array.

        :returns: Quaternion data.
        :rtype: :class:`numpy.ndarray`
        """

        return self._q.as_numpy

    @property
    def as_quat_float(self) -> list[float, float, float]:
        """
        Return quaternion components as floats.

        :returns: Quaternion values.
        :rtype: list[float, float, float]
        """

        return self._q.as_numpy.tolist()

    @property
    def as_euler_int(self) -> tuple[int, int, int]:
        """
        Return cached Euler angles truncated to integers.

        :returns: Integer Euler values.
        :rtype: tuple[int, int, int]
        """

        x, y, z = self.as_euler_float
        return int(x), int(y), int(z)

    @property
    def as_matrix_float(
        self
    ) -> list[list[float, float, float], list[float, float, float], list[float, float, float]]:
        """
        Return the cached rotation matrix as nested float lists.

        :returns: Rotation matrix rows.
        :rtype: list[list[float, float, float], list[float, float, float], list[float, float, float]]
        """

        return self._matrix.tolist()

    @property
    def as_matrix_numpy(self) -> np.ndarray:
        """
        Return the cached rotation matrix.

        :returns: Rotation matrix.
        :rtype: :class:`numpy.ndarray`
        """

        return self._matrix

    def __iter__(self) -> Iterable[float]:
        """
        Iterate over Euler-angle components.

        :returns: Iterator yielding Euler angles in degrees.
        :rtype: collections.abc.Iterable[float]
        """

        x, y, z = self._q.as_euler

        return iter([x, y, z])

    def __str__(self) -> str:
        """
        Return a readable Euler-angle string.

        :returns: String form of the angle.
        :rtype: str
        """

        x, y, z = self._q.as_euler

        return f'X: {x}, Y: {y}, Z: {z}'

    @classmethod
    def from_direction(cls, direction: np.ndarray) -> "Angle":
        """Create quaternion to rotate +Z axis to align with direction"""

        # Unit cylinder points along +Z, rotate it to point along 'direction'

        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 0.0001:
            return cls.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity
        if abs(dot + 1.0) < 0.0001:
            # 180 degree rotation around X axis
            return cls.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return cls.from_axis_angle(axis, angle)

    @classmethod
    def from_euler(cls, x: float, y: float, z: float, db_id: str | None = None) -> "Angle":
        """
        Create an angle from Euler angles in degrees.

        :param x: Rotation about the X axis.
        :type x: float
        :param y: Rotation about the Y axis.
        :type y: float
        :param z: Rotation about the Z axis.
        :type z: float
        :param db_id: Optional shared-instance identifier.
        :type db_id: str | None
        :returns: New angle instance.
        :rtype: :class:`Angle`
        """

        q = _quaternion.Quaternion.from_euler(x, y, z)  # NOQA
        ret = cls(q, [x, y, z], db_id)
        return ret

    @classmethod
    def from_quat(cls, q: list[float, float, float, float] | np.ndarray | _quaternion.Quaternion,
                  euler_angles: list[float, float, float] | None = None, db_id: str | None = None) -> "Angle":
        """
        Create an angle from quaternion data.

        :param q: Quaternion components or quaternion object.
        :type q: list[float, float, float, float] | :class:`numpy.ndarray` | :class:`~.quaternion.Quaternion`
        :param euler_angles: Optional cached Euler values.
        :type euler_angles: list[float, float, float] | None
        :param db_id: Optional shared-instance identifier.
        :type db_id: str | None
        :returns: New angle instance.
        :rtype: :class:`Angle`
        """

        if not isinstance(q, _quaternion.Quaternion):
            q = _quaternion.Quaternion(*[float(item) for item in q])  # NOQA

        return cls(q, euler_angles, db_id)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray, db_id: str | None = None) -> "Angle":
        """Convert a 3x3 rotation matrix to a unit quaternion (w, x, y, z)."""

        m00 = matrix[0, 0]
        m01 = matrix[0, 1]
        m02 = matrix[0, 2]

        m10 = matrix[1, 0]
        m11 = matrix[1, 1]
        m12 = matrix[1, 2]

        m20 = matrix[2, 0]
        m21 = matrix[2, 1]
        m22 = matrix[2, 2]

        tr = m00 + m11 + m22

        if tr > 0.0:
            S = np.sqrt(tr + ONE) * TWO  # 4*w
            w = 0.25 * S
            x = (m21 - m12) / S
            y = (m02 - m20) / S
            z = (m10 - m01) / S
        elif m00 > m11 and m00 > m22:
            S = np.sqrt(ONE + m00 - m11 - m22) * TWO  # 4*x
            w = (m21 - m12) / S
            x = 0.25 * S
            y = (m01 + m10) / S
            z = (m02 + m20) / S
        elif m11 > m22:
            S = np.sqrt(ONE + m11 - m00 - m22) * TWO  # 4*y
            w = (m02 - m20) / S
            x = (m01 + m10) / S
            y = 0.25 * S
            z = (m12 + m21) / S
        else:
            S = np.sqrt(ONE + m22 - m00 - m11) * TWO  # 4*z
            w = (m10 - m01) / S
            x = (m02 + m20) / S
            y = (m12 + m21) / S
            z = 0.25 * S

        q = _quaternion.Quaternion(w, x, y, z)

        # optional: canonicalize sign
        if q.w < 0:
            q = -q

        return cls(q, db_id=db_id)

    @classmethod
    def from_points(cls, p1: _point.Point, p2: _point.Point,
                    db_id: str | None = None) -> "Angle":  # NOQA
        """
        Create an angle that aligns the local forward axis to the line ``p1`` → ``p2``.

        :param p1: Start point.
        :type p1: :class:`~harness_designer.geometry.point.Point`
        :param p2: End point.
        :type p2: :class:`~harness_designer.geometry.point.Point`
        :param db_id: Optional shared-instance identifier.
        :type db_id: str | None
        :returns: Angle derived from the two points.
        :rtype: :class:`Angle`
        :raises RuntimeError: If a valid right vector cannot be computed.
        """

        # the sign for all of the verticies in the array needs to be flipped in
        # order to handle the -Z axis being near
        p1 = -p1.as_numpy
        p2 = -p2.as_numpy

        f = p2 - p1

        fn = np.linalg.norm(f)
        if fn < 1e-6:
            return cls(db_id=db_id)

        f = f / fn  # world-space direction of the line

        local_forward = np.array([0.0, 0.0, -1.0],
                                 dtype=np.float32)

        nz = np.nonzero(local_forward)[0][0]
        sign = np.sign(local_forward[nz])
        forward_world = f * sign

        up = np.asarray((0.0, 1.0, 0.0),
                        dtype=np.float32)

        if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
            up = np.array([0.0, 0.0, 1.0],
                          dtype=np.float32)

            if np.allclose(np.abs(np.dot(forward_world, up)), 1.0, atol=1e-8):
                up = np.array([1.0, 0.0, 0.0],
                              dtype=np.float32)

        right = np.cross(up, forward_world)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            raise RuntimeError("degenerate right vector")

        right = right / rn

        true_up = np.cross(forward_world, right)  # NOQA

        rot = np.column_stack((right, true_up, forward_world))

        return cls.from_matrix(rot, db_id)

    @classmethod
    def from_axis_angle(cls, axis: np.ndarray, angle: float, db_id: str | None = None):
        """
        Create an angle from an axis-angle rotation.

        :param axis: Rotation axis.
        :type axis: :class:`numpy.ndarray`
        :param angle: Rotation amount in radians.
        :type angle: float
        :param db_id: Optional shared-instance identifier.
        :type db_id: str | None
        :returns: New angle instance.
        :rtype: :class:`Angle`
        """

        return cls(_quaternion.Quaternion.from_axis_angle(axis, angle), db_id=db_id)
