from typing import TYPE_CHECKING

import numpy as np
from .geometry import point as _point
from .geometry import angle as _angle

if TYPE_CHECKING:
    from . import canvas as _canvas
    from .objects import base3d as _base3d


# TODO: drag rotation is not working. the angles are not being calculated
#       correctly. This will need to be fixed.


class Arcball:
    def __init__(self, canvas: "_canvas.Canvas", selected: "_base3d.Base3D"):
        self.canvas = canvas
        self.selected = selected

        self.width, self.height = self._get_screen_rect()

        self.camera_pos = canvas.camera.position.copy()
        self.camera_eye = canvas.camera.eye.copy()

        matrix = selected.angle.as_matrix
        matrix = [row.tolist() + [0] for row in matrix]
        matrix.append([0.0, 0.0, 0.0, 1.0])
        self.rotation_matrix = np.array(matrix, dtype=np.float64)
        canvas.set_angle_overlay(*self._get_euler_angles())

        self.rotation_matrix = np.identity(4)
        self.start_vector = None
        self.is_dragging = False

    def __del__(self):
        self.canvas.set_angle_overlay(None, None, None)

    def _get_screen_rect(self):
        # min_x = 999999
        # max_x = -999999
        # min_y = 999999
        # max_y = -999999
        # min_z = 999999
        # max_z = -999999
        #
        # for rect in self.selected.rect:
        #     for p in rect:
        #         min_x = min(min_x, p.x)
        #         max_x = max(max_x, p.x)
        #         min_y = min(min_y, p.y)
        #         max_y = max(max_y, p.y)
        #         min_z = min(min_z, p.y)
        #         max_z = max(max_z, p.y)
        #
        # min_point = _point.Point(min_x, min_y, min_z)
        # max_point = _point.Point(max_x, max_y, max_z)
        #
        # min_screen_point = self.canvas.camera.ProjectPoint(min_point)
        # max_screen_point = self.canvas.camera.ProjectPoint(max_point)
        #
        # width = max_screen_point.x - min_screen_point.x
        # height = max_screen_point.y - min_screen_point.y

        width, height = self.canvas.GetParent().GetParent().GetSize()
        return width, height

    def map_to_sphere(self, mouse_pos: _point.Point) -> np.ndarray:
        """Map mouse screen coordinates to a virtual sphere."""
        x = mouse_pos.x
        y = mouse_pos.y

        nx = (2.0 * x - self.width) / self.width
        ny = (self.height - 2.0 * y) / self.height
        r = nx * nx + ny * ny
        if r > 1.0:
            length = np.sqrt(r)
            nx /= length
            ny /= length
            nz = 0.0
        else:
            nz = np.sqrt(1.0 - r)

        return np.array([nx, ny, nz])

    def __call__(self, mouse_pos: _point.Point):
        if self.start_vector is None:
            self.start_vector = self.map_to_sphere(mouse_pos)
            return

        if (
            self.camera_pos != self.canvas.camera.position or
            self.camera_eye != self.canvas.camera.eye
        ):
            self.camera_pos = self.canvas.camera.position.copy()
            self.camera_eye = self.canvas.camera.eye.copy()

            self.width, self.height = self._get_screen_rect()

            self.start_vector = self.map_to_sphere(mouse_pos)
            return

        self.rotate(mouse_pos)

    def rotate(self, mouse_pos: _point.Point):
        current_vector = self.map_to_sphere(mouse_pos)

        # Handle normal rotation outside of detent
        rotation_axis = np.cross(self.start_vector, current_vector)  # NOQA
        if np.linalg.norm(rotation_axis) > 1e-6:
            rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)

            # Calculate the delta rotation angle between the start and current vector
            dot_product = np.clip(np.dot(self.start_vector, current_vector), -1.0, 1.0)
            angle_change = np.arccos(dot_product)
            rotation_matrix = self._rotation_matrix_from_axis_angle(rotation_axis, angle_change)
            self.rotation_matrix = np.dot(rotation_matrix, self.rotation_matrix)

            self.canvas.set_angle_overlay(*self._get_euler_angles())

            r_angle = _angle.Angle.from_matrix(self.rotation_matrix[0:3, 0:-1])
            print('set_angle:', r_angle)
            angle = self.selected.angle
            print('old_angle:', angle)

            diff = r_angle - angle
            print('angle_diff:', diff)
            angle += diff
            print('new_angle:', angle)
            print()

        # Update starting vector for next rotation
        self.start_vector = current_vector

    @staticmethod
    def _rotation_matrix_from_axis_angle(axis, angle):
        """Generate a 4x4 rotation matrix given an axis and angle."""
        c, s = np.cos(angle), np.sin(angle)
        t = 1.0 - c
        x, y, z = axis
        return np.array(
            [
                [t * x * x + c, t * x * y - z * s, t * x * z + y * s, 0.0],
                [t * x * y + z * s, t * y * y + c, t * y * z - x * s, 0.0],
                [t * x * z - y * s, t * y * z + x * s, t * z * z + c, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )

    def _get_euler_angles(self):
        """Convert the rotation matrix to Euler angles in degrees."""
        rm = self.rotation_matrix
        sy = np.sqrt(rm[0, 0] ** 2 + rm[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            x = np.arctan2(rm[2, 1], rm[2, 2])  # Pitch
            y = np.arctan2(-rm[2, 0], sy)       # Yaw
            z = np.arctan2(rm[1, 0], rm[0, 0])  # Roll
        else:
            x = np.arctan2(-rm[1, 2], rm[1, 1])
            y = np.arctan2(-rm[2, 0], sy)
            z = 0

        return np.degrees([x, y, z])  # Convert to degrees
