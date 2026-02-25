
from typing import TYPE_CHECKING

import wx
import math
from OpenGL import GL
from OpenGL import GLU

import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line


if TYPE_CHECKING:
    from . import Preview as _Preview

ZERO_POINT = _point.ZERO_POINT


class Camera:
    __doc__ = __doc__

    def __init__(self, canvas: "_Preview"):
        self.canvas = canvas
        self._context = canvas.context

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
        return self._position

    @property
    def eye(self):
        return self._eye

    def Reset(self):
        with self._position and self._eye:
            self._position.x = 0.0
            self._position.y = 0.0
            self._position.z = 0.0

            self._eye.x = 0.0
            self._eye.y = 1.0
            self._eye.z = 75.0

        self._update_camera(None)

    def _update_camera(self, _=None):
        if self._context.is_locked:
            self._is_dirty = True
        else:
            wx.CallAfter(self.canvas.Refresh, False)

    @property
    def orthonormalized_axes(self):  # NOQA
        def normalize(v):
            v = np.array(v, dtype=float)
            n = np.linalg.norm(v)
            return v / (n if n != 0 else 1.0)

        # Returns forward, right, up (all unit) with forward pointing from eye -> center
        f = normalize((self._position - self._eye).as_numpy)
        r = normalize(np.cross(f, self._up))  # camera right  # NOQA
        u = np.cross(r, f)  # camera up re-orthonormalized  # NOQA
        return f, r, u

    def Set(self):
        self._calculate_camera()
        camera = self._eye.as_float + self._position.as_float + tuple(self._up.tolist())
        GLU.gluLookAt(*camera)
        self._update_views()

    def _calculate_camera(self):
        eye = self._eye.as_numpy
        pos = self._position.as_numpy

        forward = pos - eye

        fn = np.linalg.norm(forward)
        if fn < 1e-6:
            return

        forward = forward / fn

        gf = np.linalg.norm(forward)
        if gf < 1e-6:
            forward_ground = np.array([0.0, 0.0, -1.0], dtype=np.float64)
        else:
            forward_ground = forward / gf

        self._forward_norm = gf

        world_up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        right = np.cross(world_up, forward_ground)  # NOQA

        rn = np.linalg.norm(right)
        if rn < 1e-6:
            right = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        else:
            right = right / rn

        self._right_norm = rn

        up = np.cross(forward_ground, right)  # NOQA

        un = np.linalg.norm(up)
        if un < 1e-6:
            up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        else:
            up = up / un

        self._up_norm = un

        self._up = up
        self._right = right
        self._forward = forward_ground

        self._focal_distance = _line.Line(self._eye, self._position).length()

    def _update_views(self):
        if not self._is_dirty:
            return

        self._calculate_camera()
        with self._context:
            self._is_dirty = False
            self._viewport = np.ascontiguousarray(GL.glGetIntegerv(GL.GL_VIEWPORT))

            self._projection = np.ascontiguousarray(np.array(
                GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)).reshape((4, 4), order="F").T)

            self._modelview = np.ascontiguousarray(np.array(
                GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)).reshape((4, 4), order="F").T)

    def Rotate(self, dx, dy):
        self._is_dirty = True
        eye = self._rotate_about(dx, dy, self._eye, self._position)
        self._eye += eye - self._eye

    @staticmethod
    def _rotate_about(dx: int, dy: int,
                      p1: _point.Point, p2: _point.Point) -> np.ndarray:

        p1 = p1.as_numpy
        p2 = p2.as_numpy

        max_pitch = 89.9

        offset = p1 - p2
        dist = np.linalg.norm(offset)

        if dist < 1e-6:
            return np.array([0.0, 0.0, 0.0], dtype=np.float64)

        up = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        def _rodrigues(v, k, angle_rad):
            k = k / np.linalg.norm(k)

            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)  # NOQA

            return ((v * cos_a) + (np.cross(k, v) * sin_a) +  # NOQA
                    (k * (np.dot(k, v)) * (1.0 - cos_a)))

        yaw_offset = _rodrigues(offset, up, math.radians(dx))
        yaw_offset_n = np.linalg.norm(yaw_offset)

        if yaw_offset_n < 1e-6:
            return np.array([0.0, 0.0, 0.0], dtype=np.float64)

        yaw_dir = yaw_offset / yaw_offset_n

        horiz_len = math.hypot(yaw_dir[0], yaw_dir[2])

        cur_pitch_deg = math.degrees(math.atan2(yaw_dir[1], horiz_len))

        desired_pitch = cur_pitch_deg + dy
        if desired_pitch > max_pitch or desired_pitch < -max_pitch:
            # block pitch movement entirely (yaw still applies)
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
                    # explicitly restore original distance to avoid shrink/grow
                    final_offset = rotated * (dist / rnorm)

        new_point = p2 + final_offset

        return _point.Point(new_point[0], new_point[1], new_point[2])

    def PanTilt(self, dx, dy):
        self._is_dirty = True
        position = self._rotate_about(dx, dy, self._position, self._eye)
        self._position += position - self._position

    def Zoom(self, delta, *_):
        move = self._forward * float(delta)

        # If moving would invert eye and pos, prevent crossing pos
        if delta > 0 and self._focal_distance <= 0.1:
            return

        elif delta < 0 and self._focal_distance >= 150.0:
            return

        self._is_dirty = True
        self._eye += move

    def Walk(self, dx, dy, speed):
        # Build desired move from input
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
        # Build desired move from input
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
