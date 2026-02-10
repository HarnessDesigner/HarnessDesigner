from typing import Union, TYPE_CHECKING


from ...geometry import point as _point


if TYPE_CHECKING:
    from ...objects.objects3d import housing as _housing
    from ...objects.objects3d import cavity as _cavity
    from ...objects.objects3d.mixins import angle as _arrow_angle
    from ...objects.objects3d.mixins import move as _arrow_move
    from ..canvas import canvas as _canvas


class DragObject:

    def __init__(self, owner: Union["_housing.Housing", "_cavity.Cavity"],
                 obj: Union["_arrow_angle.ArrowRing", "_arrow_move.ArrowMove"],
                 anchor_screen: _point.Point, pick_offset: _point.Point,
                 mouse_start: _point.Point, start_obj_pos: _point.Point,
                 last_pos: _point.Point):
        # object that was actually clicked
        self.owner = owner

        # object to be moved
        self.obj = obj

        # (winx, winy, winz)
        self.anchor_screen = anchor_screen

        # _point.Point
        self.pick_offset = pick_offset

        # (mx,my) in top-left window coords
        self.mouse_start = mouse_start

        # last object world _point.Point used for incremental moves
        self.last_pos = last_pos

        #  _point.Point start position
        self.start_obj_pos = start_obj_pos

    def rotate(self, canvas: "_canvas.Canvas", mouse_point: _point.Point):
        pass

    def move(self, canvas: "_canvas.Canvas", mouse_point: _point.Point):
        delta = mouse_point - self.mouse_start

        # compute new anchor screen position (top-left coords)
        screen_new = self.anchor_screen + delta

        # Unproject at anchor winZ (note our unproject_point expects top-left coords)
        world_hit = canvas.unproject_point(screen_new)

        # candidate world = world_hit + pick_offset
        candidate = world_hit + self.pick_offset

        new_pos = self.owner.move(candidate, self.start_obj_pos, self.last_pos)
        self.last_pos = new_pos
