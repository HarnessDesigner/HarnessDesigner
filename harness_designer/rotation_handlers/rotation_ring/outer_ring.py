# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The world-space protractor ring -- ticks, text and washer, with its
own-slot spin held fixed regardless of drag.

Its plane orientation still nests under the *other* two axes exactly
like every other ring in this gizmo (the "gyroscope" behavior) -- only
this axis's own Euler value is zeroed out before computing the plane,
so this ring's own ``0`` tick never moves even while the inner ring
(and the object) spin past it. See :meth:`OuterRing._disc_rotation`.

Owns the hover-highlight / click-to-snap-to-that-exact-angle
interaction -- there is no drag here, only discrete picks, done via a
real ray-cast against each tick's own oriented box (see
:mod:`.tick_pick_object` and :mod:`~...gl.object_picker`) rather than a
hand-rolled screen-space nearest-point search.
"""

from typing import TYPE_CHECKING

from . import tick_pick_object as _tick_pick_object
from ._protractor_base import ProtractorRingBase
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import object_picker as _object_picker
from .. import rotation_mesh as _rotation_mesh
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ... import ui as _ui
    from ...objects.objectsvar import base_var as _base_var
    from ...gl.canvas_base import camera_base as _camera_base
    from ._protractor_base import _Tick


# Nearest-tick highlight color -- bright red, per "if the user clicks
# when a mark is red the rotation would be set to that exact angle."
_HOVER_TICK_COLOR = (1.0, 0.15, 0.15)


_LABEL_COLOR = (0.4, 0.4, 0.4, 1.0)


class OuterRing(ProtractorRingBase):
    """One axis's world-space, fixed-spin protractor ring.

    :param axis: ``'x'``, ``'y'`` or ``'z'`` -- which Euler slot this
        ring displays a snap target for.
    :param obj_angle: The tracked object's own :class:`Angle` instance,
        read (not written) to keep this ring's plane nested under the
        other two axes' current values.
    :param mainframe: Needed only to satisfy
        :class:`.tick_pick_object.TickPickObject`'s own ``ObjectBase``
        constructor -- ticks are never registered with it (see that
        module's docstring).
    :param base_cls: Whichever of ``Base3D``/``BaseSchematic``/
        ``BasePegboard`` matches the view this ring actually belongs to
        -- every tick's own pickable view instance is built from this,
        since a tick (unlike the ring assembler classes) only ever
        exists in one view at a time.
    """

    @_check_types.do
    def __init__(self, axis: str, center: _point.Point, inner_radius: float,
                outer_radius: float, depth: float, material, label_size: float,
                obj_angle: _angle.Angle, context, mainframe: "_ui.MainFrame",
                base_cls: "type[_base_var.BaseVar]", camera=None):

        self._obj_angle = obj_angle
        self._hovered_tick = None

        # The outer protractor's ID sits at the torus ring -- the only
        # side clear of it is the OD, away from the object -- see
        # ProtractorRingBase's own docstring.
        super().__init__(axis, center, inner_radius, outer_radius, depth, material, label_size, context,
                         camera, labels_outward=True)

        self._pick_objects: list[_tick_pick_object.TickPickObject] = []
        self._tick_by_pick_obj: dict[_tick_pick_object.TickPickObject, "_Tick"] = {}

        # Real oriented-box picking for outer-ring ticks only (per this
        # gizmo's own design -- the inner ring never gets clickable
        # ticks, only its band-drag) -- each tick gets a pickable view
        # instance sharing the same cylinder VBO ticks already render
        # with, so gl.object_picker.find_object can ray-cast against it
        # exactly like any real scene object, without one ever being
        # registered as one (see tick_pick_object.py).
        with context:
            # One pickable stand-in for the whole washer (reusing its
            # own already-baked-to-real-dimensions VBO, see
            # _protractor_base.ProtractorRingBase._build_disc_vbo, hence
            # scale (1,1,1)) -- a cheap first-stage gate in pick_tick()
            # so a mouse move/click nowhere near this ring never has to
            # ray-cast (and screen-project every corner of) all
            # TICK_COUNT (360) individual tick boxes just to find that
            # out.
            self._ring_pick_facade = _tick_pick_object.TickPickObject(mainframe)
            ring_view_obj = base_cls(
                self._ring_pick_facade, None, self._disc_vbo, self._disc_rotation(),
                self.center, _point.Point(1.0, 1.0, 1.0), None)
            self._ring_pick_facade.set_view(ring_view_obj)

            for tick in self._ticks:
                facade = _tick_pick_object.TickPickObject(mainframe)
                view_obj = base_cls(
                    facade, None, self._tick_vbo, tick.mesh_rotation,
                    tick.position, _point.Point(1.0, 1.0, 1.0), None)
                facade.set_view(view_obj)

                self._pick_objects.append(facade)
                self._tick_by_pick_obj[facade] = tick

        self.reposition_all(self._disc_rotation())
        self.start_camera_tracking()

    def _get_label_color(self):
        return _LABEL_COLOR

    @_check_types.do
    def _disc_rotation(self) -> "_angle.Angle":
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
        """Refresh tick/label placement when either of the *other* two
        axes changes (this ring's own axis never moves it -- see
        :meth:`_disc_rotation`).
        """
        self.reposition_all(self._disc_rotation())

    @_check_types.do
    def reposition_all(self, ring_angle: "_angle.Angle") -> bool:
        """Reposition every tick (see the base class) then re-sync each
        tick's pickable view instance to match -- its obb/aabb has to
        track the same position/angle/length the tick itself just got,
        or a stale one would let picks land on where a tick used to be.

        Ticks have no externally-shared Point/Angle for
        ``BaseVar``'s usual bind-and-mutate-in-place invalidation to
        hook into (see ``objects_3d/base_3d.py``'s own
        ``_update_position`` for that normal path) -- ``OuterRing`` is
        each tick's sole owner, so writing the transform straight into
        the view instance's own private fields and recomputing obb/aabb
        immediately after is just that same invalidation, done directly
        instead of through a callback that would only be firing back to
        this same code anyway.

        Skips its own pick-object resync (the same ``ring_angle`` dirty
        check the base class already made -- see its own docstring)
        whenever the base class's reposition was itself a no-op, so a
        frame where this ring's orientation genuinely didn't change
        doesn't still pay for 360 individual obb/aabb recomputes.
        """
        if not super().reposition_all(ring_angle):
            return False

        ring_view_obj = self._ring_pick_facade.obj3d
        ring_view_obj._angle = ring_angle  # NOQA
        ring_view_obj._compute_obb()  # NOQA
        ring_view_obj._compute_aabb()  # NOQA

        if not self._pick_objects:
            return True

        # zip(self._ticks, self._pick_objects), not self._tick_by_pick_obj
        # -- both lists were built from the same single pass over
        # self._ticks (see __init__), so they're already index-aligned;
        # the dict is only needed for pick_tick()'s reverse lookup
        # (facade -> tick after a hit), not for this forward sync.
        for tick, facade in zip(self._ticks, self._pick_objects):
            view_obj = facade.obj3d

            view_obj._position = tick.position  # NOQA
            view_obj._angle = tick.mesh_rotation  # NOQA
            view_obj._scale = tick.scale  # NOQA
            view_obj.numpy_position = tick.position.as_numpy

            view_obj._compute_obb()  # NOQA
            view_obj._compute_aabb()  # NOQA

        return True

    @_check_types.do
    def pick_tick(self, mouse_pos: _point.Point,
                 camera: "_camera_base.CameraBase") -> "_Tick | None":
        """Ray-cast *mouse_pos* against every tick's own oriented box
        (see :mod:`~...gl.object_picker`) and return whichever ``_Tick``
        it actually landed on, or ``None``.

        Gated on a cheap first-stage test against the whole washer (one
        candidate) -- most mouse moves/clicks land nowhere near this
        ring at all, and screen-projecting and ray-casting all
        :data:`~._protractor_base.TICK_COUNT` (360) individual tick
        boxes to find that out, on every single mouse move, is wasted
        work the ring-level test already rules out far more cheaply.
        """
        if not self.is_visible or not self._pick_objects:
            return None

        ring_hit = _object_picker.find_object(
            mouse_pos, [self._ring_pick_facade], camera, get_view=lambda t: t.obj3d)
        if ring_hit is None:
            return None

        found = _object_picker.find_object(
            mouse_pos, self._pick_objects, camera, get_view=lambda t: t.obj3d)

        if found is None:
            return None

        return self._tick_by_pick_obj.get(found)

    @_check_types.do
    def update_hover(self, mouse_pos: _point.Point,
                     camera: "_camera_base.CameraBase") -> bool:
        """Find the tick under *mouse_pos* and mark it hovered, clearing
        the hover if none is under it.

        :returns: Whether a tick is now hovered.
        """
        tick = self.pick_tick(mouse_pos, camera)
        self._hovered_tick = tick
        return tick is not None

    @_check_types.do
    def click_hovered(self) -> float | None:
        """Return the Euler value the hovered tick snaps this axis to,
        or ``None`` if nothing is currently hovered. The caller writes
        the value back to ``obj_angle`` (same reasoning as
        :meth:`.inner_ring.InnerRing.update_drag` -- this class only
        computes, the assembler owns the write/unbind-rebind).
        """
        if self._hovered_tick is None:
            return None

        return _rotation_mesh.wrap_angle(self._hovered_tick.degrees)

    @property
    @_check_types.do
    def hovered_degrees(self) -> float | None:
        if self._hovered_tick is None:
            return None
        return self._hovered_tick.degrees

    @_check_types.do
    def clear_hover(self) -> None:
        self._hovered_tick = None

    @_check_types.do
    def _tick_override_color(self, degrees: float) -> "tuple[float, float, float] | None":
        if self._hovered_tick is not None and self._hovered_tick.degrees == degrees:
            return _HOVER_TICK_COLOR
        return None

    @_check_types.do
    def delete(self, context) -> None:
        super().delete(context)
