# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
from OpenGL import GL
from OpenGL import GLU

import numpy as np

from ....geometry import point as _point
from ....geometry import angle as _angle
from ....geometry import line as _line


if TYPE_CHECKING:
    from . import Preview as _Preview

ZERO_POINT = _point.ZERO_POINT


class Camera:
    """Represent a camera in :mod:`harness_designer.database.global_db.model3d.preview.camera`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __doc__ = __doc__

    def __init__(self, canvas: "_Preview"):
        """Initialise the :class:`Camera` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: _Preview
        """
        self.canvas = canvas

        self._is_dirty = True
        self._projection = None
        self._modelview = None
        self._viewport = None
        self._clip = None
        self._up = None
        self._right = None
        self._forward = None

        self._up_norm = None
        self._right_norm = None
        self._forward_norm = None
        self._frustum_planes = None
        self._focal_target = None

        self._position = _point.Point(0.0, 0.0, 0.0)
        self._eye = _point.Point(0.0, 1.0, 75.0)

        self._angle = _angle.Angle.from_points(self._position, self._eye)
        self._angle_from_center = _angle.Angle.from_points(ZERO_POINT.copy(), self._eye)
        self._focal_distance = _line.Line(self._eye, self._position).length()
        self._distance_from_center = _line.Line(ZERO_POINT, self._eye).length()

        self._calculate_camera()

        self._position.bind(self._update_camera)
        self._eye.bind(self._update_camera)

    @property
    def position(self):
        """Return the position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._position

    @property
    def eye(self):
        """Return the eye.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._eye

    def Reset(self):
        """Execute the reset operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        with self._position and self._eye:
            self._position.x = 0.0
            self._position.y = 0.0
            self._position.z = 0.0

            self._eye.x = 0.0
            self._eye.y = 1.0
            self._eye.z = 75.0

        self._update_camera(None)

    def _update_camera(self, _=None):
        """Update the camera.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.canvas.update)

    @property
    def orthonormalized_axes(self):  # NOQA
        """Return the orthonormalized axes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        def normalize(v):
            """Execute the normalize operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param v: Value for ``v``.
            :type v: UNKNOWN
            :returns: Return value. UNKNOWN details.
            :rtype: UNKNOWN
            """
            v = np.array(v, dtype=float)
            n = np.linalg.norm(v)
            return v / (n if n != 0 else 1.0)

        f = normalize((self._position - self._eye).as_numpy)
        r = normalize(np.cross(f, self._up))  # NOQA
        u = np.cross(r, f)  # NOQA
        return f, r, u

    def Set(self):
        """Execute the set operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._calculate_camera()
        camera = self._eye.as_float + self._position.as_float + tuple(self._up.tolist())
        GLU.gluLookAt(*camera)
        self._update_views()

    def _calculate_camera(self):
        """Calculate the camera.

        UNKNOWN details are inferred from the callable name and signature.
        """
        eye = self._eye.as_numpy
        pos = self._position.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        forward = forward / fn

        gf = np.linalg.norm(forward)
        if gf < 1e-6:
            forward_ground = np.array([0.0, 0.0, -1.0], dtype=np.float32)
        else:
            forward_ground = forward / gf

        self._forward_norm = gf

        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        right = np.cross(world_up, forward_ground)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            right = right / rn

        self._right_norm = rn

        up = np.cross(forward_ground, right)  # NOQA

        un = np.linalg.norm(up)
        if un < 1e-6:
            up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        else:
            up = up / un

        self._up_norm = un

        self._up = up
        self._right = right
        self._forward = forward_ground

        self._focal_distance = _line.Line(self._eye, self._position).length()

    def _update_views(self):
        """Update the views.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if not self._is_dirty:
            return

        self._calculate_camera()
        self.canvas.makeCurrent()
        self._is_dirty = False
        self._viewport = np.ascontiguousarray(GL.glGetIntegerv(GL.GL_VIEWPORT))

        self._projection = np.ascontiguousarray(np.array(
            GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)).reshape((4, 4), order="F").T)

        self._modelview = np.ascontiguousarray(np.array(
            GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)).reshape((4, 4), order="F").T)
        self.canvas.doneCurrent()

    def Rotate(self, dx, dy):
        """Execute the rotate operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: UNKNOWN
        :param dy: Value for ``dy``.
        :type dy: UNKNOWN
        """
        self._is_dirty = True
        eye = self._rotate_about(dx, dy, self._eye, self._position)
        self._eye += eye - self._eye

    @staticmethod
    def _rotate_about(dx: int, dy: int,
                      p1: _point.Point, p2: _point.Point) -> np.ndarray:
        """Execute the rotate about operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: int
        :param dy: Value for ``dy``.
        :type dy: int
        :param p1: Value for ``p1``.
        :type p1: :class:`_point.Point`
        :param p2: Value for ``p2``.
        :type p2: :class:`_point.Point`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`np.ndarray`
        """

        p1 = p1.as_numpy
        p2 = p2.as_numpy

        max_pitch = 89.9

        offset = p1 - p2
        dist = np.linalg.norm(offset)

        if dist < 1e-6:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)

        up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        def _rodrigues(v, k, angle_rad):
            """Execute the rodrigues operation.

            UNKNOWN details are inferred from the callable name and signature.

            :param v: Value for ``v``.
            :type v: UNKNOWN
            :param k: Value for ``k``.
            :type k: UNKNOWN
            :param angle_rad: Value for ``angle_rad``.
            :type angle_rad: UNKNOWN
            :returns: Return value. UNKNOWN details.
            :rtype: UNKNOWN
            """
            k = k / np.linalg.norm(k)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)  # NOQA
            return ((v * cos_a) + (np.cross(k, v) * sin_a) +  # NOQA
                    (k * (np.dot(k, v)) * (1.0 - cos_a)))

        yaw_offset = _rodrigues(offset, up, math.radians(dx))
        yaw_offset_n = np.linalg.norm(yaw_offset)

        if yaw_offset_n < 1e-6:
            return np.array([0.0, 0.0, 0.0], dtype=np.float32)

        yaw_dir = yaw_offset / yaw_offset_n

        horiz_len = math.hypot(yaw_dir[0], yaw_dir[2])
        cur_pitch_deg = math.degrees(math.atan2(yaw_dir[1], horiz_len))

        desired_pitch = cur_pitch_deg + dy
        if desired_pitch > max_pitch or desired_pitch < -max_pitch:
            dy = 0.0

        if abs(dy) < 1e-6:
            final_offset = yaw_dir * dist
        else:
            right = np.cross(yaw_dir, up)  # NOQA
            rn = np.linalg.norm(right)

            if rn < 1e-6:
                final_offset = yaw_dir * dist
            else:
                right = right / rn
                rotated = _rodrigues(yaw_offset, right, math.radians(dy))

                rnorm = np.linalg.norm(rotated)

                if rnorm < 1e-6:
                    final_offset = yaw_dir * dist
                else:
                    final_offset = rotated * (dist / rnorm)

        new_point = p2 + final_offset

        return _point.Point(new_point[0], new_point[1], new_point[2])

    def PanTilt(self, dx, dy):
        """Execute the pan tilt operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: UNKNOWN
        :param dy: Value for ``dy``.
        :type dy: UNKNOWN
        """
        self._is_dirty = True
        position = self._rotate_about(dx, dy, self._position, self._eye)
        self._position += position - self._position

    def Zoom(self, delta, *_):
        """Execute the zoom operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        move = self._forward * float(delta)

        if delta > 0 and self._focal_distance <= 0.1:
            return
        elif delta < 0 and self._focal_distance >= 150.0:
            return

        self._is_dirty = True
        self._eye += move

    def Walk(self, dx, dy, speed):
        """Execute the walk operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: UNKNOWN
        :param dy: Value for ``dy``.
        :type dy: UNKNOWN
        :param speed: Value for ``speed``.
        :type speed: UNKNOWN
        """
        input_mag = math.sqrt((dx * dx) + (dy * dy))

        if input_mag == 0:
            return

        move_dir = self._right * float(dx) + self._forward * float(dy)

        mdn = np.linalg.norm(move_dir)

        if mdn < 1e-6:
            return

        move_dir = move_dir / mdn
        move = move_dir * (input_mag * speed)

        self._is_dirty = True
        with self._eye and self._position:
            self._eye += move
            self._position += move

    def TruckPedestal(self, dx, dy, speed):
        """Execute the truck pedestal operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param dx: Value for ``dx``.
        :type dx: UNKNOWN
        :param dy: Value for ``dy``.
        :type dy: UNKNOWN
        :param speed: Value for ``speed``.
        :type speed: UNKNOWN
        """
        input_mag = math.sqrt((dx * dx) + (dy * dy))

        if input_mag == 0:
            return

        move_dir = self._right * float(dx) + self._up * float(dy)

        mdn = np.linalg.norm(move_dir)
        if mdn < 1e-6:
            return

        move_dir = move_dir / mdn
        move = move_dir * (input_mag * speed)

        with self._eye:
            self._eye += move

        self._is_dirty = True
        self._position += move
