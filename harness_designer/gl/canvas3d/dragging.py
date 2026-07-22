# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...geometry import line as _line
from ... import debug as _debug
from . import move_arrows as _move_arrows


if TYPE_CHECKING:
    from . import canvas as _canvas
    from ... import objects as _objects
    from ...objects import wire as _wire_object


# Number of drag events to let pass before locking in the dominant axis.
# The first event(s) right after button-down are dominated by mouse-down
# jitter (worse on high-resolution mice), which picks the wrong axis far
# more often than a settled delta does.
_AXIS_LOCK_SETTLE_EVENTS = 2


class DragObject:
    """Represent a drag object in :mod:`harness_designer.gl.canvas3d.dragging`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas: "_canvas.Canvas", selected: "_objects.ObjectBase"):
        """Initialise the :class:`DragObject` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        :param selected: Value for ``selected``.
        :type selected: :class:`_objects.ObjectBase`
        """
        self.canvas = canvas
        self.selected = selected

        # last object world _point.Point used for incremental moves
        self.last_pos = selected.obj3d.position.copy()
        self.axis_lock = _point.Point(0, 0, 0)
        self.move_arrows: _move_arrows.MoveArrows = None

        self.pick_offset = None
        self._settle_events = 0

        # Duck-typed: only WireServiceLoop 3D defines this (see its own
        # begin_move_session docstring) -- caches its collision-candidate
        # list for the whole drag instead of rebuilding it on every one of
        # the many position updates a drag produces.
        if hasattr(selected.obj3d, 'begin_move_session'):
            selected.obj3d.begin_move_session()

    def delete(self):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if hasattr(self.selected.obj3d, 'end_move_session'):
            self.selected.obj3d.end_move_session()

        if self.move_arrows is not None:
            self.move_arrows.delete()

        self.move_arrows = None

    @_debug.logfunc
    def __call__(self, delta):
        """Call the instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """
        # Step 1: Project object position to screen space
        anchor_screen = self.canvas.camera.ProjectPoint(self.selected.obj3d.position)
        # Step 2: Use object's anchor_screen.z as the depth reference
        depth = anchor_screen.z  # Preserve screen depth for unprojecting screen_new

        # Step 3: Compute new screen position with delta (mouse movement)
        screen_new = anchor_screen + delta
        screen_new.z = depth  # Ensure consistent depth

        # Step 4: Unproject the screen position back to world space
        world_hit = self.canvas.camera.UnprojectPoint(screen_new)

        # Step 5: Apply offset to maintain object position relative to pick point
        pick_world = self.canvas.camera.UnprojectPoint(anchor_screen)

        if self.pick_offset is None:
            self.pick_offset = self.selected.obj3d.position - pick_world

        world_hit += self.pick_offset

        # Step 6: Calculate delta in world space
        delta3d = world_hit - self.last_pos

        # Step 7: Determine the dominant axis to lock movement (axis_lock).
        # Hold off on locking for the first few events -- last_pos is left
        # untouched below while settling, so delta3d naturally accumulates
        # into the net movement since the drag started rather than reacting
        # to a single (possibly jittery) event.
        if tuple(self.axis_lock) == (0.0, 0.0, 0.0):
            self._settle_events += 1
            if self._settle_events < _AXIS_LOCK_SETTLE_EVENTS:
                return

            axis_values = {'x': abs(delta3d.x), 'y': abs(delta3d.y), 'z': abs(delta3d.z)}
            dominant_axis = max(axis_values, key=axis_values.get)
            setattr(self.axis_lock, dominant_axis, 1.0)

            # Create movement arrows when the axis is first determined
            self.move_arrows = _move_arrows.MoveArrows(self.selected.obj3d.position, dominant_axis,
                                                       self.canvas.mainframe, self.selected.obj3d.aabb)

        # Step 8: Apply axis locking
        delta3d *= self.axis_lock

        # Step 9: Update the object's position
        position = self.selected.obj3d.position

        position += delta3d

        # Step 10: Update the last position for the next drag
        self.last_pos = position.copy()


class WireDragObject:
    """Rigid-translate drag for a Wire: moves both endpoints together by
    the same world-space delta, anchored on the wire's midpoint.

    A plain :class:`DragObject` can't be used for a wire -- it drags
    ``obj3d.position``, which for a Wire is only the start endpoint (see
    objects3d.wire.Wire.__init__), leaving the stop endpoint behind.

    Only ever constructed for a wire where
    ``obj3d.is_housing_attached()`` is False (see mouse_handler.py) -- a
    housing-attached wire's position is derived from its housing, not
    freely draggable.
    """

    def __init__(self, canvas: "_canvas.Canvas", selected: "_wire_object.Wire"):
        self.canvas = canvas
        self.selected = selected

        obj3d = selected.obj3d
        line = _line.Line(obj3d.start_position, obj3d.stop_position)
        # A fresh, unregistered Point (no db_id) -- purely a local
        # screen-projection anchor, tracked incrementally below exactly
        # like DragObject.last_pos, never itself persisted.
        self._anchor = line.point_from_start(line.length() / 2.0)

        self.last_pos = self._anchor.copy()
        self.axis_lock = _point.Point(0, 0, 0)
        self.move_arrows: _move_arrows.MoveArrows = None

        self.pick_offset = None
        self._settle_events = 0

    def delete(self):
        if self.move_arrows is not None:
            self.move_arrows.delete()

        self.move_arrows = None

    @_debug.logfunc
    def __call__(self, delta):
        anchor_screen = self.canvas.camera.ProjectPoint(self._anchor)
        depth = anchor_screen.z

        screen_new = anchor_screen + delta
        screen_new.z = depth

        world_hit = self.canvas.camera.UnprojectPoint(screen_new)
        pick_world = self.canvas.camera.UnprojectPoint(anchor_screen)

        if self.pick_offset is None:
            self.pick_offset = self._anchor - pick_world

        world_hit += self.pick_offset

        delta3d = world_hit - self.last_pos

        if tuple(self.axis_lock) == (0.0, 0.0, 0.0):
            self._settle_events += 1
            if self._settle_events < _AXIS_LOCK_SETTLE_EVENTS:
                return

            axis_values = {'x': abs(delta3d.x), 'y': abs(delta3d.y), 'z': abs(delta3d.z)}
            dominant_axis = max(axis_values, key=axis_values.get)
            setattr(self.axis_lock, dominant_axis, 1.0)

            self.move_arrows = _move_arrows.MoveArrows(
                self._anchor, dominant_axis, self.canvas.mainframe, self.selected.obj3d.aabb)

        delta3d *= self.axis_lock

        obj3d = self.selected.obj3d

        start_position = obj3d.start_position
        stop_position = obj3d.stop_position

        start_position += delta3d
        stop_position += delta3d

        self._anchor += delta3d
        self.last_pos = self._anchor.copy()
