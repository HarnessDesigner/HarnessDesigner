# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The peg-board view of a placed cable (``TWISTED_WIRE_DESIGN.md`` section 8a, step 8).

A cable's trunk is drawn on the board as a wire is, so this subclasses the peg-board wire view and reuses all of it: the path
through the cable's own peg-board waypoints, the mitred bends, the picking. What differs is small:

* it is drawn at the cable's trunk size (a ribbon is its width by its thickness, any other cable round), in the jacket colour
  (for a twisted or ribbon cable, which has none, the colour of its first conductor), with no stripe;
* its ends are always free (the facade has no sibling), so a wire's crimp-end look never shows;
* a split end of the cable lies at the split plane, the conductors leaving it as the cable's leads (ordinary wires);
* its length is the 3D length: it starts that way (:meth:`Cable.seed_from_3d`) and the cable's slack handler keeps it so (the rope-pull
  solver treats the cable as a chain: the far end is pulled when the near one is dragged too far, slack is bowed in when the ends are
  closer);
* a click on it only selects it: dragging a placed cable is not built (in 3D either).

A cable is placed in the 3D editor, as a bundle is, and seeded into the board afterwards: the 3D route is unfolded into the board
plane with every segment keeping its real length, so the cable's length on the board is exactly its length in 3D. Where its
conductors leave the trunk, and where their ends land, is worked out here on the board's flat plane (:meth:`split_positions`,
:meth:`fan_out_positions`): the conductors sit side by side across the trunk at the split plane and spread out across the cable's
true end.
"""

from typing import TYPE_CHECKING, Union as _Union

import numpy as np

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import twisted_wire as _twisted_wire
from ...database import id_generator as _id_generator
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ..objects_3d import cable as _cable_3d
from . import wire as _wire_pegboard
from ... import check_types as _check_types
from ...crash_dump import capturable


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from .. import cable as _cable
    from ...database.project_db import pjt_cable as _pjt_cable
    from ...ui.editor_pegboard import editor_pegboard as _editor_pegboard


@capturable()
class Cable(_wire_pegboard.Wire):
    """The peg-board view of a placed cable."""

    parent: "_cable.Cable" = None
    db_obj: "_pjt_cable.PJTCable" = None

    _uses_stripe = False

    _start_split: float = 0.0
    _stop_split: float = 0.0

    # a ribbon cable: its segments with its flat side in their angle (cleared by _recalculate_geometry)
    _ribbon: bool = False
    _rolled: list = None

    # a ribbon's look is the 3D view's: a row of touching round conductors through the same shader at rate 0
    _build_ribbon = _cable_3d.Cable._build_ribbon

    @_check_types.do
    def _make_look(self, diameter: float) -> object:
        """The look of the cable's conductors, as the 3D view draws them: a twisted pair / triple as a wire's, a ribbon as a row
        of conductors, any other cable ``None`` (one plain tube in the jacket colour).

        :param diameter: The cable's diameter, mm.
        """
        if self._part.is_ribbon:
            return self._build_ribbon()

        return super()._make_look(diameter)

    @staticmethod
    @_check_types.do
    def _trunk_size(part: object) -> tuple[float, float]:
        """How wide and how thick the trunk is drawn (``Wire.trunk_size``: a ribbon is ``count * pitch`` by one pitch, any
        other cable round).

        :param part: The cable's catalog wire.
        """
        return part.trunk_size

    @_check_types.do
    def _jacket_color(self, part: object) -> object:
        """The jacket's colour; for a cable with none (a twisted or ribbon cable has the "no color" jacket) the colour of its
        first conductor, else the part's own.

        :param part: The cable's catalog wire.
        """
        if part.color_id == _id_generator.NO_COLOR_UUID.bytes:
            conductors = part.conductors

            if conductors:
                return conductors[0].color.ui

        return part.color.ui

    @_check_types.do
    def reload_look(self) -> None:
        """Draw the trunk again after the part's colours were edited (they are the catalog's, so the change is global)."""
        self._material = _materials.Plastic(self._jacket_color(self._part))
        self._ribbon = False
        self._twist = self._make_look(self._trunk_size(self._part)[0])
        self._recalculate_geometry()
        self.pegboard.Refresh()

    @_check_types.do
    def _recalculate_geometry(self) -> None:
        """As the wire's; a ribbon's flat side is worked out again with the path."""
        self._rolled = None
        super()._recalculate_geometry()

    @_check_types.do
    def _segment_transforms(self):
        """As the wire's; for a ribbon each segment's angle is turned about its direction so that the flat side keeps its
        direction round every bend (parallel transport), as in the 3D view. On the board every bend is in the board's plane, so
        the strip lies flat on it with its width across the path, which is how a ribbon cable is laid out on a board.
        """
        if not self._ribbon:
            yield from super()._segment_transforms()
            return

        if self._rolled is None:
            self._rolled = self._carry_flat_side(list(super()._segment_transforms()))

        yield from self._rolled

    @_check_types.do
    def _carry_flat_side(self, segments: list[tuple]) -> list[tuple]:
        """The wire's segments with the angle of each turned by the ribbon's twist phase there (no roll: the strip lies flat).

        :param segments: ``(position, angle, scale, length)`` per segment as the wire view yields them.
        """
        if not segments:
            return []

        rotations = [angle.as_matrix_numpy for _position, angle, _scale, _length in segments]
        lengths = [length for _position, _angle_, _scale, length in segments]
        twists = _twisted_wire.plan(rotations, lengths, self._segment_joins(segments), 0.0, self._twist.outer_radius, 0.0)
        result = []

        for (position, angle, scale, length), rotation, twist in zip(segments, rotations, twists):
            if twist.phase != 0.0:
                angle = _angle.Angle.from_matrix(_twisted_wire.rolled(rotation, twist.phase))

            result.append((position, angle, scale, length))

        return result

    @_check_types.do
    def _update_position(self, _: _Union[_point.Point, None]) -> None:
        """As the wire's, then keep the board's split points of a split end on the trunk's split plane (see the 3D view)."""
        super()._update_position(_)
        self.parent.sync_board_split_ends()

    @_check_types.do
    def reload_splits(self) -> None:
        """Read the split distances again after a split or a join: a split end lies at the split plane, and the distance is how far
        beyond it the end was before the split."""
        self._start_split = float(self.db_obj.start_split_mm)
        self._stop_split = float(self.db_obj.stop_split_mm)

        self._recalculate_geometry()
        self.pegboard.Refresh()

    @_check_types.do
    def _end_frame(self, start: bool) -> _Union[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], None]:
        """The flat frame at one end of the cable: where the cable's true end is (the split distance beyond the end it has now, when
        the end is split), the direction going from it into the trunk, the direction across the trunk (the same side for both ends
        of the cable) and the centre of the split plane (the end the cable has now).

        :param start: The start end (True) or the stop end (False).
        :returns: ``(end, inward, lateral, plane)``; ``None`` while the end segment has no length on the board.
        """
        segments = list(self._segments())

        if not segments:
            return None

        if start:
            p1, p2 = segments[0]
            end = p1
        else:
            p1, p2 = segments[-1]
            end = p2

        forward = np.array([p2[0] - p1[0], 0.0, p2[2] - p1[2]], dtype=np.float64)
        length = float(np.linalg.norm(forward))

        if length < 1e-9:
            return None

        forward /= length
        lateral = np.array([-forward[2], 0.0, forward[0]], dtype=np.float64)
        inward = forward if start else -forward
        split = self._start_split if start else self._stop_split
        plane = np.array([end[0], 0.0, end[2]], dtype=np.float64)

        return plane - inward * split, inward, lateral, plane

    @_check_types.do
    def _spacings(self, count: int, split: float) -> tuple[float, float]:
        """How far apart the conductors sit across the trunk at the split plane, and how far apart their ends land: the trunk's
        width shared out, and that projected onto the cable's true end, *split* mm beyond the plane, from a light behind it
        (:func:`~harness_designer.objects.objects_3d.cable.fan_scale`, as in 3D).

        :param count: How many conductors (and the shield) there are.
        :param split: The distance from the split plane to the cable's true end, mm.
        """
        inner = float(self._part.trunk_size[0]) / max(1, count)
        outer = inner * _cable_3d.fan_scale((count - 1) / 2.0 * inner, split)

        return inner, outer

    @_check_types.do
    def split_positions(self, start: bool) -> list[np.ndarray]:
        """Where each conductor leaves the trunk at the split plane of one end: side by side across the trunk, in conductor
        order (shield last). Only meaningful while that end is split.

        :param start: The start end (True) or the stop end (False).
        """
        frame = self._end_frame(start)
        count = len(self.db_obj.conductors)

        if frame is None or not count:
            return []

        _end, _inward, lateral, plane = frame
        inner, _outer = self._spacings(count, 0.0)

        return [plane + lateral * ((index - (count - 1) / 2.0) * inner) for index in range(count)]

    @_check_types.do
    def fan_out_positions(self, start: bool) -> list[np.ndarray]:
        """Where each conductor's end lands when one end of the cable is split: across the cable's true end, in conductor
        order (shield last). The places are fixed (one per conductor row, side by side); which conductor takes which is its
        ``start_order`` / ``stop_order`` (by default its ``idx``, so each lands straight out from where it sits).

        :param start: The start end (True) or the stop end (False).
        """
        frame = self._end_frame(start)
        conductors = self.db_obj.conductors
        count = len(conductors)

        if frame is None or not count:
            return []

        end, _inward, lateral, _plane = frame

        split = self._start_split
        if not start:
            split = self._stop_split

        _inner, outer = self._spacings(count, split)

        places = [end + lateral * ((index - (count - 1) / 2.0) * outer) for index in range(count)]
        orders = [conductor.start_order if start else conductor.stop_order for conductor in conductors]

        # an order that is not a permutation of the places is ignored rather than guessed at
        if sorted(orders) == list(range(count)):
            return [places[order] for order in orders]

        return places

    @_check_types.do
    def needs_seed(self) -> bool:
        """Whether the cable has no presence on the board yet: it has a length in 3D, none of its own peg-board waypoints and
        both its ends on the same spot (a cable placed before the peg board knew cables, or a fresh one)."""
        db_obj = self.db_obj

        if db_obj.length_mm < 0.001 or db_obj.waypoints_pegboard:
            return False

        return bool(np.allclose(self.start_position.as_numpy, self.stop_position.as_numpy))

    @_check_types.do
    def seed_from_3d(self) -> None:
        """Give the cable its presence on the board by unfolding its 3D path into the board plane: from the board start (the
        3D start's X and Z), every 3D segment is stepped out by its own REAL length along its X / Z direction (a vertical one
        keeps the previous direction, +X for the first), one board waypoint per interior 3D waypoint. The board stop is where
        the walk ends, so the cable's length on the board is exactly its length in 3D.
        """
        with self.parent._slack_handler.suspended():  # NOQA -- the route is right as a whole, not step by step
            self._seed_from_3d()

    @_check_types.do
    def _seed_from_3d(self) -> None:
        """The walk of :meth:`seed_from_3d`."""
        ptables = self.parent.mainframe.project.ptables
        db_obj = self.db_obj

        points3d = [db_obj.start_position3d, *(w.point for w in db_obj.waypoints3d), db_obj.stop_position3d]

        start = self.start_position
        first = points3d[0]
        start += _point.Point(float(first.x), 0.0, float(first.z)) - start

        current = np.array([float(start.x), 0.0, float(start.z)], dtype=np.float64)
        previous = np.array([1.0, 0.0], dtype=np.float64)
        walked = []

        for a, b in zip(points3d[:-1], points3d[1:]):
            segment = b.as_numpy - a.as_numpy
            length = float(np.linalg.norm(segment))

            if length < 1e-9:
                continue

            planar = np.array([segment[0], segment[2]], dtype=np.float64)
            planar_length = float(np.linalg.norm(planar))

            if planar_length > 1e-9:
                previous = planar / planar_length

            current = current + np.array([previous[0] * length, 0.0, previous[1] * length], dtype=np.float64)
            walked.append(current.copy())

        stop_at = walked.pop() if walked else current

        for position in walked:
            row = ptables.pjt_points_pegboard_table.insert(float(position[0]), 0.0, float(position[2]))
            ptables.pjt_cable_paths_table.append(db_obj.db_id, 'pegboard', row.db_id)

        stop = self.stop_position
        stop += _point.Point(float(stop_at[0]), 0.0, float(stop_at[2])) - stop

        self.refresh_waypoints()

    @_check_types.do
    def _delete_waypoint(self, point: _point.Point) -> None:
        """Remove one waypoint of the cable's route on the board: a cable has no layouts at its waypoints, so the point comes out of the
        route and is deleted itself, then the cable catches up."""
        ptables = self.parent.mainframe.project.ptables
        point_id = point.db_id[:-2]

        ptables.pjt_cable_paths_table.remove(self.db_obj.db_id, 'pegboard', point_id)
        ptables.pjt_points_pegboard_table[point_id].delete()

        self.refresh_waypoints()

    @_check_types.do
    def refresh_waypoints(self) -> None:
        """Call after the cable's own waypoint rows change so the live callbacks, the cached length and the geometry catch
        up. As the wire's: the slack handler is told which points to watch now."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.pegboard.Refresh()

        handler = getattr(self.parent, '_slack_handler', None)  # not there yet while the facade is still being built

        if handler is not None:
            handler.register_pegboard()

    @_check_types.do
    def get_context_menu(self) -> "CableMenu":
        """Return the context menu.

        :rtype: :class:`CableMenu`
        """
        return CableMenu(self.pegboard.editor, self)

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Drag the cable as a wire is dragged (a click and drag on the selected cable's body moves what the click is near: a
        free end, the two waypoints round the segment, or the whole cable, see ``drag_handlers.editor_pegboard.cable``); a plain
        click falls through to the default select / deselect. A cable is not placed on the board (it is placed in 3D and
        seeded), so there is no placement session here.

        :returns: Whether the interaction was handled.
        """
        from ...drag_handlers.editor_pegboard import cable as _drag_cable  # NOQA -- avoid a cycle at import time

        if self._waypoint_drag:
            return self._handle_waypoint_drag(last_pos, current_pos, interaction_type)

        handler = self._active_handler

        if handler is not None:
            if interaction_type is _interaction.MouseInteraction.MOVE:
                handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                handler.delete()
                self._active_handler = None
                # no real drag happened: let a plain click-release fall through to the default select / deselect
                return had_motion

            return False

        if (
            interaction_type is not _interaction.MouseInteraction.LEFT_DOWN or
            clicked_object is not self.parent or
            self.parent.mainframe.get_selected() is not self.parent
        ):
            return False

        # a press on one of this object's waypoint handles drags that waypoint (objects/mixins/waypoint_handles.py)
        if self._arm_waypoint_drag(current_pos):
            return True

        plan = _drag_cable.Cable.plan_wire_drag(self.parent.mainframe.project, self.parent, current_pos)

        if plan is None:
            return False

        self._active_handler = _drag_cable.Cable(self.pegboard.editor, self.parent, plan)
        return True


class CableMenu(_cable_3d.CableMenu):
    """The context menu of a cable on the peg board: the 3D one without the roll."""

    _has_roll = False
    _has_add_layout = False
    _has_sleeve = False
