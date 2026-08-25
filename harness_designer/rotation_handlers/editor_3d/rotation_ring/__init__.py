# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Assembles one axis's :class:`~.torus_ring.TorusRing` +
:class:`~.inner_ring.InnerRing` + :class:`~.outer_ring.OuterRing` into a
single :class:`RotationRing`, and owns the show/hide/pickability state
machine between them.

Initial state: only the torus ring is visible and pickable (the
"always-on" activation ring for this axis). Clicking it (see
:meth:`RotationRing.try_activate`) shows this axis's protractor (inner
+ outer rings) and dims/depickables the torus; the sibling axes' torus
rings get dimmed too, via :meth:`RotationRing.set_dimmed` -- called by
whatever owns all three instances (``rotation_handlers/rotation_rings.py``)
since dimming a sibling is inherently a cross-axis decision this class
can't make on its own.
"""

from typing import TYPE_CHECKING

from .torus_ring import TorusRing
from .inner_ring import InnerRing
from .outer_ring import OuterRing
from ....geometry import point as _point
from ....geometry import angle as _angle
from ....gl import materials as _materials
from ....gl.canvas_base import rotation_mesh as _rotation_mesh
from .... import color as _color
from .... import check_types as _check_types

if TYPE_CHECKING:
    from ...gl.canvas_base import camera_base as _camera_base
    from ...gl import shaders as _shaders


# Torus opacity while a sibling axis's protractor is active -- "the
# other 2 rings would becomes more transparent."
_DIMMED_ALPHA = 0.25
_NORMAL_ALPHA = 1.0


class RotationRing:
    """One axis's full protractor gizmo (torus + inner + outer rings).

    :param axis: ``'x'``, ``'y'`` or ``'z'``.
    :param center: World-space center -- shared with the tracked
        object's position (not copied), same as every other piece of
        this gizmo.
    :param obj_angle: The tracked object's own :class:`Angle` (shared
        reference) -- every sub-ring reads this directly rather than
        keeping its own synced copy.
    :param radius: Torus ring radius. The protractor rings sit just
        inside it (see :data:`_PROTRACTOR_RADIUS_SCALE`).
    :param tube_diameter_scale: Torus tube thickness, as a fraction of
        *radius* -- ``Config.rotation_rings.tube_diameter_scale``.
    :param color: Base RGB for this axis (muted, not the old gizmo's
        saturated primaries -- see the docstring on
        ``rotation_handlers/rotation_rings.py`` for the config knobs).
    :param label_size: Font size for tick numbers.
    """

    # Inner is the larger (outermost) of the two flat protractor rings,
    # outer the smaller (innermost) -- "inner"/"outer" names their role
    # (object-space vs. world-space spin), not their radial order. The
    # torus -- the always-on, click-to-activate ring -- sits radially
    # between the two, splitting them, and is the one actually grabbed
    # to free-rotate once its axis is active (the inner ring is what
    # that drag rotates, not what you click on to start it).
    _INNER_RADIUS_SCALE = 0.82
    _OUTER_RADIUS_SCALE = _INNER_RADIUS_SCALE * 0.92
    _TORUS_RADIUS_SCALE = (_INNER_RADIUS_SCALE + _OUTER_RADIUS_SCALE) / 2.0
    _PROTRACTOR_DEPTH_SCALE = 0.03

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point,
                obj_angle: _angle.Angle, radius: float,
                tube_diameter_scale: float, color: "_color.Color",
                label_size: float, context, camera=None):

        self.axis = axis
        self.center = center
        self.obj_angle = obj_angle
        self.radius = radius

        self.is_active = False
        self._dimmed = False

        cr, cg, cb = color.rgb
        torus_material = _materials.Plastic(color)
        protractor_material = _materials.Glowing(_color.Color(cr, cg, cb, 40))

        torus_angle = _rotation_mesh.slot_ring_angle(axis, obj_angle.as_euler_float)
        self.torus = TorusRing(
            center, torus_angle, radius * self._TORUS_RADIUS_SCALE,
            tube_diameter_scale, torus_material, context)

        inner_radius = radius * self._INNER_RADIUS_SCALE
        outer_radius = radius * self._OUTER_RADIUS_SCALE
        protractor_depth = radius * self._PROTRACTOR_DEPTH_SCALE

        self.inner = InnerRing(
            axis, center, inner_radius, protractor_depth,
            protractor_material, label_size, obj_angle, context, camera)

        self.outer = OuterRing(
            axis, center, outer_radius, protractor_depth,
            protractor_material, label_size, obj_angle, context, camera)

    @_check_types.do
    def on_object_angle_changed(self) -> None:
        """Refresh every sub-ring's orientation -- call whenever
        ``obj_angle``'s callback fires. Runs for all three axes'
        instances regardless of which is active, since the gyroscope
        nesting means any axis's change can move any ring's plane.
        """
        self.torus.angle = _rotation_mesh.slot_ring_angle(
            self.axis, self.obj_angle.as_euler_float)
        self.inner.on_object_angle_changed()
        self.outer.on_object_angle_changed()

    @_check_types.do
    def on_object_scale_changed(self, radius: float) -> None:
        """Resize when the tracked object's scale changes -- the caller
        (the owning ``RotationRings3D``-equivalent) recomputes *radius*
        the same way ``Rings3D._compute_size`` always did; this method
        just re-derives everything downstream of it.
        """
        self.radius = radius
        self.torus.radius = radius * self._TORUS_RADIUS_SCALE
        self.inner.radius = radius * self._INNER_RADIUS_SCALE
        self.outer.radius = radius * self._OUTER_RADIUS_SCALE
        self.inner.depth = radius * self._PROTRACTOR_DEPTH_SCALE
        self.outer.depth = radius * self._PROTRACTOR_DEPTH_SCALE

        if self.is_active:
            self.inner.reposition_all(self.inner._disc_rotation())  # NOQA
            self.outer.reposition_all(self.outer._disc_rotation())  # NOQA

    @_check_types.do
    def set_dimmed(self, flag: bool) -> None:
        """Dim/undim this axis's torus ring -- called on the two axes
        that are NOT the one just activated.
        """
        self._dimmed = flag
        self.torus.material.diffuse[3] = _DIMMED_ALPHA if flag else _NORMAL_ALPHA
        self.torus.is_pickable = not flag and not self.is_active

    @_check_types.do
    def activate(self) -> None:
        """Show this axis's protractor and stop this torus from being
        pickable (dragging now happens on the protractor bands).
        """
        self.is_active = True
        self.torus.is_pickable = False
        self.inner.is_visible = True
        self.outer.is_visible = True
        self.inner.reposition_all(self.inner._disc_rotation())  # NOQA
        self.outer.reposition_all(self.outer._disc_rotation())  # NOQA

    @_check_types.do
    def deactivate(self) -> None:
        """Hide this axis's protractor and restore normal torus picking."""
        self.is_active = False
        self.inner.is_visible = False
        self.outer.is_visible = False
        self.inner.end_drag()
        self.outer.clear_hover()
        self.torus.is_pickable = not self._dimmed

    @_check_types.do
    def hit_test_torus(self, mouse_pos: _point.Point,
                       camera: "_camera_base.CameraBase") -> bool:
        return self.torus.hit_test(mouse_pos, camera)

    @_check_types.do
    def hit_test_inner(self, mouse_pos: _point.Point,
                       camera: "_camera_base.CameraBase") -> bool:
        return self.is_active and self.inner.hit_test(mouse_pos, camera)

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        self.torus.render(shaders)

        if self.is_active:
            self.inner.render(shaders)
            self.outer.render(shaders)

    @_check_types.do
    def delete(self, context) -> None:
        self.torus.delete(context)
        self.inner.delete(context)
        self.outer.delete(context)
