from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ...shapes import arrow as _arrow
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import color as _color

if TYPE_CHECKING:
    from ... import ui as _ui


ARROW_LENGTH_SCALE = 1.5
OFFSET_SCALE = 0.6


class MoveArrows:

    def __init__(self, position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        """
        Create movement arrows for visual feedback during dragging.

        Args:
            position: The Point instance from the object being dragged (to bind callback)
            axis: String - 'x', 'y', or 'z' indicating which axis is locked
            mainframe: MainFrame reference
            aabb: The object's axis-aligned bounding box for sizing calculations
        """
        vbo = _arrow.create_vbo()

        cyan = _color.Color(0, 255, 255, 255)
        self._material = _materials.Generic(cyan)

        width = aabb[1][0] - aabb[0][0]
        height = aabb[1][1] - aabb[0][1]
        depth = aabb[1][2] - aabb[0][2]
        max_dim = max(width, height, depth)

        arrow_length = max_dim * ARROW_LENGTH_SCALE

        arrow_position = _point.Point(0, 0, 0)

        if axis == 'x':
            offset = _point.Point(0, height / 2 + max_dim * OFFSET_SCALE, 0)
            arrow_angle = _angle.Angle.from_euler(0, 90, 0)
            flip_angle = _angle.Angle.from_euler(0, 180, 0)
            scale = _point.Point(arrow_length, arrow_length, arrow_length)

        elif axis == 'z':
            offset = _point.Point(0, height / 2 + max_dim * OFFSET_SCALE, 0)
            arrow_angle = _angle.Angle.from_euler(0, 0, 0)
            flip_angle = _angle.Angle.from_euler(180, 0, 0)
            scale = _point.Point(arrow_length, arrow_length, arrow_length)

        else:  # axis == 'y'
            offset = _point.Point(width / 2 + max_dim * OFFSET_SCALE, 0, 0)
            arrow_angle = _angle.Angle.from_euler(-90, 0, 0)
            flip_angle = _angle.Angle.from_euler(180, 0, 0)
            scale = _point.Point(arrow_length, arrow_length, arrow_length)

        self._offset = offset
        self._flip_angle = arrow_angle + flip_angle

        arrow_position.x = position.x + offset.x
        arrow_position.y = position.y + offset.y
        arrow_position.z = position.z + offset.z

        self._vbo = vbo
        self._position = arrow_position
        self._angle = arrow_angle
        self._scale = scale
        self._is_visible = True

        position.bind(self._on_position_changed)

    def _on_position_changed(self, new_position: _point.Point):
        """Update arrow position when the dragged object moves."""
        self._position.x = new_position.x + self._offset.x
        self._position.y = new_position.y + self._offset.y
        self._position.z = new_position.z + self._offset.z

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    def render(self, shader_program):
        """Render bidirectional arrow (VBO rendered twice with 180° flip)."""
        if not self.is_visible:
            return

        self._material.set(shader_program)

        pos_loc = GL.glGetUniformLocation(shader_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(shader_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(shader_program, "objectScale")

        objectHasReflectionLoc = GL.glGetUniformLocation(shader_program, "objectHasReflection")
        GL.glUniform1i(objectHasReflectionLoc, 1)

        GL.glUniform3f(scale_loc, *self._scale.as_float)
        GL.glUniform3f(pos_loc, *self._position.as_float)

        GL.glUniform4f(rot_loc, *self._angle.as_quat_numpy.tolist())
        self._vbo.render()

        GL.glUniform4f(rot_loc, *self._flip_angle.as_quat_numpy.tolist())
        self._vbo.render()
