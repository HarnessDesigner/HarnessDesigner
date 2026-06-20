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


def _obb_face_direction(current_obb: np.ndarray, local_obb: np.ndarray, face_idx: int):
    """Return the unit outward-normal direction for *face_idx* from the rotated OBB.

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


def _euler_from_matrix_continuous(rot_mat: np.ndarray, prev_euler_deg):
    """YXZ Euler (degrees) from *rot_mat*, wrapped to stay within ±180° of *prev_euler_deg*."""
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


def set_angle_from_housing(acc_db_obj, housing_db_obj) -> bool:
    """Align *acc_db_obj*'s angle3d to match the housing's current world-space rotation.

    Uses the accessory's OBB forward/up face indices to derive a continuous Euler
    representation.  Returns True when the angle was written, False when data is
    missing (no model3d, no forward_up, degenerate geometry).
    """
    part = acc_db_obj.part
    if part is None:
        return False
    model3d = part.model3d
    if model3d is None:
        return False
    local_obb = model3d.obb
    if local_obb is None:
        return False
    fwd_face, up_face = model3d.forward_up
    if fwd_face == -1 or up_face == -1:
        return False

    q_h = housing_db_obj.angle3d._q
    # Full world-space rotation: housing angle on top of the accessory's baked
    # model3d orientation (q_h ⊗ q_model3d), matching how pjt_housing tracks it.
    q_model3d = model3d.angle3d._q
    q_obb = q_model3d + q_h  # = q_h ⊗ q_model3d
    rotated = np.array([q_obb @ c for c in local_obb], dtype=np.float32)

    fwd = _obb_face_direction(rotated, local_obb, fwd_face)
    up = _obb_face_direction(rotated, local_obb, up_face)
    if fwd is None or up is None:
        return False

    right = np.cross(up, fwd)
    rn = float(np.linalg.norm(right))
    if rn < 1e-8:
        return False
    right /= rn
    up = np.cross(fwd, right)
    rot_mat = np.column_stack([right, up, fwd])

    obj_angle = acc_db_obj.angle3d
    old_euler = obj_angle.as_euler_float
    new_euler = _euler_from_matrix_continuous(rot_mat, old_euler)

    obj_angle._q.w = q_h.w
    obj_angle._q.x = q_h.x
    obj_angle._q.y = q_h.y
    obj_angle._q.z = q_h.z
    euler_cache = obj_angle._Angle__euler_angles
    if euler_cache is not None:
        euler_cache[0] = new_euler[0]
        euler_cache[1] = new_euler[1]
        euler_cache[2] = new_euler[2]
    obj_angle._matrix[:] = q_h.as_matrix
    obj_angle._process_callbacks()
    return True


def reset_angle(acc_db_obj) -> None:
    """Reset *acc_db_obj*'s angle3d to the identity rotation (0, 0, 0)."""
    obj_angle = acc_db_obj.angle3d
    obj_angle._q.w = 1.0
    obj_angle._q.x = 0.0
    obj_angle._q.y = 0.0
    obj_angle._q.z = 0.0
    euler_cache = obj_angle._Angle__euler_angles
    if euler_cache is not None:
        euler_cache[0] = 0.0
        euler_cache[1] = 0.0
        euler_cache[2] = 0.0
    obj_angle._matrix[:] = np.eye(3, dtype=np.float32)
    obj_angle._process_callbacks()


class HandlerBase:
    """
    Base class for the 3d handlers
    """

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        """Initialize the object and capture the state required for later interaction.

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

    def capture_position(self, position: "_point.Point") -> None:
        """Store the most recently captured cursor position for later use by the handler.

        :param position: 3D point used for placement or geometric calculations.
        :type position: "_point.Point"
        """
        self._captured_position = position

    def release_capture(self) -> None:
        """Handle release of the captured position and complete any deferred placement work.

        :raises NotImplementedError: Raised by handlers that require a subclass implementation.
        """
        raise NotImplementedError

    def ignore_next_input(self):
        """
        Removes a current mouse capture if any.
        """
        self._captured_position = None

    def hover(self, mouse_pos: _point.Point):
        """Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        pass

    def cancel(self):
        """Cancel the active operation and clean up any preview objects.
        """
        self.obj.delete()

    @property
    def is_finalized(self) -> bool:
        """Return whether the handler has completed all required work.

        :returns: :data:`True` when the handler has finished its work; otherwise :data:`False`.
        :rtype: bool
        """
        return self._finalized
