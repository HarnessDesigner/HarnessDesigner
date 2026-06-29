# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Base classes and shared helpers for interactive editor handlers.
"""

import math
import numpy as np
from typing import TYPE_CHECKING

from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..geometry import point as _point


class HandlerBase:
    """
    Base class for the 3d handlers
    """

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        """
        Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        :param part_id: Identifier of the selected part definition.
        :type part_id: int
        """

        self.mainframe = mainframe
        self.part_id = part_id
        self.obj = None
        self.is_active = False
        self.camera = self.mainframe.editor3d.camera
        self.ptables = self.mainframe.project.ptables
        self._captured_position: "_point.Point" = None
        self._finalized = False

    @staticmethod
    def obb_face_direction(
        current_obb: np.ndarray,
        local_obb: np.ndarray,
        face_idx: int
    ):
        """
        Return the unit outward-normal direction for *face_idx* from the rotated OBB.

        Face membership is determined by sorting *local_obb* corners along each axis;
        face centroid is computed from *current_obb* (the rotated corners).
        """

        center = current_obb.mean(axis=0)
        axis = face_idx // 2
        sign = face_idx % 2
        sorted_i = np.argsort(local_obb[:, axis])
        corner_i = sorted_i[4:] if sign else sorted_i[:4]
        fc = current_obb[corner_i].mean(axis=0) - center

        n = float(np.linalg.norm(fc))
        if n < 1e-8:
            return None

        return fc / n

    @staticmethod
    def euler_from_matrix_continuous(rot_mat: np.ndarray, prev_euler_deg):
        """
        YXZ Euler (degrees) from *rot_mat*, wrapped to stay within ±180° of *prev_euler_deg*.
        """

        r = rot_mat
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, float(-r[1][2])))))
        yaw = math.degrees(math.atan2(float(r[0][2]), float(r[2][2])))
        roll = math.degrees(math.atan2(float(r[1][0]), float(r[1][1])))
        result = [pitch, yaw, roll]
        for i in range(3):
            while result[i] - prev_euler_deg[i] > 180.0:
                result[i] -= 360.0

            while result[i] - prev_euler_deg[i] < -180.0:
                result[i] += 360.0

        return result

    @classmethod
    def set_angle_from_housing(cls, acc_obj, housing_obj) -> bool:
        """
        Align *acc_db_obj*'s angle3d to match the housing's current world-space rotation.

        Uses the accessory's OBB forward/up face indices to derive a continuous Euler
        representation.  Returns True when the angle was written, False when data is
        missing (no model3d, no forward_up, degenerate geometry).
        """
        part = acc_obj.db_obj.part
        if part is None:
            return False

        model3d = part.model3d
        if model3d is None:
            return False

        local_obb = acc_obj.obj3d._vbo.local_obb  # NOQA
        if local_obb is None:
            return False

        fwd_face, up_face = model3d.forward_up
        if fwd_face == -1 or up_face == -1:
            return False

        q_h = housing_obj.db_obj.angle3d._q  # NOQA

        # Full world-space rotation: housing angle on top of the accessory's baked
        # model3d orientation (q_h ⊗ q_model3d), matching how pjt_housing tracks it.
        q_obj = acc_obj.obj3d.angle._q  # NOQA

        # = q_h ⊗ q_model3d
        q_obb = q_obj + q_h
        rotated = np.array([q_obb @ c for c in local_obb], dtype=np.float32)

        fwd = cls.obb_face_direction(rotated, local_obb, fwd_face)
        up = cls.obb_face_direction(rotated, local_obb, up_face)
        if fwd is None or up is None:
            return False

        right = np.cross(up, fwd)
        rn = float(np.linalg.norm(right))
        if rn < 1e-8:
            return False

        right /= rn
        up = np.cross(fwd, right)
        rot_mat = np.column_stack([right, up, fwd])

        obj_angle = acc_obj.obj3d.angle
        old_euler = obj_angle.as_euler_float
        new_euler = cls.euler_from_matrix_continuous(rot_mat, old_euler)

        with obj_angle:
            obj_angle.x = new_euler[0]
            obj_angle.y = new_euler[1]
            obj_angle.z = new_euler[2]
            obj_angle._matrix[:] = q_h.as_matrix  # NOQA

        obj_angle._q.w = q_h.w  # NOQA
        obj_angle._q.x = q_h.x  # NOQA
        obj_angle._q.y = q_h.y  # NOQA
        obj_angle._q.z = q_h.z  # NOQA

        obj_angle._process_callbacks()  # NOQA

        return True

    @classmethod
    def set_angle_from_cavity(cls, acc_obj, pjt_cavity) -> bool:
        """
        Align *acc_obj*'s angle3d to match *pjt_cavity*'s world-space rotation.

        Mirrors :meth:`set_angle_from_housing` but uses the cavity quaternion.
        Returns True when the angle was written, False when data is missing.
        """

        part = acc_obj.db_obj.part
        if part is None:
            return False

        model3d = part.model3d
        if model3d is None:
            return False

        local_obb = acc_obj.obj3d._vbo.local_obb  # NOQA
        if local_obb is None:
            return False

        fwd_face, up_face = model3d.forward_up
        if fwd_face == -1 or up_face == -1:
            return False

        q_c = pjt_cavity.angle3d._q  # NOQA
        q_obj = acc_obj.obj3d.angle._q  # NOQA
        q_obb = q_obj + q_c
        rotated = np.array([q_obb @ c for c in local_obb], dtype=np.float32)

        fwd = cls.obb_face_direction(rotated, local_obb, fwd_face)
        up = cls.obb_face_direction(rotated, local_obb, up_face)
        if fwd is None or up is None:
            return False

        right = np.cross(up, fwd)
        rn = float(np.linalg.norm(right))
        if rn < 1e-8:
            return False

        right /= rn
        up = np.cross(fwd, right)
        rot_mat = np.column_stack([right, up, fwd])

        obj_angle = acc_obj.obj3d.angle
        old_euler = obj_angle.as_euler_float
        new_euler = cls.euler_from_matrix_continuous(rot_mat, old_euler)

        with obj_angle:
            obj_angle.x = new_euler[0]
            obj_angle.y = new_euler[1]
            obj_angle.z = new_euler[2]
            obj_angle._matrix[:] = q_c.as_matrix  # NOQA

        obj_angle._q.w = q_c.w  # NOQA
        obj_angle._q.x = q_c.x  # NOQA
        obj_angle._q.y = q_c.y  # NOQA
        obj_angle._q.z = q_c.z  # NOQA
        obj_angle._process_callbacks()  # NOQA
        return True

    @staticmethod
    def reset_angle(acc_obj) -> None:
        """
        Reset *acc_db_obj*'s angle3d to the identity rotation (0, 0, 0).
        """

        obj_angle = acc_obj.obj3d.angle

        with obj_angle:
            obj_angle.x = 0.0
            obj_angle.y = 0.0
            obj_angle.z = 0.0
            obj_angle._matrix[:] = np.eye(3, dtype=np.float32)  # NOQA

        obj_angle._q.w = 1.0  # NOQA
        obj_angle._q.x = 0.0  # NOQA
        obj_angle._q.y = 0.0  # NOQA
        obj_angle._q.z = 0.0  # NOQA

        obj_angle._process_callbacks()  # NOQA

    def capture_position(self, position: "_point.Point") -> None:
        """
        Store the most recently captured cursor position for later use by the handler.

        :param position: 3D point used for placement or geometric calculations.
        :type position: "_point.Point"
        """

        self._captured_position = position

    def release_capture(self) -> None:
        """
        Handle release of the captured position and complete any deferred placement work.

        :raises NotImplementedError: Raised by handlers that require a subclass implementation.
        """

        raise NotImplementedError

    def ignore_next_input(self):
        """
        Removes a current mouse capture if any.
        """
        self._captured_position = None

    def hover(self, mouse_pos: _point.Point):
        """
        Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """

        pass

    def cancel(self):
        """
        Cancel the active operation and clean up any preview objects.
        """

        self.obj.delete()

    @property
    def is_finalized(self) -> bool:
        """
        Return whether the handler has completed all required work.

        :returns: :data:`True` when the handler has finished its work; otherwise :data:`False`.
        :rtype: bool
        """

        return self._finalized
