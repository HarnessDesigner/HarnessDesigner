from typing import TYPE_CHECKING, Union

from scipy.spatial.transform import Rotation as _Rotation
import numpy as np
from ..wrappers.decimal import Decimal as _decimal
from .constants import TEN_0

if TYPE_CHECKING:
    from . import point as _point


class Rotation:

    def __init__(self, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal):
        self._x_angle = x_angle
        self._y_angle = y_angle
        self._z_angle = z_angle

        self._R = _Rotation.from_euler('xyz', [x_angle, y_angle, z_angle], degrees=True)

    @property
    def x_angle(self) -> _decimal:
        return self._x_angle

    @x_angle.setter
    def x_angle(self, angle: _decimal):
        self._x_angle = angle

    @property
    def y_angle(self) -> _decimal:
        return self._y_angle

    @y_angle.setter
    def y_angle(self, angle: _decimal):
        self._y_angle = angle

    @property
    def z_angle(self) -> _decimal:
        return self._z_angle

    @z_angle.setter
    def z_angle(self, angle: _decimal):
        self._z_angle = angle

    def set_angles(self, x_angle: _decimal | None = None,
                   y_angle: _decimal | None = None,
                   z_angle: _decimal | None = None):

        if x_angle is not None:
            self._x_angle = x_angle

        if y_angle is not None:
            self._y_angle = y_angle

        if z_angle is not None:
            self._z_angle = z_angle

        self._R = _Rotation.from_euler(
            'xyz', [self._x_angle, self._y_angle, self._z_angle], degrees=True)

    def __call__(
        self, origin: "_point.Point", x: np.array, y: np.ndarray | None = None, z: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray] | np.ndarray:

        if y is not None and z is None:
            raise RuntimeError('sanity check')

        if y is None and z is None:
            origin = origin.as_numpy
            x -= origin
            x_ = self._R.apply(x.T).T
            x_ += origin
            return x_
        else:
            origin = origin.as_float

            local_points = np.vstack((x.flatten(), y.flatten(), z.flatten()))
            local_points = self._R.apply(local_points.T).T

            X = local_points[0].reshape(x.shape) + origin[0]
            Y = local_points[1].reshape(y.shape) + origin[1]
            Z = local_points[2].reshape(z.shape) + origin[2]
            return X, Y, Z

    def __rmatmul__(self, other: np.ndarray) -> np.ndarray:
        return self._R.apply(other.T).T


def get_angles(p1: "_point.Point", p2: "_point.Point") -> tuple[_decimal, _decimal, _decimal]:

    # to get the "roll" we need to have a directional vew we are looking from.
    # We always want that to be from a point looking down on the model along
    # the Z axis. So we create a 3rd point looking down with a z axis of 20 and
    # then add the input point that has the highest Z axis to it.

    p3 = p1 + p2
    p3 *= _decimal(0.5)

    if float(p1.z) > float(p2.z):
        p3.z = p1.z + TEN_0
    else:
        p3.z = p2.z + TEN_0

    # Convert to numpy arrays
    p1, p2, p3 = p1.as_numpy, p2.as_numpy, p3.as_numpy

    # Direction vector (main axis)
    forward = p2 - p1
    forward /= np.linalg.norm(forward)

    # Temporary "up" vector
    up_temp = p3 - p1
    up_temp /= np.linalg.norm(up_temp)

    # Right vector (perpendicular to forward and up_temp)
    right = np.cross(up_temp, forward)
    right /= np.linalg.norm(right)

    # True up vector (recomputed to ensure orthogonality)
    up = np.cross(forward, right)

    # Build rotation matrix
    matrix = np.array([right, up, forward]).T  # 3x3 rotation matrix

    # Extract Euler angles (XYZ order)
    pitch = np.arctan2(-matrix[2, 1], matrix[2, 2])
    yaw = np.arctan2(matrix[1, 0], matrix[0, 0])
    roll = np.arctan2(matrix[2, 0],
                      np.sqrt(matrix[2, 1] ** 2 + matrix[2, 2] ** 2))

    pitch, yaw, roll = np.degrees([pitch, yaw, roll])
    return _decimal(pitch) + _decimal(90.0), _decimal(roll), _decimal(yaw) - _decimal(90.0)
