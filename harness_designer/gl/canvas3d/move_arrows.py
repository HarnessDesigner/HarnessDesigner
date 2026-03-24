from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ...shapes import arrow as _arrow
from ...objects.objects3d import base3d as _base3d
from ...objects.objects2d import base2d as _base2d

from ...objects import object_base as _object_base
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import color as _color

if TYPE_CHECKING:
    from ... import ui as _ui


# Scale factor applied to the object's max dimension to determine arrow length
ARROW_LENGTH_SCALE = 0.05

# Scale factor applied to the object's max dimension to determine arrow offset from the object
ARROW_OFFSET_SCALE = 2.0


class MoveArrows(_object_base.ObjectBase):

    def __init__(self, obj_position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        _object_base.ObjectBase.__init__(self, mainframe)
        self.obj2d = Arrows2D(self)
        self.obj3d = Arrows3D(self, obj_position, axis, mainframe, aabb)
        self._treeitem = None
        self.mainframe.add_object(self)

    def set_treeitem(self, treeitem):
        self._treeitem = treeitem

    def get_treeitem(self):
        return self._treeitem

    def __del__(self):
        self.delete()

    def delete(self):
        self.mainframe.remove_object(self)

    def close(self):
        raise NotImplementedError

    def set_selected(self, flag):
        pass

    @property
    def is_selected(self) -> bool:
        return False

    @is_selected.setter
    def is_selected(self, value: bool):
        pass


class Arrows2D(_base2d.Base2D):

    def __init__(self, parent):
        _base2d.Base2D.__init__(self, parent, None)

    def set_selected(self, flag: bool):
        pass

    @property
    def is_selected(self) -> bool:
        return False


class Arrows3D(_base3d.Base3D):

    def __init__(self, parent, obj_position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        """
        Create movement arrows for visual feedback during dragging.

        Args:
            obj_position: The Point instance from the object being dragged (to bind callback)
            axis: String - 'x', 'y', or 'z' indicating which axis is locked
            mainframe: MainFrame reference
            aabb: The object's axis-aligned bounding box for sizing calculations
        """
        # CRITICAL: Set OpenGL context before creating VBO
        with mainframe.editor3d.context:
            vbo = _arrow.create_vbo()

        # Create cyan material
        cyan = _color.Color(0, 255, 255, 170)
        material = _materials.Polished(cyan)

        # Calculate arrow dimensions from object AABB
        width = abs(aabb[1][0] - aabb[0][0])
        height = abs(aabb[1][1] - aabb[0][1])
        depth = abs(aabb[1][2] - aabb[0][2])
        max_dim = max(width, height, depth)

        # Scale the Z length of the VBO geometry (VBO always points along +Z)
        arrow_scale = max_dim * ARROW_LENGTH_SCALE
        scale = _point.Point(arrow_scale, arrow_scale, arrow_scale)

        if axis == 'x':
            # Arrow along X axis, positioned above the object
            offset = _point.Point(width / 2, 0, 0)
            arrow_angle = _angle.Angle.from_euler(0, 0, 0)  # Rotate Z to X
            flip = _angle.Angle.from_euler(0, 180, 0)        # 180° around Y

        elif axis == 'z':
            # Arrow along Z axis, positioned above the object
            offset = _point.Point(0, 0, depth / 2)
            arrow_angle = _angle.Angle.from_euler(0, 90, 0)   # Already points along Z
            flip = _angle.Angle.from_euler(0, 270, 0)        # 180° around X

        else:  # axis == 'y'
            # Arrow along Y axis, positioned to the side of the object
            offset = _point.Point(0, height / 2, 0)
            arrow_angle = _angle.Angle.from_euler(0, 0, -90)  # Rotate Z to Y
            flip = _angle.Angle.from_euler(180, 0, 90)         # 180° around X

        self._offset = offset
        self._flip_angle = flip

        # Set initial arrow position relative to tracked object
        position = obj_position.copy()

        # Bind to tracked position so arrow follows the object being dragged
        obj_position.bind(self._on_obj_position)
        self._obj_position = obj_position
        self._o_obj_position = obj_position.copy()

        _base3d.Base3D.__init__(self, parent, None, vbo, arrow_angle, position, scale, material)
        self._is_visible = True

    def _on_obj_position(self, position: _point.Point):
        """Update arrow position when the dragged object moves."""

        delta = position - self._o_obj_position
        self._o_obj_position = position.copy()

        self._position += delta

    def render(self, shader_program):
        """Render bidirectional arrow by drawing the VBO twice with a 180° rotation."""

        # Set material
        self._material.set(shader_program)

        # Get uniform locations
        pos_loc = GL.glGetUniformLocation(shader_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(shader_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(shader_program, "objectScale")

        objectHasReflectionLoc = GL.glGetUniformLocation(shader_program, "objectHasReflection")
        GL.glUniform1i(objectHasReflectionLoc, 1)

        GL.glUniform3f(pos_loc, *(self._position + self._offset).as_float)
        GL.glUniform3f(scale_loc, *self._scale.as_float)

        # Render first arrow (positive direction)
        GL.glUniform4f(rot_loc, *self._angle.as_quat_numpy.tolist())
        self._vbo.render()

        GL.glUniform3f(pos_loc, *(self._position + (-self._offset)).as_float)
        # Render second arrow (negative direction - 180° flipped)
        GL.glUniform4f(rot_loc, *self._flip_angle.as_quat_numpy.tolist())
        self._vbo.render()
