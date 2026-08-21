# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Directional-arrow gizmo for a wire-marker drag, oriented along the
wire the marker is constrained to instead of a world axis.

Structurally mirrors :class:`~.move_arrows.MoveArrows`/``Arrows3D`` (same
single cached arrow VBO -- see ``shapes.arrow.create_vbo`` -- drawn twice
per frame with different position/rotation uniforms for the bidirectional
look) but takes the arrow's orientation/position/scale supplied directly
rather than derived internally from a fixed ``'x'``/``'y'``/``'z'`` axis
string -- a wire marker's drag is constrained to an arbitrary (not
axis-aligned) line, so there is no discrete axis to look up.

The rotation math (:func:`angle_for_direction`) was verified numerically
against ``Arrows3D``'s own hardcoded per-axis quaternions before use (see
session notes) -- ``shapes.arrow.create_vbo``'s mesh points along local
+X, NOT local -Z like :meth:`~harness_designer.geometry.angle.angle.Angle.from_points`
assumes for every other object in the codebase, so ``from_points`` itself
cannot be reused here without producing a mirrored/incorrect orientation.
"""

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ...shapes import arrow as _arrow
from ...objects.objects_3d import base_3d as _base_3d
from ...objects.objects_schematic import base_schematic as _base_schematic
from ...objects import object_base as _object_base
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


# Scale factor applied to the object's max dimension to determine arrow length
ARROW_LENGTH_SCALE = 0.055

# Scale factor applied to the object's max dimension to determine arrow offset from the object
ARROW_OFFSET_SCALE = 1.40


@_check_types.do
def angle_for_direction(direction: np.ndarray) -> "_angle.Angle":
    """Return the :class:`Angle` that rotates the arrow mesh's local
    forward axis (+X, per ``shapes.arrow.create_vbo``'s geometry) onto
    world-space *direction*.

    Mirrors the right/up/forward orthonormal-basis construction
    :meth:`Angle.from_points` uses internally, but for a local-forward of
    +X (this mesh's own convention) instead of -Z (the convention every
    other object in the codebase uses via ``from_points``) -- verified
    numerically to reproduce ``Arrows3D``'s own hardcoded per-axis
    quaternions for the world X/Y/Z cases, plus two arbitrary
    non-axis-aligned directions, before being used here.

    :param direction: World-space direction to point the arrow along.
        Need not be pre-normalized.
    """
    direction = np.asarray(direction, dtype=np.float32)
    norm = np.linalg.norm(direction)
    if norm < 1e-8:
        return _angle.Angle.from_euler(0.0, 0.0, 0.0)

    forward = direction / norm

    up = np.asarray((0.0, 1.0, 0.0), dtype=np.float32)
    if np.allclose(np.abs(np.dot(forward, up)), 1.0, atol=1e-6):
        up = np.asarray((0.0, 0.0, 1.0), dtype=np.float32)

    right = np.cross(up, forward)  # NOQA
    right = right / np.linalg.norm(right)

    true_up = np.cross(forward, right)  # NOQA

    rot = np.column_stack((forward, right, true_up))
    return _angle.Angle.from_matrix(rot)


class WireMarkerArrow(_object_base.ObjectBase):
    """Wraps the bidirectional wire-direction arrow gizmo -- see the
    module docstring."""

    @_check_types.do
    def __init__(self, obj_position: _point.Point, direction: np.ndarray,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        """Initialise the :class:`WireMarkerArrow` instance.

        :param obj_position: The dragged marker's own Point (bound so the
            gizmo follows it as it's constrained back onto the wire).
        :param direction: World-space direction of the wire the marker
            sits on (either endpoint order -- the gizmo is bidirectional).
        :param mainframe: MainFrame reference.
        :param aabb: The marker's axis-aligned bounding box, for sizing.
        """
        _object_base.ObjectBase.__init__(self, mainframe, None)
        self.objschematic = _ArrowMarker2D(self)
        self.obj3d = ArrowMarker3D(self, obj_position, direction, mainframe, aabb)
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


class _ArrowMarker2D(_base_schematic.BaseSchematic):
    """Dummy 2D presence -- this gizmo is a 3D-editor-only concept (wire
    markers have no schematic-view drag mechanics yet); see
    ``move_arrows.Arrows2D`` for the identical pattern."""

    @_check_types.do
    def __init__(self, parent):
        angle = _angle.Angle()
        position = _point.Point(0, 0)
        super().__init__(parent, None, None, angle, position, None, None)

    @_check_types.do
    def set_selected(self, flag: bool):
        pass

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        return False


class ArrowMarker3D(_base_3d.Base3D):
    """Renders the bidirectional wire-direction arrow pair."""

    @_check_types.do
    def __init__(self, parent, obj_position: _point.Point, direction: np.ndarray,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        color = _color.Color(0, 170, 170, 255)
        material = _materials.Glowing(color)

        width = abs(aabb[1][0] - aabb[0][0])
        height = abs(aabb[1][1] - aabb[0][1])
        depth = abs(aabb[1][2] - aabb[0][2])
        max_dim = max(width, height, depth)

        arrow_scale = max_dim * ARROW_LENGTH_SCALE
        scale = _point.Point(arrow_scale, arrow_scale, arrow_scale)

        arrow_angle = angle_for_direction(direction)
        flip = angle_for_direction(-np.asarray(direction, dtype=np.float32))

        offset_dist = max_dim / 2.0 * ARROW_OFFSET_SCALE
        norm = np.linalg.norm(direction)
        unit_dir = (np.asarray(direction, dtype=np.float32) / norm
                    if norm > 1e-8 else np.array([1.0, 0.0, 0.0], dtype=np.float32))

        offset1 = _point.Point(*[float(v) for v in (unit_dir * offset_dist)])
        offset2 = _point.Point(*[float(v) for v in (-unit_dir * offset_dist)])

        self._arrow1_offset = offset1
        self._arrow2_offset = offset2
        self._flip_angle = flip

        position = obj_position.copy()

        # Bind to the tracked marker position so the arrows follow it as
        # it's continuously re-clamped back onto the wire's line.
        obj_position.bind(self._on_obj_position)
        self._obj_position = obj_position
        self._o_obj_position = obj_position.copy()

        # _floor_guard defeats Base3D.__init__'s inline floor-lock check --
        # the arrows are a UI element and must never be pushed off their
        # anchor by the ground plane (same reasoning as move_arrows.Arrows3D).
        self._floor_guard = True

        with mainframe.editor3d.context:
            vbo = _arrow.create_vbo()
            super().__init__(parent, None, vbo, arrow_angle, position, scale, material)

        self._floor_guard = False
        self._compute_aabb()

        self._is_visible = True

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Track position changes WITHOUT Base3D's floor-lock logic --
        see move_arrows.Arrows3D._update_position for the identical
        rationale."""
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
        """Update arrow position when the dragged marker moves."""
        delta = position - self._o_obj_position
        self._o_obj_position = position.copy()

        self._position += delta

    @_check_types.do
    def render(self, faces_program, edges_program, vertices_program):
        """Render the bidirectional arrow -- same draw-the-VBO-twice
        approach as move_arrows.Arrows3D.render."""
        GL.glUseProgram(faces_program)
        self._material.set(faces_program)

        pos_loc = GL.glGetUniformLocation(faces_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(faces_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(faces_program, "objectScale")

        reflect_loc = GL.glGetUniformLocation(faces_program, "objectHasReflection")
        if reflect_loc != -1:
            GL.glUniform1i(reflect_loc, 0)

        clip_loc = GL.glGetUniformLocation(faces_program, "stripeClipLength")
        if clip_loc != -1:
            GL.glUniform1f(clip_loc, 0.0)

        GL.glUniform3f(pos_loc, *(self._position + self._arrow1_offset).as_float)
        GL.glUniform3f(scale_loc, *self._scale.as_float)

        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        self._vbo.render()

        GL.glUniform3f(pos_loc, *(self._position + self._arrow2_offset).as_float)
        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._flip_angle.as_quat_numpy.tolist()])
        self._vbo.render()

        if reflect_loc != -1:
            config = self.editor3d.config
            GL.glUniform1i(reflect_loc, int(
                config.floor.reflections.enable and
                config.floor.enable_floor_lock))
