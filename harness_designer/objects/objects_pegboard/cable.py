# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The peg-board view of a placed cable (``TWISTED_WIRE_DESIGN.md`` section 8a, step 8).

A cable's trunk is drawn on the board as a wire is, so this subclasses the peg-board wire view and reuses all of it: the path
through the cable's own peg-board waypoints, the mitred bends, the picking. What differs is small:

* it is drawn at the cable's trunk size (a ribbon is its width by its thickness, any other cable round), in the jacket colour
  (for a twisted or ribbon cable, which has none, the colour of its first conductor), with no stripe;
* its ends are always free (the facade has no sibling), so a wire's crimp-end look never shows;
* the trunk is drawn only between the split planes, the conductors leaving it as the cable's leads (ordinary wires);
* it is not tied to the slack handler: nothing is attached to a cable, so there is nothing to pull or bow, and its length is the
  3D length by construction (:meth:`Cable.seed_from_3d`);
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


@_check_types.do
def _trimmed(segments: list[tuple[np.ndarray, np.ndarray]], start_split: float,
             stop_split: float) -> list[tuple[np.ndarray, np.ndarray]]:
    """The trunk's path between the split planes: the first segment starts *start_split* mm along it and the last ends
    *stop_split* mm before its end.

    :param segments: The path, as ``(p1, p2)`` pairs.
    :param start_split: Mm from the start end; 0 for none.
    :param stop_split: Mm from the stop end; 0 for none.
    """
    segments = list(segments)

    if not segments:
        return segments

    if start_split > 0.0:
        p1, p2 = segments[0]
        vector = p2 - p1
        length = float(np.linalg.norm(vector))

        if length > start_split + 1e-6:
            segments[0] = (p1 + vector / length * start_split, p2)

    if stop_split > 0.0:
        p1, p2 = segments[-1]
        vector = p2 - p1
        length = float(np.linalg.norm(vector))

        if length > stop_split + 1e-6:
            segments[-1] = (p1, p2 - vector / length * stop_split)

    return segments


@capturable()
class Cable(_wire_pegboard.Wire):
    """The peg-board view of a placed cable."""

    parent: "_cable.Cable" = None
    db_obj: "_pjt_cable.PJTCable" = None

    _uses_stripe = False

    _start_split: float = 0.0
    _stop_split: float = 0.0

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
        self.pegboard.Refresh()

    @_check_types.do
    def reload_splits(self) -> None:
        """Read the split distances again after a split or a join: the trunk is drawn between the split planes."""
        self._start_split = float(self.db_obj.start_split_mm)
        self._stop_split = float(self.db_obj.stop_split_mm)

        self._recalculate_geometry()
        self.pegboard.Refresh()

    @_check_types.do
    def _raw_segments(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """The whole path from the start to the stop, whatever is split."""
        return list(super()._segments())

    @_check_types.do
    def _segments(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """The trunk's path: as the wire's, but between the split planes."""
        return _trimmed(self._raw_segments(), self._start_split, self._stop_split)

    @_check_types.do
    def _end_frame(self, start: bool) -> _Union[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], None]:
        """The flat frame at one end of the cable: where the end is, the direction going from it into the trunk, the direction
        across the trunk (the same side for both ends of the cable) and the centre of the split plane.

        :param start: The start end (True) or the stop end (False).
        :returns: ``(end, inward, lateral, plane)``; ``None`` while the end segment has no length on the board.
        """
        segments = self._raw_segments()

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
        end = np.array([end[0], 0.0, end[2]], dtype=np.float64)

        return end, inward, lateral, end + inward * split

    @_check_types.do
    def _spacings(self, count: int) -> tuple[float, float]:
        """How far apart the conductors sit across the trunk at the split plane, and how far apart their ends land: the
        trunk's width shared out, and for any cable but a ribbon (whose conductors tear off the web side by side) that
        spread out by :data:`~harness_designer.objects.objects_3d.cable.FAN_SPREAD`.

        :param count: How many conductors (and the shield) there are.
        """
        inner = float(self._part.trunk_size[0]) / max(1, count)
        outer = inner if self._part.is_ribbon else inner * _cable_3d.FAN_SPREAD

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
        inner, _outer = self._spacings(count)

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
        _inner, outer = self._spacings(count)

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
    def refresh_waypoints(self) -> None:
        """Call after the cable's own waypoint rows change so the live callbacks, the cached length and the geometry catch
        up. As the wire's, without the slack handler (which a cable does not have)."""
        self._bind_waypoints()
        self._recalculate_geometry()
        self.pegboard.Refresh()

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
        """Do nothing, so that a click falls through to the default select / deselect. A cable is not placed on the board
        (it is placed in 3D and seeded), and dragging a placed one is not built: the wire's drag plans assume a wire.

        :returns: False.
        """
        return False


class CableMenu(_cable_3d.CableMenu):
    """The context menu of a cable on the peg board: the 3D one without the roll."""

    _has_roll = False

    @_check_types.do
    def _click_world(self) -> _Union[np.ndarray, None]:
        """Where the right click was, on the board (``None`` when the menu was opened some other way). The click is kept as
        a screen position."""
        click_pos = self.selected._context_menu_click_pos  # NOQA

        if click_pos is None:
            return None

        return self.selected.pegboard.editor.camera.screen_to_world(click_pos).as_numpy
