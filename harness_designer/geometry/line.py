from typing import Iterable as _Iterable
import math

import numpy as np

from . import point as _point
from . import angle as _angle

ZERO_5 = 0.5


class Line:

    def __array_ufunc__(self, func, method, inputs, instance, **kwargs):
        if func == np.matmul:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr @= instance
                p1, p2 = arr.tolist()

                self._p1.x = p1[0]
                self._p1.y = p1[1]
                self._p1.z = p1[1]

                self._p2.x = p2[0]
                self._p2.y = p2[1]
                self._p2.z = p2[1]

                return self
            else:
                return inputs @ self.as_numpy

        if func == np.add:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr += instance
                p1, p2 = arr.tolist()

                self._p1.x = p1[0]
                self._p1.y = p1[1]
                self._p1.z = p1[1]

                self._p2.x = p2[0]
                self._p2.y = p2[1]
                self._p2.z = p2[1]
                return self
            else:
                return inputs + self.as_numpy

        if func == np.subtract:
            if isinstance(instance, np.ndarray):
                arr = self.as_numpy
                arr -= instance
                p1, p2 = arr.tolist()

                self._p1.x = p1[0]
                self._p1.y = p1[1]
                self._p1.z = p1[1]

                self._p2.x = p2[0]
                self._p2.y = p2[1]
                self._p2.z = p2[1]
                return self
            else:
                return inputs + self.as_numpy

        raise RuntimeError

    def __init__(self, p1: _point.Point,
                 p2: _point.Point | None = None,
                 length: float | None = None,
                 angle: _angle.Angle | None = None):

        self._p1 = p1

        if p2 is None:
            if length is None or angle is None:
                raise ValueError('If an end point is not supplied then the "length", '
                                 '"x_angle", "y_angle" and "z_angle" parameters need to be supplied')

            p2 = _point.Point(0.0, 0.0, length)
            p2 @= angle
            p2 += p1

        self._p2 = p2

    @property
    def as_numpy(self) -> np.ndarray:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return np.array([p1, p2], dtype=np.dtypes.Float64DType)

    @property
    def as_float(self) -> tuple[list[float, float, float], list[float, float, float]]:
        p1 = self._p1.as_float
        p2 = self._p2.as_float

        return p1, p2

    def copy(self) -> "Line":
        p1 = self._p1.copy()
        p2 = self._p2.copy()
        return Line(p1, p2)

    @property
    def p1(self) -> _point.Point:
        return self._p1

    @property
    def p2(self) -> _point.Point:
        return self._p2

    def __len__(self) -> int:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z
        res = math.sqrt(x * x + y * y + z * z)
        return int(round(res))

    def length(self) -> float:
        x = self._p2.x - self._p1.x
        y = self._p2.y - self._p1.y
        z = self._p2.z - self._p1.z

        return math.sqrt(x * x + y * y + z * z)

    def get_angle(self, origin: _point.Point) -> _angle.Angle:
        temp_p1 = self._p1.copy()
        temp_p2 = self._p2.copy()

        if origin == self._p1:
            temp_p2 -= temp_p1
            temp_p1 = _point.ZERO_POINT
        elif origin == self._p2:
            temp_p1 -= temp_p2
            temp_p2 = _point.ZERO_POINT
        else:
            temp_p1 -= origin
            temp_p2 -= origin

        return _angle.Angle.from_points(temp_p1, temp_p2)

    def set_angle(self, angle: _angle.Angle, origin: _point.Point) -> None:
        if origin == self._p1:
            temp_p2 = self._p2.copy()
            temp_p2 -= origin
            temp_p2 @= angle
            temp_p2 += origin
            diff = temp_p2 - self._p2
            self._p2 += diff

        elif origin == self._p2:
            temp_p1 = self._p1.copy()
            temp_p1 -= origin
            temp_p1 @= angle
            temp_p1 += origin
            diff = temp_p1 - self._p1
            self._p1 += diff
        else:
            temp_p1 = self._p1.copy()
            temp_p2 = self._p2.copy()

            temp_p1 -= origin
            temp_p2 -= origin

            temp_p1 @= angle
            temp_p2 @= angle

            temp_p1 += origin
            temp_p2 += origin

            diff_p1 = temp_p1 - self._p1
            diff_p2 = temp_p2 - self._p2

            self._p1 += diff_p1
            self._p2 += diff_p2

    def point_from_start(self, distance: float) -> _point.Point:
        """
        Calculate point on the line at a specific distance from the start point.

        :param distance: Distance from start point to the calculated point.
        :type distance: `decimal.Decimal`

        :returns: The coordinates of the calculated point.
        :rtype: `_point.Point`

        :raises ValueError: If the specified distance places the point beyond p2.
        """

        # Convert points to numpy arrays
        p1 = self._p1.as_numpy
        p2 = self._p2.as_numpy

        # Compute the vector from p1 to p2
        vector = p2 - p1

        # Compute the total distance between p1 and p2
        total_distance = np.linalg.norm(vector)

        # Check if the specified distance is valid
        if distance > total_distance:
            raise ValueError("calculated point is not on the line")

        # Normalize the vector to get the unit direction vector
        unit_vector = vector / total_distance

        # Calculate the third point
        p3 = p1 + distance * unit_vector

        return _point.Point(p3[0], p3[1], p3[2])

    def __isub__(self, other: _point.Point | np.ndarray) -> "Line":
        self._p1 -= other
        self._p2 -= other

        return self

    def __sub__(self, other: _point.Point | np.ndarray) -> "Line":
        p1 = self._p1 - other
        p2 = self._p2 - other

        return Line(p1, p2)

    def __iadd__(self, other: _point.Point | np.ndarray) -> "Line":
        self._p1 += other
        self._p2 += other

        return self

    def __add__(self, other: _point.Point | np.ndarray) -> "Line":
        p1 = self._p1 + other
        p2 = self._p2 + other

        return Line(p1, p2)

    def __imul__(self, other: _point.Point | np.ndarray) -> "Line":
        self._p1 *= other
        self._p2 *= other

        return self

    def __mul__(self, other: _point.Point | np.ndarray) -> "Line":
        p1 = self._p1 * other
        p2 = self._p2 * other

        return Line(p1, p2)

    def __imatmul__(self, other: _angle.Angle | np.ndarray) -> "Line":
        self._p1 @= other
        self._p2 @= other

        return self

    def __matmul__(self, other: _angle.Angle | np.ndarray) -> "Line":
        p1 = self._p1 @ other
        p2 = self._p2 @ other

        return Line(p1, p2)

    @property
    def center(self) -> _point.Point:
        x = (self._p1.x + self._p2.x) * ZERO_5
        y = (self._p1.y + self._p2.y) * ZERO_5
        z = (self._p1.z + self._p2.z) * ZERO_5
        return _point.Point(x, y, z)

    def __iter__(self) -> _Iterable[_point.Point]:
        return iter([self._p1, self._p2])

    def get_rotated_line(self, angle: _angle.Angle, pivot: _point.Point) -> "Line":

        if pivot is None:
            pivot = self.center

        p1 = self._p1.copy()
        p2 = self._p2.copy()

        p1 -= pivot
        p2 -= pivot
        p1 @= angle
        p2 @= angle
        p1 += pivot
        p2 += pivot

        return Line(p1, p2)

    def get_parallel_line(self, offset: float, offset_dir: _point.Point | None = None,
                          plane: str = 'x') -> "Line":
        """
        Calculate a parallel line in 3D space by specifying
        either a direction vector or a plane.

        :param offset: The perpendicular distance between the
                       original and parallel lines.
        :type offset: `decimal.Decimal`

        :param offset_dir: A vector indicating the direction of the offset.
        :type offset_dir: Optional, `_point.Point`, `None`

        :param plane: The plane ('x', 'y', or 'z') for normal
                      direction of the offset.
        :type plane: Optional, `str`, `None`

        :returns: Two points defining the parallel line (np.array, np.array).
        :rtype: `Line`

        :raises ValueError: If neither `offset_dir` nor `plane` is provided,
                           or if `plane` is invalid.
        """
        if self._p1.is2d and self._p2.is2d:
            offset_dir = None
            plane = 'x'
        else:
            if offset_dir is None and plane is None:
                raise ValueError("offset_dir or plane MUST be supplied")

        # Convert inputs to NumPy arrays
        p1 = self._p1.as_numpy
        p2 = self._p2.as_numpy

        # Determine offset direction
        if offset_dir is not None:
            offset_dir = offset_dir.as_numpy

            if np.linalg.norm(offset_dir) == 0:
                if plane is None:
                    raise ValueError("Offset direction vector must be non-zero.")

                offset_dir = None
            else:
                # Normalize the offset direction vector
                offset_dir = offset_dir / np.linalg.norm(offset_dir)

        if offset_dir is None:
            # Set the offset direction based on the specified plane
            if plane == 'x':
                offset_dir = np.array([1, 0, 0], dtype=float)
            elif plane == 'y':
                offset_dir = np.array([0, 1, 0], dtype=float)
            elif plane == 'z':
                offset_dir = np.array([0, 0, 1], dtype=float)
            else:
                raise ValueError(f"Invalid plane specified: {plane}. "
                                 f"Valid options are 'x', 'y', or 'z'.")

        # Scale the offset direction by the given distance
        offset_vector = offset_dir * float(offset)

        # Compute the points on the parallel line
        p1 = p1 + offset_vector
        p2 = p2 + offset_vector

        p1 = _point.Point(p1[0], p1[1], p1[2])
        p2 = _point.Point(p2[0], p2[1], p2[2])

        return Line(p1, p2)
