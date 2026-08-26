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

from ...geometry import point as _point
from .. import move_arrows as _move_arrows
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
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
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        self.axis_lock = _point.Point(0, 0, 0)
        self.move_arrows: _move_arrows.MoveArrows | None = None

        self.pick_offset = None
        self._settle_events = 0

    @_check_types.do
    def _delta3d(self, anchor: _point.Point, last_pos: _point.Point, delta) -> _point.Point:
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
                              delta, aabb):
        """Return :meth:`_delta3d`'s raw world-space delta, locked to
        whichever axis dominated once the first few events have settled
        past initial click jitter -- or ``None`` while still settling, in
        which case the caller must treat this event as a no-op (leave its
        own anchor/last_pos untouched).

        *aabb* sizes the move-arrows gizmo created the moment the axis
        locks in.
        """
        delta3d = self._delta3d(anchor, last_pos, delta)

        if tuple(self.axis_lock) == (0.0, 0.0, 0.0):
            self._settle_events += 1
            if self._settle_events < _AXIS_LOCK_SETTLE_EVENTS:
                return None

            axis_values = {'x': abs(delta3d.x), 'y': abs(delta3d.y), 'z': abs(delta3d.z)}
            dominant_axis = max(axis_values, key=axis_values.get)
            setattr(self.axis_lock, dominant_axis, 1.0)

            self.move_arrows = _move_arrows.MoveArrows(
                anchor, dominant_axis, self.canvas.mainframe, aabb)

        delta3d *= self.axis_lock
        return delta3d

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
