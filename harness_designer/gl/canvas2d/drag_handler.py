# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Base class for editor-specific object-drag mechanics.

Long-lived: one instance per :class:`~.mouse_handler.MouseHandler`,
constructed once in its ``__init__`` (see ``MouseHandler.
_get_drag_handler``) and reused for the editor's entire lifetime -- NOT
one instance per drag the way
:class:`harness_designer.gl.canvas3d.dragging.base.DragObject` is. This
is deliberate: a subclass that needs collision or wire-routing state
(e.g. to reroute wires as a housing moves, or track a bundle's remaining
slack) can build and cache that once and keep it warm across many
separate drags, rather than paying to rebuild it from scratch every time
a drag starts, which construct-per-drag would force.

Lifecycle per drag: :meth:`can_drag` (eligibility -- e.g. the peg board's
handler rejects whatever a bundle's fixed-length rule can't accommodate),
then :meth:`begin`, then this instance is called directly with each
mouse-move delta for the duration of the drag, then :meth:`end`.

Mirrors :class:`harness_designer.gl.canvas3d.dragging.base.DragObjectBase`'s
per-frame screen-projection math as closely as it still makes sense to,
but not its per-drag construct/delete lifecycle or its dominant-axis
locking (X/Y/Z) -- that exists in 3D because a 2D screen delta is
inherently ambiguous once unprojected into free 3D space. This base
class's camera (:mod:`harness_designer.gl.canvas2d.camera`) is
permanently locked looking straight down the world Y axis under an
orthographic projection, so a screen delta already maps unambiguously to
a world X/Z delta -- there is no ambiguity left to resolve by locking
onto one axis, so that entire mechanism (``axis_lock``, the
``move_arrows`` gizmo, the settle-event jitter debounce) is dropped here
rather than carried over unused.

Not keyed to any specific object type -- *target* is whatever the
concrete ``MouseHandler``'s ``_get_view_object`` already resolved
(``obj2d``, ``objpeg``, ...), duck-typed on nothing more than what this
class itself needs (see :meth:`DragHandler._screen_delta_to_world`).
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas


class DragHandler:
    """Base class for editor-specific object-drag mechanics.

    See the module docstring for the full rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`DragHandler` instance.

        Constructed once (see the module docstring) -- a subclass adding
        its own long-lived caches (collision state, routing graphs, ...)
        should build them here, not in :meth:`begin`.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        """
        self.canvas = canvas

        # Per-drag state -- reset in begin()/end(), never touched by
        # long-lived, cross-drag subclass state set up above.
        self.target = None
        self.pick_offset = None

    @_check_types.do
    def can_drag(self, target) -> bool:
        """Return whether *target* is draggable at all by this handler.

        Must be overridden by the subclass -- e.g. rejecting whatever a
        bundle's fixed-length rule can't accommodate, or whatever a
        cavity-seated terminal shouldn't allow. Called by the
        ``MouseHandler`` before :meth:`begin`.

        :param target: The view-object under the mouse -- already
            resolved via ``MouseHandler._get_view_object``.
        :rtype: bool
        """
        raise NotImplementedError

    @_check_types.do
    def begin(self, target) -> None:
        """Start a new drag on *target* -- resets this handler's
        per-drag state (not its long-lived, cross-drag caches).

        Base implementation just records *target*; override to also
        seed whatever per-drag state the subclass's own :meth:`__call__`
        needs, calling ``super().begin(target)`` first.

        :param target: The view-object being dragged -- already resolved
            by the caller via ``MouseHandler._get_view_object``.
        """
        self.target = target
        self.pick_offset = None

    @_check_types.do
    def _screen_delta_to_world(self, anchor: _point.Point,
                               last_pos: _point.Point, delta) -> _point.Point:
        """Project *anchor* to screen space, add the raw mouse *delta*,
        and unproject back to world space -- the world-space delta to
        apply this frame.

        :param anchor: The point (in world space) this drag is currently
            tracking -- typically *target*'s own position, or a specific
            point along its path for a segment-local drag.
        :type anchor: :class:`~harness_designer.geometry.point.Point`
        :param last_pos: *anchor*'s value as of the previous call (or its
            initial value, on the first call after :meth:`begin`).
        :type last_pos: :class:`~harness_designer.geometry.point.Point`
        :param delta: Raw screen-space mouse delta for this event.
        :returns: World-space delta to apply this frame.
        :rtype: :class:`~harness_designer.geometry.point.Point`
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
    def __call__(self, delta):
        """Apply one frame's worth of mouse-move *delta* to the target
        set by :meth:`begin`.

        Must be overridden by the subclass -- what "the target's
        position" even means differs per object type (a plain object's
        whole position vs. a wire's nearest draggable segment vs. a
        bundle whose fixed length must be conserved end-to-end).

        :param delta: Raw screen-space mouse delta for this event.
        """
        raise NotImplementedError

    @_check_types.do
    def end(self) -> None:
        """End the current drag -- clears this handler's per-drag state.

        The handler instance itself is not discarded -- it stays alive
        on the ``MouseHandler`` for the next drag (see the module
        docstring). Base implementation just clears :attr:`target`/
        :attr:`pick_offset`; override to also release/undo whatever
        per-drag (not long-lived) state the subclass's own :meth:`begin`
        acquired, calling ``super().end()`` too.
        """
        self.target = None
        self.pick_offset = None
