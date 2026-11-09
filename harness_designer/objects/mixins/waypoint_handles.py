# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Waypoints are not objects of their own to see or pick: the wire, bundle or cable that owns them drags them (WAYPOINT_REWORK_DESIGN.md).

A waypoint used to be a sphere, a ``WireLayout`` / ``BundleLayout`` object drawn in the scene all the time and picked on its own. Now
the route shows its own corner (it is drawn rounded, ``objects/mixins/tube.py``) and the layout view objects have no geometry: they
are data (a position, and the database row the routing logic reads), never drawn and never picked. The exceptions that keep a
drawn layout are the markers where a split-out cable's conductors join the broken-out wires, the snap probes of the wire
placement flow, and the sphere of a waypoint being placed.

While an owner is selected, its waypoints are drag handles that belong to it:

* :meth:`WaypointOwnerMixin._handle_hit` makes the owner pickable where the mouse is over a handle (a sphere
  :data:`HANDLE_SCALE` times the diameter, centred on the point of the DRAWN path nearest the waypoint, since the rounded corner
  passes inside it), so a press there reaches the owner even beyond its tube;
* the owner's ``handle_interaction`` calls :meth:`WaypointOwnerMixin._arm_waypoint_drag` first, which arms the same drag for a
  wire, a bundle and a cable (``Generic`` through the layout's data object where there is one, ``Waypoint`` on the point itself
  for a cable, which has no layouts) and keeps the selection where it was;
* a menu's **Delete Layout** removes the waypoint nearest the right click (:meth:`WaypointOwnerMixin.delete_closest_waypoint`).

The registry here maps a waypoint's point id to the layout object at it, so the owner finds the object the existing drag and
delete logic works on.
"""

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

import weakref

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...geometry import point as _point


# How much bigger than the wire (bundle, cable) a waypoint's drag handle, and the preview of one being placed, is: easy to see and to hit.
HANDLE_SCALE = 1.25

# point id -> the layout view object at that point
_LAYOUTS: "weakref.WeakValueDictionary[bytes, object]" = weakref.WeakValueDictionary()

# True while the preview of a waypoint being placed is built: that layout object gets the sphere it is drawn as
_PREVIEW_GEOMETRY = False


@contextmanager
def preview_geometry() -> Iterator[None]:
    """Build the layout object inside this block WITH geometry: the preview sphere of a waypoint being placed."""
    global _PREVIEW_GEOMETRY

    _PREVIEW_GEOMETRY = True

    try:
        yield
    finally:
        _PREVIEW_GEOMETRY = False


def wants_preview_geometry() -> bool:
    """Whether the layout object being built is the preview of a waypoint being placed."""
    return _PREVIEW_GEOMETRY


def register(layout: object) -> None:
    """Record *layout* (a layout view object with a position) as the layout at its point."""
    _LAYOUTS[layout._position.db_id] = layout  # NOQA


def layout_for(point_id: bytes) -> object | None:
    """The layout view object at the point *point_id*, ``None`` when the waypoint has none (a cable's)."""
    return _LAYOUTS.get(point_id)


class WaypointOwnerMixin:
    """For an object with a route (wire, bundle, cable): its waypoints are its drag handles while it is selected. The class using it has
    ``_waypoint_points`` (the live waypoint Points, kept by ``_bind_waypoints``), ``is_selected``, ``_scale``, ``_curve_chords`` (``TubeMixin``),
    ``_mouse_ray`` and ``_make_waypoint_drag`` (its view's ``WireTypeMixin``), and calls :meth:`_handle_waypoint_drag` and
    :meth:`_arm_waypoint_drag` from ``handle_interaction`` and :meth:`_handle_hit` from ``hit_test_step3``."""

    # True from the press that armed a waypoint drag until its release
    _waypoint_drag: bool = False

    @_check_types.do
    def _handle_centers(self) -> list[np.ndarray]:
        """Where each waypoint's handle is: the point of the drawn path (rounded corners) nearest the waypoint, since the tube passes
        inside the corner (a bend of 90 degrees by 0.4 of a diameter, 150 degrees by 2.9) and a handle at the waypoint would float
        beside it."""
        vertices = [point.as_numpy.astype(np.float64) for point in self._waypoint_points]
        chords = self._curve_chords()

        if not chords or not vertices:
            return vertices

        starts = np.array([chord[0] for chord in chords])
        ends = np.array([chord[1] for chord in chords])
        along = ends - starts
        lengths_sq = np.maximum((along * along).sum(axis=1), 1e-12)

        centers = []

        for vertex in vertices:
            t = np.clip(((vertex - starts) * along).sum(axis=1) / lengths_sq, 0.0, 1.0)
            nearest = starts + along * t[:, None]
            best = int(((nearest - vertex) ** 2).sum(axis=1).argmin())
            centers.append(nearest[best])

        return centers

    @_check_types.do
    def waypoint_under_ray(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> int | None:
        """The index (in ``_waypoint_points``) of the waypoint whose handle the ray passes through, the nearest along the ray; ``None``
        when it passes through none."""
        if not self._waypoint_points:
            return None

        radius_sq = (HANDLE_SCALE * float(self._scale.x) * 0.5) ** 2
        best = None
        best_along = None

        for index, center in enumerate(self._handle_centers()):
            to_center = center - ray_origin
            along = float(np.dot(to_center, ray_direction))

            if along < 0.0:
                continue

            miss_sq = float(np.dot(to_center, to_center)) - along * along

            if miss_sq <= radius_sq and (best_along is None or along < best_along):
                best_along = along
                best = index

        return best

    def _handle_hit(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> bool:
        """Whether the ray passes through a waypoint handle of this object while it is selected (``hit_test_step3`` answers this when
        the ray misses the tube). Per pick, so not wrapped in ``check_types.do``."""
        if not self.is_selected or not self._waypoint_points:
            return False

        return self.waypoint_under_ray(ray_origin, ray_direction) is not None

    @_check_types.do
    def _arm_waypoint_drag(self, mouse_pos: "_point.Point") -> bool:
        """A press at *mouse_pos* on a waypoint handle of this selected object arms that waypoint's drag (the same for a wire, a bundle
        and a cable) and returns True, the object staying selected. False when the press is on no handle, or on a waypoint that cannot
        be dragged (a terminal's back point, a guard): the ordinary drag of the object then runs, which leaves those where they are."""
        if not self.is_selected:
            return False

        ray_origin, ray_direction = self._mouse_ray(mouse_pos)

        if ray_origin is None:
            return False

        index = self.waypoint_under_ray(ray_origin, ray_direction)

        if index is None:
            return False

        handler = self._make_waypoint_drag(self._waypoint_points[index])

        if handler is None:
            return False

        self._active_handler = handler
        self._waypoint_drag = True
        return True

    @_check_types.do
    def _handle_waypoint_drag(self, last_pos: "_point.Point", current_pos: "_point.Point",
                              interaction_type: "_interaction.MouseInteraction") -> bool:
        """Forward one mouse event to the armed waypoint drag; a release ends it and, the object staying selected, never falls through to
        the default select / deselect."""
        # the drag can already be gone: deselecting the object deletes its armed handler (``BaseVar.set_selected``)
        if self._active_handler is None:
            self._waypoint_drag = False
            return False

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self._active_handler(current_pos - last_pos, current_pos)
            return True

        # A drag that is cancelled ends like one that is released: it holds a write gesture open (every database write of the
        # project is deferred while one is), so one left open would keep later moves, additions and deletions of waypoints
        # from being saved
        if interaction_type in (_interaction.MouseInteraction.LEFT_UP, _interaction.MouseInteraction.CANCEL):
            self._active_handler.delete()
            self._active_handler = None
            self._waypoint_drag = False
            return True

        return False

    @_check_types.do
    def _make_waypoint_drag(self, point: "_point.Point") -> object | None:
        """The drag handler of the waypoint at *point*, ``None`` when it cannot be dragged. Each view supplies it (its ``WireTypeMixin``)."""
        raise NotImplementedError

    @_check_types.do
    def closest_waypoint(self, mouse_pos: "_point.Point") -> int | None:
        """The index (in ``_waypoint_points``) of the waypoint nearest the ray under *mouse_pos* (viewport coordinates), judged at its
        handle on the drawn path; ``None`` when there are no waypoints or no ray."""
        if not self._waypoint_points:
            return None

        ray_origin, ray_direction = self._mouse_ray(mouse_pos)

        if ray_origin is None:
            return None

        best = None
        best_distance = None

        for index, center in enumerate(self._handle_centers()):
            miss = np.cross(center - ray_origin, ray_direction)
            distance = float(np.dot(miss, miss))

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best = index

        return best

    @_check_types.do
    def delete_closest_waypoint(self, mouse_pos: "_point.Point | None") -> None:
        """Remove the waypoint nearest *mouse_pos* (the place of the right click that opened the menu); nothing without a position. The
        wire, bundle or cable keeps the rest of its route."""
        if mouse_pos is None:
            return

        index = self.closest_waypoint(mouse_pos)

        if index is not None:
            self._delete_waypoint(self._waypoint_points[index])

    @_check_types.do
    def _delete_waypoint(self, point: "_point.Point") -> None:
        """Remove one waypoint of the route: by deleting the layout at it (which takes it out of the route, renumbers the rest and has the
        owner refresh). A cable, which has no layouts, removes the point from its route itself."""
        layout = layout_for(point.db_id)

        if layout is None:
            raise RuntimeError('a waypoint of this route has no layout to delete')

        # a waypoint that cannot be dragged (a terminal's or cavity's routing point, one shared with a boot or a transition) is not
        # this route's to delete
        if not layout.can_drag():
            return

        layout.parent.delete()
