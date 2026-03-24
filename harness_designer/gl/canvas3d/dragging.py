from typing import TYPE_CHECKING


from ...geometry import point as _point
from ... import debug as _debug
from ...objects.objects3d import move_arrows as _move_arrows

if TYPE_CHECKING:
    from . import canvas as _canvas
    from ... import objects as _objects


class DragObject:

    def __init__(self, canvas: "_canvas.Canvas", selected: "_objects.ObjectBase"):
        self.canvas = canvas
        self.selected = selected

        # last object world _point.Point used for incremental moves
        self.last_pos = selected.obj3d.position.copy()
        self.axis_lock = _point.Point(0, 0, 0)

        self.pick_offset = None
        self.move_arrows = None

    @_debug.logfunc
    def __call__(self, delta):
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

        # Step 7: Determine the dominant axis to lock movement (axis_lock)
        if tuple(self.axis_lock) == (0.0, 0.0, 0.0):
            axis_values = {'x': abs(delta3d.x), 'y': abs(delta3d.y), 'z': abs(delta3d.z)}
            dominant_axis = max(axis_values, key=axis_values.get)
            setattr(self.axis_lock, dominant_axis, 1.0)

            # Create movement arrows when the axis is first determined
            if self.move_arrows is None:
                self.move_arrows = _move_arrows.MoveArrows(
                    self.selected.obj3d.position,
                    dominant_axis,
                    self.canvas.mainframe,
                    self.selected.obj3d.aabb
                )

        # Step 8: Apply axis locking
        delta3d *= self.axis_lock

        # Step 9: Update the object's position
        position = self.selected.obj3d.position

        position += delta3d

        # Step 10: Update the last position for the next drag
        self.last_pos = position.copy()


