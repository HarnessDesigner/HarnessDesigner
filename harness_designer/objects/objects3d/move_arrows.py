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


# Scale factor applied to the object's max dimension to determine arrow length
ARROW_LENGTH_SCALE = 1.5
# Scale factor applied to the object's max dimension to determine arrow offset from the object
ARROW_OFFSET_SCALE = 0.6


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
        # CRITICAL: Set OpenGL context before creating VBO
        with mainframe.editor3d.context:
            self._vbo = _arrow.create_vbo()

        # Create cyan material
        cyan = _color.Color(0, 255, 255, 255)
        self._material = _materials.Generic(cyan)

        # Calculate arrow dimensions from object AABB
        width = aabb[1][0] - aabb[0][0]
        height = aabb[1][1] - aabb[0][1]
        depth = aabb[1][2] - aabb[0][2]
        max_dim = max(width, height, depth)

        # Scale the Z length of the VBO geometry (VBO always points along +Z)
        arrow_length = max_dim * ARROW_LENGTH_SCALE
        scale = _point.Point(1.0, 1.0, arrow_length)

        if axis == 'x':
            # Arrow along X axis, positioned above the object
            offset = _point.Point(0, height / 2 + max_dim * ARROW_OFFSET_SCALE, 0)
            arrow_angle = _angle.Angle.from_euler(0, 90, 0)  # Rotate Z to X
            flip = _angle.Angle.from_euler(0, 180, 0)        # 180° around Y

        elif axis == 'z':
            # Arrow along Z axis, positioned above the object
            offset = _point.Point(0, height / 2 + max_dim * ARROW_OFFSET_SCALE, 0)
            arrow_angle = _angle.Angle.from_euler(0, 0, 0)   # Already points along Z
            flip = _angle.Angle.from_euler(180, 0, 0)        # 180° around X

        else:  # axis == 'y'
            # Arrow along Y axis, positioned to the side of the object
            offset = _point.Point(width / 2 + max_dim * ARROW_OFFSET_SCALE, 0, 0)
            arrow_angle = _angle.Angle.from_euler(-90, 0, 0)  # Rotate Z to Y
            flip = _angle.Angle.from_euler(180, 0, 0)         # 180° around X

        self._offset = offset
        self._angle = arrow_angle
        self._flip_angle = arrow_angle + flip
        self._scale = scale

        # Set initial arrow position relative to tracked object
        self._position = _point.Point(
            float(position.x) + float(offset.x),
            float(position.y) + float(offset.y),
            float(position.z) + float(offset.z),
        )

        self._is_visible = True

        # Bind to tracked position so arrow follows the object being dragged
        position.bind(self._on_position_changed)

    def _on_position_changed(self, new_position: _point.Point):
        """Update arrow position when the dragged object moves."""
        self._position.x = float(new_position.x) + float(self._offset.x)
        self._position.y = float(new_position.y) + float(self._offset.y)
        self._position.z = float(new_position.z) + float(self._offset.z)

    def render(self, shader_program):
        """Render bidirectional arrow by drawing the VBO twice with a 180° rotation."""
        if not self._is_visible:
            return

        # Set material
        self._material.set(shader_program)

        # Get uniform locations
        pos_loc = GL.glGetUniformLocation(shader_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(shader_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(shader_program, "objectScale")

        objectHasReflectionLoc = GL.glGetUniformLocation(shader_program, "objectHasReflection")
        GL.glUniform1i(objectHasReflectionLoc, 1)

        GL.glUniform3f(pos_loc, *self._position.as_float)
        GL.glUniform3f(scale_loc, *self._scale.as_float)

        # Render first arrow (positive direction)
        GL.glUniform4f(rot_loc, *self._angle.as_quat_numpy.tolist())
        self._vbo.render()

        # Render second arrow (negative direction - 180° flipped)
        GL.glUniform4f(rot_loc, *self._flip_angle.as_quat_numpy.tolist())
        self._vbo.render()
