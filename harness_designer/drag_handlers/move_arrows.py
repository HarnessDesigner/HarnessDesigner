# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ..shapes import arrow as _arrow
from ..objects.objects_3d import base_3d as _base_3d
from ..objects.objects_schematic import base_schematic as _base_schematic
from ..objects.objects_pegboard import base_pegboard as _base_pegboard
from ..objects import object_base as _object_base
from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl import materials as _materials
from .. import color as _color
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..gl import shaders as _shaders


# Scale factor applied to the object's max dimension
# to determine arrow length
ARROW_LENGTH_SCALE = 0.055

# Scale factor applied to the object's max dimension
# to determine arrow offset from the object
ARROW_OFFSET_SCALE = 2.0


class MoveArrows(_object_base.ObjectBase):

    @_check_types.do
    def __init__(self, obj_position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        """
        Initialise the :class:`MoveArrows` instance.

        :param obj_position: Value for ``obj_position``.
        :type obj_position: :class:`_point.Point`

        :param axis: Value for ``axis``.
        :type axis: str

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`

        :param aabb: Value for ``aabb``.
        :type aabb: :class:`np.ndarray`
        """
        _object_base.ObjectBase.__init__(self, mainframe, None)
        self.objschematic = ArrowsSchematic(self)
        self.objpegboard = ArrowsPegboard(self)
        self.obj3d = Arrows3D(self, obj_position, axis, mainframe, aabb)
        self._treeitem = None
        self.mainframe.add_object(self)

    @_check_types.do
    def set_treeitem(self, treeitem):
        self._treeitem = treeitem

    @_check_types.do
    def get_treeitem(self):
        return self._treeitem

    @_check_types.do
    def __del__(self):
        try:
            self.delete()
        except RuntimeError:
            pass

    @_check_types.do
    def delete(self):
        self.mainframe.remove_object(self)

    @_check_types.do
    def close(self):
        raise NotImplementedError

    @_check_types.do
    def set_selected(self, flag):
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        return False

    @is_selected.setter
    @_check_types.do
    def is_selected(self, value: bool):
        pass


class ArrowsSchematic(_base_schematic.BaseSchematic):

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent, None, None, None,
                         None, None, None)

    @_check_types.do
    def set_selected(self, flag: bool):
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        return False


class ArrowsPegboard(_base_pegboard.BasePegboard):

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent, None, None, None,
                         None, None, None)

    @_check_types.do
    def set_selected(self, flag: bool):
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        return False


class Arrows3D(_base_3d.Base3D):

    @_check_types.do
    def __init__(self, parent, obj_position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):

        # Create cyan material
        color = _color.Color(0, 170, 170, 255)
        material = _materials.Glowing(color)

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
            offset1 = _point.Point(width / 2 * 0.7, 0, depth / 2.0 * 1.40)
            arrow_angle = _angle.Angle.from_euler(0, 0, 0)

            offset2 = _point.Point(-width / 2 * 0.7, 0, depth / 2.0 * 1.40)
            flip = _angle.Angle.from_euler(0, 180, 0)

        elif axis == 'z':
            # Arrow along Z axis, positioned above the object
            offset1 = _point.Point(-width / 2.0 * 1.40, 0, depth / 2 * 0.7)

            arrow_angle = _angle.Angle.from_euler(0, 270, 0)

            offset2 = _point.Point(-width / 2.0 * 1.40, 0, -depth / 2 * 0.7)
            flip = _angle.Angle.from_euler(0, 90, 0)

        else:  # axis == 'y'
            # Arrow along Y axis, positioned to the side of the object
            offset1 = _point.Point(width / 2.0 * 1.40, -height / 2.0 * 0.7, 0)
            arrow_angle = _angle.Angle.from_euler(0, 0, -90)

            offset2 = _point.Point(width / 2.0 * 1.40, height / 2.0 * 0.7, 0)
            flip = _angle.Angle.from_euler(180, 0,  -90)

        self._arrow1_offset = offset1
        self._arrow2_offset = offset2
        self._flip_angle = flip

        # Set initial arrow position relative to tracked object
        position = obj_position.copy()

        # Bind to tracked position so arrow follows the object being dragged
        obj_position.bind(self._on_obj_position)
        self._obj_position = obj_position
        self._o_obj_position = obj_position.copy()

        # _floor_guard defeats Base3D.__init__'s inline floor-lock check —
        # the arrows are a UI element and must never be pushed off their
        # anchor by the ground plane
        self._floor_guard = True

        with mainframe.editor3d.context:
            vbo = _arrow.create_vbo()
            super().__init__(parent, None, vbo,
                             arrow_angle, position, scale, material)

        self._floor_guard = False
        self._compute_aabb()

        self._is_visible = True

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Track position changes WITHOUT Base3D's floor-lock logic.

        The base implementation re-applies the floor lock on every position
        write, which pushes the arrows off their anchor whenever the dragged
        object nears the ground plane.
        """
        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

    @_check_types.do
    def _compute_aabb(self):
        _base_3d.Base3D._compute_aabb(self)

        if getattr(self, '_floor_guard', False):
            ground = float(self.editor3d.config.floor.ground_height)
            if self._aabb[0][1] < ground:
                self._aabb[0][1] = ground

    @_check_types.do
    def _on_obj_position(self, position: _point.Point):
        delta = position - self._o_obj_position
        self._o_obj_position = position.copy()

        self._position += delta

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram"):
        faces_program = shaders.faces

        with faces_program:
            self._material.set(faces_program)

            # The arrows are a UI element, not part of the scene — suppress the
            # floor reflection for them, then restore the global config value so
            # objects rendered after the arrows keep theirs.
            faces_program.has_reflection = 0

            # A WireStripe drawn earlier in the same frame can leave
            # stripeClipStart/stripeClipStop set to a real window, which
            # would otherwise clip this gizmo's own geometry too.
            faces_program.stripe_clip_start = 0.0
            faces_program.stripe_clip_stop = 0.0

            # Render first arrow (positive direction). smooth=None here
            # (not self.smooth) preserves this gizmo's original behavior
            # of never touching normalMode at all -- see gl/vbo.py's
            # render() docstring.
            self._vbo.render(faces_program,
                             self._position + self._arrow1_offset, self._angle,
                             self._scale, None)

            # Render second arrow (negative direction - 180° flipped)
            self._vbo.render(faces_program,
                             self._position + self._arrow2_offset, self._flip_angle,
                             self._scale, None)

            config = self.editor3d.config
            reflect = int(config.floor.reflections.enable and
                          config.floor.enable_floor_lock)

            faces_program.has_reflection = reflect
