from typing import TYPE_CHECKING

import math
import numpy as np


if TYPE_CHECKING:
    from . import canvas as _canvas


class FreeRotate:

    def __init__(self, canvas: "_canvas.Canvas", selected, x: int, y: int):
        self.selected = selected
        self.canvas = canvas
        self.v0 = self.map_to_sphere(x, y)

    def __call__(self, x: int, y: int):
        v1 = self.map_to_sphere(x, y)

        # small-rotation quaternion from v0 -> v1
        q = self.quat_from_vectors(self.v0, v1)

        # accumulate orientation: q * orient
        quat = np.array(q, dtype=np.float64)
        self.selected.rotate(quat)
        self.v0 = v1

    @staticmethod
    def normalize(v):
        v = np.array(v, dtype=float)
        n = np.linalg.norm(v)
        return v / (n if n != 0 else 1.0)

    @classmethod
    def camera_axes(cls, eye, position, up):
        # Returns forward, right, up (all unit) with forward pointing from eye -> center
        f = cls.normalize((position - eye).as_numpy)
        r = cls.normalize(np.cross(f, up))  # camera right  # NOQA
        u = np.cross(r, f)  # camera up re-orthonormalized  # NOQA
        return f, r, u

    @classmethod
    def axis_angle_to_matrix(cls, axis, angle):
        axis = cls.normalize(axis)
        x, y, z = axis
        c = np.cos(angle)
        s = np.sin(angle)
        t = 1 - c
        # Rodrigues rotation matrix
        return np.array([
            [t*x*x + c,   t*x*y - s*z, t*x*z + s*y],
            [t*x*y + s*z, t*y*y + c,   t*y*z - s*x],
            [t*x*z - s*y, t*y*z + s*x, t*z*z + c  ]
        ], dtype=float)

    def map_to_sphere(self, mx: int, my: int) -> np.ndarray:
        sens = 0.007  # radians per pixel, tune this
        f, right, cam_up = self.camera_axes(self.canvas.camera.eye, self.canvas.camera.position, self.canvas.camera.up)

        # Build incremental rotations in camera space:
        # horizontal mouse -> rotate around camera up (yaw)
        # vertical mouse   -> rotate around camera right (pitch)
        # Note: sign of angles may need flipping depending on your desired handedness / mouse convention.
        R_yaw = self.axis_angle_to_matrix(cam_up, mx * sens)
        R_pitch = self.axis_angle_to_matrix(right, -my * sens)

        # Compose: apply pitch then yaw (order matters). Pick order that feels right.
        R_delta = R_yaw @ R_pitch

        # Update model rotation: apply R_delta in world coords about object center
        # If you store model_rotation as 3x3 R_model, update: R_model = R_delta @ R_model
        w, h = self.canvas.GetClientSize()

        if w <= 0 or h <= 0:
            return np.array([0.0, 0.0, 0.0], dtype=np.float64)

        x = (2.0 * mx - w) / w
        y = (h - 2.0 * my) / h  # flip Y

        length2 = x * x + y * y

        if length2 > 1.0:
            inv_len = 1.0 / math.sqrt(length2)
            return np.array([x * inv_len, y * inv_len, 0.0], dtype=np.float64)

        z = math.sqrt(max(0.0, 1.0 - length2))

        point = np.array([x, y, z], dtype=np.float64)
        point @= R_delta
        return point

    @staticmethod
    def quat_normalize(q):
        q = np.array(q, dtype=np.float64)

        n = math.sqrt((q * q).sum())

        if n == 0.0:
            return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)

        return (q / n).astype(np.float64)

    def quat_from_vectors(self, vfrom, vto):
        # vfrom, vto: length-3 iterables (single vector)
        f = np.array(vfrom, dtype=np.float64)
        t = np.array(vto, dtype=np.float64)

        f = f / (np.linalg.norm(f) + 1e-20)
        t = t / (np.linalg.norm(t) + 1e-20)

        d = np.dot(f, t)
        if d > 0.999999:
            return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)

        if d < -0.999999:
            # pick orthogonal axis
            axis = np.cross(np.array([1.0, 0.0, 0.0]), f)  # NOQA

            if np.linalg.norm(axis) < 1e-6:
                axis = np.cross(np.array([0.0, 1.0, 0.0]), f)  # NOQA

            axis = axis / np.linalg.norm(axis)
            quat = np.concatenate(
                ([math.cos(math.pi / 2.0)], axis * math.sin(math.pi / 2.0)))

            quat = np.array([quat[1], quat[2], quat[3], quat[0]],
                            dtype=np.float64)

            return self.quat_normalize(quat)

        axis = np.cross(f, t)  # NOQA
        w = math.sqrt((1.0 + d) * 2.0) * 0.5
        invs = 1.0 / (2.0 * w)

        q = np.array([axis[0] * invs, axis[1] * invs, axis[2] * invs, w],
                     dtype=np.float64)

        return self.quat_normalize(q)
