# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared screen-projection / axis-lock mechanics for every 3D-editor
drag handler.

Ported from :class:`~harness_designer.gl.canvas_3d.dragging.base.DragObjectBase`
(proven, working code from before this package existed) -- a free-orbit
3D camera makes a raw screen-space mouse delta ambiguous (it could mean
movement along any of X/Y/Z), so every 3D drag locks to whichever single
axis dominates once the first couple of events have settled past initial
click jitter, and shows a directional arrows gizmo once that lock
engages. This is the one piece of drag mechanics that's genuinely 3D-only
-- the 2D-style editors (schematic/pegboard) have an unambiguous locked
top-down projection and never need it (see
:mod:`~harness_designer.drag_handlers.editor_schematic`/
:mod:`~harness_designer.drag_handlers.editor_pegboard`).

Concrete per-object-type handlers (:mod:`~.generic`, :mod:`~.wire`,
:mod:`~.bundle`, :mod:`~.wire_marker`) each track their own notion of
"anchor" (the point projected to screen space and incrementally updated
every call) and decide what a computed world-space delta actually moves
-- this base only owns the math that's identical regardless of what's
being dragged.
"""

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import point as _point
from .. import move_arrows as _move_arrows
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas_window as _canvas_window
    from ...gl import shaders as _shaders
    from ... import objects as _objects


# Number of drag events to let pass before locking in the dominant axis.
# The first event(s) right after button-down are dominated by mouse-down
# jitter (worse on high-resolution mice), which picks the wrong axis far
# more often than a settled delta does.
_AXIS_LOCK_SETTLE_EVENTS = 2


class DragHandler3D(_base.DragHandlerBase):
    """Shared 3D screen-projection / axis-lock mechanics.

    See the module docstring for the full rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas_window.CanvasWindow", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        self.axis_lock = _point.Point(0, 0, 0)
        self.move_arrows: _move_arrows.MoveArrows | None = None

        self.pick_offset = None
        self._settle_events = 0

        # Where the mouse is now (screen space), set by a handler that wants the dragged
        # point latched to it; and where the axis lock engaged (see _axis_locked_delta3d).
        self.cursor: _point.Point | None = None
        self._lock_origin: _point.Point | None = None

        # Where the dragged point is on screen relative to the pointer when the drag begins
        # (an object grabbed by its edge is not under the pointer's exact spot): kept all
        # drag long, see _latched_delta3d.
        self._grab_offset: _point.Point | None = None

    @_check_types.do
    def _delta3d(self, anchor: _point.Point, last_pos: _point.Point, delta: _point.Point) -> _point.Point:
        """Project *anchor* to screen space, add the raw mouse *delta*,
        unproject back to world space, and return the resulting raw
        (un-locked) world-space delta this frame implies.

        Shared by :meth:`_axis_locked_delta3d` (adds the axis-lock clamp
        on top) and any 3D drag handler that needs 3D screen<->world
        projection but not axis-locking at all -- e.g. a wire marker,
        whose position is already forced onto its wire's line by the
        object's own bound callback regardless of which raw direction the
        delta points in, so there is no ambiguous axis to lock in the
        first place.
        """
        anchor_screen = self.canvas.camera.ProjectPoint(anchor)
        depth = anchor_screen.z

        screen_new = anchor_screen + delta
        screen_new.z = depth

        world_hit = self.canvas.camera.UnprojectPoint(screen_new)
        pick_world = self.canvas.camera.UnprojectPoint(anchor_screen)

        if self.pick_offset is None:
            self.pick_offset = anchor - pick_world

        world_hit += self.pick_offset

        return world_hit - last_pos

    @_check_types.do
    def _axis_locked_delta3d(self, anchor: _point.Point, last_pos: _point.Point,
                              delta: _point.Point, aabb: np.ndarray) -> _point.Point | None:
        """Return :meth:`_delta3d`'s raw world-space delta, locked to
        whichever axis dominated once the first few events have settled
        past initial click jitter -- or ``None`` while still settling, in
        which case the caller must treat this event as a no-op (leave its
        own anchor/last_pos untouched).

        *aabb* sizes the move-arrows gizmo created the moment the axis
        locks in.
        """
        self._record_grab(anchor, delta)

        delta3d = self._delta3d(anchor, last_pos, delta)

        if tuple(self.axis_lock) == (0.0, 0.0, 0.0):
            self._settle_events += 1
            if self._settle_events < _AXIS_LOCK_SETTLE_EVENTS:
                return None

            axis_values = {'x': abs(delta3d.x), 'y': abs(delta3d.y), 'z': abs(delta3d.z)}
            dominant_axis = max(axis_values, key=axis_values.get)
            if dominant_axis == 'x':
                self.axis_lock.x = 1.0
            elif dominant_axis == 'y':
                self.axis_lock.y = 1.0
            else:
                self.axis_lock.z = 1.0

            self._lock_origin = anchor.copy()
            self.move_arrows = _move_arrows.MoveArrows(
                anchor, dominant_axis, self.canvas.mainframe, aabb)

        latched = self._latched_delta3d(anchor)
        if latched is not None:
            return latched

        delta3d *= self.axis_lock
        return delta3d

    @_check_types.do
    def _latched_delta3d(self, anchor: _point.Point) -> _point.Point | None:
        """With the axis locked, the world delta that puts *anchor* on the
        locked axis line at the spot closest to the mouse ray -- so the dragged
        point stays under the pointer as far as one axis allows, instead of
        drifting away by whatever part of the mouse motion the lock discards.

        The point keeps the place on screen, relative to the pointer, that it had when
        the drag began (see :meth:`_record_grab`): an object grabbed by its edge stays
        grabbed by its edge instead of jumping its origin under the pointer.

        ``None`` when the handler gave no :attr:`cursor`, or the axis points
        along the view ray (nothing to latch to): the caller falls back to the
        plain locked delta.
        """
        if self.cursor is None or self._lock_origin is None:
            return None

        axis = np.array([self.axis_lock.x, self.axis_lock.y, self.axis_lock.z], dtype=np.float64)
        origin = self._lock_origin.as_numpy.astype(np.float64)

        distance = self._ray_distance_on_line(origin, axis)
        if distance is None:
            return None

        target = origin + axis * distance

        return _point.Point(*(target - anchor.as_numpy.astype(np.float64)))

    @_check_types.do
    def _line_latched_distance(self, origin: _point.Point, direction: np.ndarray,
                               delta: _point.Point) -> float | None:
        """For a drag that is confined to a line (a wire marker on its wire, a service loop
        slid along its wire): the signed distance, along *direction* from *origin*, to the
        spot on that line nearest the mouse ray now, the ray being taken through the place
        the dragged object keeps relative to the pointer (see :meth:`_record_grab`). Moving
        the object by it puts it under the pointer as far as the line allows; an object
        that cannot follow (it hit a stop) simply catches up when the pointer comes back,
        instead of drifting.

        :param origin: Where the dragged object is now.
        :param direction: The line's direction, any length (it is normalised here).
        :param delta: The screen move of this event.
        :returns: The distance, or ``None`` when the handler has no :attr:`cursor`, the line
            has no direction, or it points along the view ray: the caller then moves by the
            plain screen delta.
        """
        if self.cursor is None:
            return None

        self._record_grab(origin, delta)

        line_dir = np.asarray(direction, dtype=np.float64)
        length = float(np.linalg.norm(line_dir))
        if length < 1e-9:
            return None

        line_dir = line_dir / length

        return self._ray_distance_on_line(origin.as_numpy.astype(np.float64), line_dir)

    @_check_types.do
    def _record_grab(self, anchor: _point.Point, delta: _point.Point) -> None:
        """Remember, the first time it is called (the drag's first event, before anything
        has moved), where *anchor* is on screen relative to the mouse then: the cursor of
        that event less its own move is where the mouse went down. Nothing happens without
        a :attr:`cursor`.
        """
        if self._grab_offset is not None or self.cursor is None:
            return

        grab_cursor = self.cursor - delta
        anchor_screen = self.canvas.camera.ProjectPoint(anchor)

        if anchor_screen is None:
            self._grab_offset = _point.Point(0.0, 0.0, 0.0)
            return

        self._grab_offset = _point.Point(
            anchor_screen.x - grab_cursor.x, anchor_screen.y - grab_cursor.y, 0.0)

    @_check_types.do
    def _ray_distance_on_line(self, origin: np.ndarray, direction: np.ndarray) -> float | None:
        """The distance, along the unit *direction* from *origin*, of the spot on that line
        nearest the mouse ray now -- the ray through the cursor moved by the grab offset, so
        it is the ray the dragged point itself should lie on. ``None`` when that ray runs
        along the line, or there is none.
        """
        screen = _point.Point(self.cursor.x, self.cursor.y, 0.0)
        if self._grab_offset is not None:
            screen = _point.Point(
                self.cursor.x + self._grab_offset.x, self.cursor.y + self._grab_offset.y, 0.0)

        ray_origin, ray_dir = self.canvas.camera.get_mouse_ray(screen)
        if ray_origin is None:
            return None

        w0 = origin - np.asarray(ray_origin, dtype=np.float64)
        ray_dir = np.asarray(ray_dir, dtype=np.float64)

        b = float(np.dot(direction, ray_dir))
        d = float(np.dot(direction, w0))
        e = float(np.dot(ray_dir, w0))
        denom = 1.0 - b * b
        if denom < 1e-6:
            return None

        return (b * e - d) / denom

    @_check_types.do
    def delete(self) -> None:
        if self.move_arrows is not None:
            self.move_arrows.delete()

        self.move_arrows = None

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Render the move-arrows gizmo, if the axis lock has engaged
        and built one yet -- called via ``BaseVar.render_handler()``,
        not registered as its own scene object (see move_arrows.py's
        own docstring for why).
        """
        if self.move_arrows is None:
            return

        self.move_arrows.obj3d.render(shaders)
