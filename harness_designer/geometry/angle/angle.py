import math
from typing import Self, Callable, Iterable, Union
import weakref
import numpy as np

from . import quaternion as _quaternion
from .. import point as _point


ONE = 1.0
TWO = 2.0


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

    def __call__(cls, q: _quaternion.Quaternion | None = None,
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | str | None = None):

        if db_id is not None:
            if db_id in cls._instances:
                instance = cls._instances[db_id]
            else:
                instance = super().__call__(q, euler_angles, db_id)
                cls._instances[db_id] = weakref.ref(instance, cls._remove_instance)
        else:
            instance = super().__call__(q, euler_angles, db_id)

        return instance


class Angle(metaclass=AngleMeta):

    def __array_ufunc__(self, func, method, inputs, instance, out=None, **kwargs):  # NOQA
        if func == np.matmul:

            if out is None:
                return inputs @ self._q
            else:
                inputs @= self._q
                return inputs

        if func == np.add:
            if isinstance(instance, np.ndarray):
                if instance.shape == (4,):
                    quat = _quaternion.Quaternion(*[float(item) for item in instance])
                elif instance.shape == (3,):
                    quat = _quaternion.Quaternion.from_euler(*[float(item) for item in instance])
                else:
                    raise ValueError('Incorrect array shape')

                self._q += quat
                self._process_update()

                return self
            else:
                if inputs.shape == (3,):
                    # arr = np.array(self.as_float, dtype=np.float64)
                    point = self.from_euler(*[float(item) for item in inputs])
                    point += self
                    inputs[0] = point.x
                    inputs[1] = point.y
                    inputs[2] = point.z
                    return inputs

                elif inputs.shape == (4,):
                    q = _quaternion.Quaternion(*[float(item) for item in inputs])
                    q += self._q
                    q = q.as_numpy
                    inputs[0] = q[0]
                    inputs[1] = q[1]
                    inputs[2] = q[2]
                    inputs[3] = q[3]
                    return inputs

                raise ValueError('array shape is not correct')

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                if instance.shape == (4,):
                    quat = _quaternion.Quaternion(*[float(item) for item in instance])
                elif instance.shape == (3,):
                    quat = _quaternion.Quaternion.from_euler(*[float(item) for item in instance])
                else:
                    raise ValueError('Incorrect array shape')

                self._q -= quat
                self._process_update()

                return self
            else:
                if inputs.shape == (3,):
                    point = self.from_euler(*[float(item) for item in inputs])
                    point -= self
                    inputs[0] = point.x
                    inputs[1] = point.y
                    inputs[2] = point.z
                    return inputs

                elif inputs.shape == (4,):
                    q = _quaternion.Quaternion(*[float(item) for item in inputs])
                    q -= self._q
                    q = q.as_numpy
                    inputs[0] = q[0]
                    inputs[1] = q[1]
                    inputs[2] = q[2]
                    inputs[3] = q[3]
                    return inputs

                raise ValueError('array shape is not correct')

        raise RuntimeError

    def __init__(self, q: _quaternion.Quaternion | None = None, 
                 euler_angles: list[float, float, float] | None = None,
                 db_id: int | str | None = None):

        self.db_id = db_id

        if q is None:
            q = _quaternion.Quaternion(1.0, 0.0, 0.0, 0.0)

        self._q = q

        if euler_angles is None:
            self.__euler_angles = None
        else:
            self.__euler_angles = np.array(euler_angles, dtype=np.float64)

        self.__callbacks = []
        self._ref_count = 0

        self._matrix = self._q.as_matrix

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def __remove_callback(self, ref):
        try:
            self.__callbacks.remove(ref)
        except:  # NOQA
            pass

    def bind(self, cb: Callable[["Angle"], None]) -> bool:
        # We don't explicitly check to see if a callback is already registered.
        # What we care about is if a callback is called only one time and that
        # check is done when the callbacks are being executed. If there happens
        # to be a duplicate, the duplicate is then removed at that point in time.
        ref = weakref.WeakMethod(cb, self.__remove_callback)
        self.__callbacks.append(ref)
        return True

    def unbind(self, cb: Callable[["Angle"], None]) -> None:
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
        q = -self._q
        return Angle(q)
    
    def __neg__(self) -> "Angle":
        q = -self._q
        return Angle(q)

    @property
    def x(self) -> float:
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles[0]

    @x.setter
    def x(self, value: float):
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[0] = value
        
        q = _quaternion.Quaternion.from_euler(*self.__euler_angles)
        self.__update_quat(q)

        self._process_update()

    def __update_quat(self, q):
        self._q.w = q.w
        self._q.x = q.x
        self._q.y = q.y
        self._q.z = q.z
        self.__update_matrix()

    @property
    def y(self) -> float:
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles[1]

    @y.setter
    def y(self, value: float):
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[1] = value
        q = _quaternion.Quaternion.from_euler(*self.__euler_angles)

        self.__update_quat(q)
        self._process_update()

    @property
    def z(self) -> float:
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return math.nan

        return self.__euler_angles[2]

    @z.setter
    def z(self, value: float):
        if self.__euler_angles is None:
            # self.__euler_angles = self._q.as_euler
            return

        self.__euler_angles[2] = value

        q = _quaternion.Quaternion.from_euler(*self.__euler_angles)

        self.__update_quat(q)
        self._process_update()

    def copy(self) -> "Angle":
        return Angle.from_quat(self._q)

    @staticmethod
    def __get_quat_from_other(other: Union["Angle", np.ndarray | _quaternion.Quaternion]) -> _quaternion.Quaternion:
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
        matrix = self._q.as_matrix

        for i in range(3):
            for j in range(3):
                self._matrix[i][j] = matrix[i][j]

    def __iadd__(self, other: Union["Angle", np.ndarray]) -> Self:
        self._q += self.__get_quat_from_other(other)
        self.__update_matrix()
        self._process_update()
        return self

    def __add__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        q = self._q + self.__get_quat_from_other(other)

        return self.from_quat(q)

    def __isub__(self, other: Union["Angle", np.ndarray]) -> Self:
        self._q -= self.__get_quat_from_other(other)
        self.__update_matrix()
        self._process_update()
        return self

    def __sub__(self, other: Union["Angle", np.ndarray]) -> "Angle":
        q = self._q - self.__get_quat_from_other(other)
        return self.from_quat(q)

    def __rmatmul__(self, other: Union[np.ndarray, _point.Point]) -> np.ndarray | _point.Point:
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
        arr = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
        return not all(np.isclose(self.as_quat_numpy, arr))

    def __eq__(self, other: "Angle") -> bool:
        other = other.as_quat_numpy
        return all(np.isclose(other, self.as_quat_numpy))

    def __ne__(self, other: "Angle") -> bool:
        return not self.__eq__(other)

    @property
    def as_euler_numpy(self) -> np.ndarray:
        return self.__euler_angles

    @property
    def as_euler_float(self) -> list[float, float, float]:
        return self.__euler_angles.tolist()

    @property
    def as_quat_numpy(self) -> np.ndarray:
        return self._q.as_numpy

    @property
    def as_quat_float(self) -> list[float, float, float]:
        return self._q.as_numpy.tolist()

    @property
    def as_euler_int(self) -> tuple[int, int, int]:
        x, y, z = self.as_euler_float
        return int(x), int(y), int(z)

    @property
    def as_matrix_float(
        self
    ) -> list[list[float, float, float], list[float, float, float], list[float, float, float]]:

        return self._matrix.tolist()

    @property
    def as_matrix_numpy(self) -> np.ndarray:
        return self._matrix

    def __iter__(self) -> Iterable[float]:
        x, y, z = self._q.as_euler

        return iter([x, y, z])

    def __str__(self) -> str:
        x, y, z = self._q.as_euler

        return f'X: {x}, Y: {y}, Z: {z}'

    @classmethod
    def from_euler(cls, x: float, y: float, z: float, db_id: str | None = None) -> "Angle":
        q = _quaternion.Quaternion.from_euler(x, y, z)  # NOQA
        ret = cls(q, [x, y, z], db_id)
        return ret

    @classmethod
    def from_quat(cls, q: list[float, float, float, float] | np.ndarray | _quaternion.Quaternion,
                  euler_angles: list[float, float, float] | None = None, db_id: str | None = None) -> "Angle":

        if not isinstance(q, _quaternion.Quaternion):
            q = _quaternion.Quaternion(*[float(item) for item in q])  # NOQA

        return cls(q, euler_angles, db_id)

    @classmethod
    def from_matrix(cls, matrix: np.ndarray, db_id: str | None = None) -> "Angle":
        """
        Convert a 3x3 rotation matrix to a unit quaternion (w, x, y, z).
        """

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

        return cls.from_matrix(rot, db_id)

    @classmethod
    def from_axis_angle(cls, axis: np.ndarray, angle: float, db_id: str | None = None):
        return cls(_quaternion.Quaternion.from_axis_angle(axis, angle), db_id=db_id)
