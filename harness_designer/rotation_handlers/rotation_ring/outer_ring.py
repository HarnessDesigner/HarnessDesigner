# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
The world-space protractor ring -- ticks, text and washer, with its
own-slot spin held fixed regardless of drag.

Its plane orientation still nests under the *other* two axes exactly
like every other ring in this gizmo (the "gyroscope" behavior) -- only
this axis's own Euler value is zeroed out before computing the plane,
so this ring's own ``0`` tick never moves even while the inner ring
(and the object) spin past it. See :meth:`OuterRing._disc_rotation`.

Owns the hover-highlight / click-to-snap-to-that-exact-angle
interaction -- there is no drag here, only discrete picks, done with a
real ray against each tick's own oriented box rather than a hand-rolled
screen-space nearest-point search. The 360 boxes are one NumPy array held
by :class:`._protractor_base.ProtractorRingBase` in the ring's own frame, and
:meth:`OuterRing.pick_tick_index` carries them to the world with the ring's
rotation and tests the ray against all of them in one array pass (see
"PICKING" in that module's docstring for the arrays and why nothing is ever
stale).
"""

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ._protractor_base import ProtractorRingBase, TICK_STEP_DEGREES
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import object_picker as _object_picker
from .. import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types
from ...gl.canvas_base import camera_base as _camera_base


if TYPE_CHECKING:
    from ...gl import context as _gl_context
    from ...gl.materials import material as _material


# Nearest-tick highlight color -- bright red, per "if the user clicks
# when a mark is red the rotation would be set to that exact angle."
_HOVER_TICK_COLOR = (1.0, 0.15, 0.15)


_LABEL_COLOR = (0.4, 0.4, 0.4, 1.0)


class OuterRing(ProtractorRingBase):
    """
    One axis's world-space, fixed-spin protractor ring.

    :param axis: ``'x'``, ``'y'`` or ``'z'`` -- which Euler slot this
                 ring displays a snap target for.

    :param obj_angle: The tracked object's own :class:`Angle` instance,
                      read (not written) to keep this ring's plane nested
                      under the other two axes' current values.
    """

    _HOVER_COLOR = _HOVER_TICK_COLOR

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, inner_radius: float,
                 outer_radius: float, depth: float, material: "_material.GLMaterial", label_size: float,
                 obj_angle: _angle.Angle, context: "_gl_context.GLContext",
                 camera: _Union["_camera_base.CameraBase", None] = None,
                 local_tilt: _angle.Angle | None = None):

        self._obj_angle = obj_angle

        # The outer protractor's ID sits at the torus ring -- the only
        # side clear of it is the OD, away from the object -- see
        # ProtractorRingBase's own docstring.
        super().__init__(axis, center, inner_radius, outer_radius, depth,
                         material, label_size, context, camera, labels_outward=True,
                         local_tilt=local_tilt)

        self.reposition_all(self._disc_rotation())
        self.start_camera_tracking()

    @_check_types.do
    def _get_label_color(self) -> tuple[float, float, float, float]:
        return _LABEL_COLOR

    @_check_types.do
    def _disc_rotation(self) -> _angle.Angle:
        ex, ey, ez = self._obj_angle.as_euler_float

        if self.axis == 'x':
            ex = 0.0
        elif self.axis == 'y':
            ey = 0.0
        else:
            ez = 0.0

        return _rotation_mesh.slot_ring_angle(self.axis, (ex, ey, ez))

    @_check_types.do
    def on_object_angle_changed(self) -> None:
        """
        Refresh the label placement when either of the *other* two
        axes changes (this ring's own axis never moves it -- see
        :meth:`_disc_rotation`).
        """

        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def pick_tick_index(self, mouse_pos: _point.Point,
                        camera: _camera_base.CameraBase) -> int | None:
        """
        Ray-cast *mouse_pos* against every tick's oriented box and return
        the index (degrees / :data:`~._protractor_base.TICK_STEP_DEGREES`) of
        the nearest tick the ray passes through, or ``None``.

        The boxes live in the ring's own frame as three arrays (see
        ``_box_centre_l`` / ``_box_axes_l`` / ``_box_half`` in
        :class:`._protractor_base.ProtractorRingBase`); here they are carried
        to the world with the ring's current rotation and centre (one matmul
        each) and the ray is tested against all 360 with the slab method,
        vectorised: for each box, along each of its three axes the ray enters
        and leaves the slab between ``(e -+ half) / f`` (``e`` = the box
        centre's offset from the ray origin along the axis, ``f`` = the ray
        direction along it); the ray hits the box when the latest entry is not
        after the earliest exit and that exit is not behind the origin. A ray
        parallel to a slab either stays inside it (no constraint) or is outside
        it (a miss). The same test as ``gl.object_picker._ray_intersect_obb``,
        over arrays (checked against it on random rays).

        :returns: The hit tick nearest the ray origin, or ``None`` if the ray
            misses every tick or this ring is not visible.
        """

        if not self.is_visible:
            return None

        origin, direction = _object_picker.build_ray(mouse_pos, camera)
        if origin is None:
            return None

        origin = origin.astype(np.float64)
        direction = direction.astype(np.float64)

        matrix_t = self._ring_matrix.T

        centres = self._box_centre_l @ matrix_t + self._center_array()
        axes = self._box_axes_l @ matrix_t

        offset = np.einsum('nak,nk->na', axes, centres - origin)
        along = axes @ direction

        half = self._box_half
        parallel = np.abs(along) <= 1e-8
        divisor = np.where(parallel, 1.0, along)

        near = (offset - half) / divisor
        far = (offset + half) / divisor
        outside = np.abs(offset) > half

        slab_in = np.where(parallel, np.where(outside, np.inf, -np.inf), np.minimum(near, far))
        slab_out = np.where(parallel, np.where(outside, -np.inf, np.inf), np.maximum(near, far))

        enter = np.maximum(0.0, slab_in.max(axis=1))
        leave = slab_out.min(axis=1)

        hit = (enter <= leave) & (leave >= 0.0)

        if not hit.any():
            return None

        return int(np.argmin(np.where(hit, enter, np.inf)))

    @_check_types.do
    def update_hover(self, mouse_pos: _point.Point,
                     camera: _camera_base.CameraBase) -> bool:

        """
        Find the tick under *mouse_pos* and mark it hovered, clearing
        the hover if none is under it.

        :returns: Whether a tick is now hovered.
        """

        self._hovered_index = self.pick_tick_index(mouse_pos, camera)
        return self._hovered_index is not None

    @_check_types.do
    def click_hovered(self) -> float | None:
        """
        Return the Euler value the hovered tick snaps this axis to,
        or ``None`` if nothing is currently hovered. The caller writes
        the value back to ``obj_angle`` (same reasoning as
        :meth:`.inner_ring.InnerRing.update_drag` -- this class only
        computes, the assembler owns the write/unbind-rebind).
        """

        if self._hovered_index is None:
            return None

        return _rotation_mesh.wrap_angle(self._hovered_index * TICK_STEP_DEGREES)

    @property
    @_check_types.do
    def hovered_degrees(self) -> float | None:
        if self._hovered_index is None:
            return None

        return self._hovered_index * TICK_STEP_DEGREES

    @_check_types.do
    def clear_hover(self) -> None:
        self._hovered_index = None

    @_check_types.do
    def delete(self, context: "_gl_context.GLContext") -> None:
        super().delete(context)
