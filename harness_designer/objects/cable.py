# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A placed cable: a shielded wire or one with more than one conductor.

The cable is what is placed, routed, selected and listed once in the bill of materials; its conductors
(:mod:`~harness_designer.database.project_db.pjt_cable_conductor`) are what a circuit contains. It has a 3D view and a
peg-board view (placed in 3D and seeded onto the board, :meth:`~harness_designer.objects.objects_pegboard.cable.Cable.
seed_from_3d`) and is never drawn in the schematic (each conductor is, as its own wire). A cable's two ends are always free: a
terminal or splice is attached to a conductor, after the cable is split. See ``TWISTED_WIRE_DESIGN.md`` section 8a in the repo
root.
"""

from typing import TYPE_CHECKING

import numpy as np

from . import ObjectBase as _ObjectBase
from . import cable_conductor as _cable_conductor
from ..geometry import point as _point
from .objects_3d import cable as _cable_3d
from .objects_pegboard import cable as _cable_pegboard
from .. import check_types as _check_types
from ..crash_dump import capturable


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cable as _pjt_cable
    from ..database.project_db import pjt_cable_conductor as _pjt_cable_conductor
    from . import wire as _wire


@capturable()
class Cable(_ObjectBase):
    """A placed cable."""
    obj3d: _cable_3d.Cable = None
    objpegboard: _cable_pegboard.Cable = None
    db_obj: "_pjt_cable.PJTCable" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_pjt_cable.PJTCable", project_load: bool = False):
        """Initialise the :class:`Cable` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: The cable's row.
        :type db_obj: :class:`_pjt_cable.PJTCable`
        :param project_load: Whether the cable is being built as its project loads.
        :type project_load: bool
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj3d = _cable_3d.Cable(self, db_obj)
        self.objpegboard = _cable_pegboard.Cable(self, db_obj)

        # A conductor's end points follow the cable's (they are children of them), but only once their live Point
        # objects exist: that is what binds the follow callback. A cable still being placed has no conductors yet.
        for conductor in db_obj.conductors:
            conductor.start_position3d  # NOQA
            conductor.stop_position3d  # NOQA

        # The junction object of each conductor (see :meth:`conductor_object`), made when first asked for.
        self._conductor_objects: dict[bytes, _cable_conductor.CableConductor] = {}

        # The drawn-only markers where the leads of a split end meet the trunk, per end (see :meth:`_make_split_markers`).
        self._split_markers: dict[bool, list] = {True: [], False: []}

        if db_obj.start_split_mm > 0.0 or db_obj.stop_split_mm > 0.0:
            self.obj3d.reload_splits()
            self.objpegboard.reload_splits()

            for split_start in (True, False):
                if self.is_split(split_start):
                    self._make_split_markers(split_start)
        elif project_load and self.objpegboard.needs_seed():
            # a cable placed before the board knew cables: give it the board presence a new one gets when it is placed
            self.objpegboard.seed_from_3d()

        self.mainframe.add_object(self)

    @_check_types.do
    def conductor_object(self, conductor: "_pjt_cable_conductor.PJTCableConductor") -> "_cable_conductor.CableConductor":
        """The junction object of one conductor, made the first time it is asked for.

        :param conductor: The conductor's row.
        :type conductor: :class:`_pjt_cable_conductor.PJTCableConductor`
        :rtype: :class:`_cable_conductor.CableConductor`
        """
        node = self._conductor_objects.get(conductor.db_id)

        if node is None:
            node = _cable_conductor.CableConductor(self.mainframe, conductor, self)
            self._conductor_objects[conductor.db_id] = node
            conductor.set_object(node)

        return node

    @_check_types.do
    def reload_looks(self) -> None:
        """Draw the trunk and every lead again, after a conductor's colour was edited or the conductors were made."""
        self.obj3d.reload_look()
        self.objpegboard.reload_look()

        for node in self._conductor_objects.values():
            for lead in node.wires:
                lead.obj3d.reload_conductor_colors()
                lead.objpegboard.reload_conductor_colors()

    @_check_types.do
    def refresh_browser(self) -> None:
        """Make the object browser list the cable's conductors and leads as they are now (after the conductors were made, or
        an end was split or joined)."""
        self.mainframe.object_browser.refresh_cable(self)

    @_check_types.do
    def conductors_made(self) -> None:
        """The placement session has made the cable's conductor rows: draw their colours and list them in the browser."""
        self.reload_looks()
        self.refresh_browser()

    @_check_types.do
    def drawn_conductor_objects(self) -> list["_cable_conductor.CableConductor"]:
        """The junction objects made so far (a conductor drawn in the schematic has one), without making the rest.

        :rtype: list[:class:`_cable_conductor.CableConductor`]
        """
        return list(self._conductor_objects.values())

    @property
    @_check_types.do
    def conductor_objects(self) -> list["_cable_conductor.CableConductor"]:
        """The junction objects of the cable's conductors, in conductor order.

        :rtype: list[:class:`_cable_conductor.CableConductor`]
        """
        return [self.conductor_object(conductor) for conductor in self.db_obj.conductors]

    @_check_types.do
    def is_split(self, start: bool) -> bool:
        """Whether the conductors have been split out of the cable at its start (True) or stop (False) end.

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        if start:
            return self.db_obj.start_split_mm > 0.0

        return self.db_obj.stop_split_mm > 0.0

    @_check_types.do
    def max_split_mm(self, start: bool) -> float:
        """The furthest from the end that the conductors can leave the cable: the length of the end segment of the trunk (counting
        what was split off it already: the end of a split cable lies at the split plane), less what must stay of it. The split stays
        inside the end segment so that no waypoint of the trunk is cut off.

        :param start: Which end.
        :type start: bool
        :returns: Distance in mm; 0.0 when the end segment is too short to split in.
        :rtype: float
        """
        db_obj = self.db_obj
        points = [db_obj.start_position3d.as_numpy, *(p.point.as_numpy for p in db_obj.waypoints3d),
                  db_obj.stop_position3d.as_numpy]

        if start:
            reach = float(np.linalg.norm(points[1] - points[0])) + db_obj.start_split_mm
        else:
            reach = float(np.linalg.norm(points[-1] - points[-2])) + db_obj.stop_split_mm

        return max(0.0, reach - _cable_3d.MIN_TRUNK_MM)

    @_check_types.do
    def lead_wires(self, start: bool) -> list["_wire.Wire"]:
        """The wire objects that are the leads of this cable's conductors at one end, in conductor order. A conductor whose
        lead is not built (an end that is not split) is left out.

        :param start: Which end.
        :type start: bool
        :rtype: list[:class:`_wire.Wire`]
        """
        wires_table = self.mainframe.project.ptables.pjt_wires_table
        result = []

        for conductor in self.db_obj.conductors:
            split_id = conductor.start_split_point3d_id if start else conductor.stop_split_point3d_id

            if split_id is None:
                continue

            for lead_db in wires_table.leads_of(conductor.db_id):
                if lead_db.stop_position3d_id == split_id:
                    lead = lead_db.get_object()

                    if lead is not None:
                        result.append(lead)

        return result

    @_check_types.do
    def can_join(self, start: bool) -> bool:
        """Whether the conductors of one end can be brought back into the cable: nothing is attached to the free end of
        any of their leads (a terminal, a splice).

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        return all(lead.start_sibling is None for lead in self.lead_wires(start))

    @_check_types.do
    def can_reorder(self, start: bool) -> bool:
        """Whether the fan-out order of one end can be changed: always before the end is split (it is used when it is), and
        after, while nothing is attached to the free end of any lead (a terminal or splice there would be left behind when the
        end points move). Never for a ribbon, whose conductors tear off the web in pin order.

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        return self.can_join(start) and not self.db_obj.part.is_ribbon

    @_check_types.do
    def can_roll(self) -> bool:
        """Whether the ribbon can be turned about its length: it is a ribbon and neither end is split (the conductors' split
        points sit on the ribbon's flat side, which the roll moves).

        :rtype: bool
        """
        return self.db_obj.part.is_ribbon and not self.is_split(True) and not self.is_split(False)

    @_check_types.do
    def set_roll(self, degrees: float) -> None:
        """Turn the ribbon about its length, so that its flat side starts at *degrees* from the 3D view's default.

        :param degrees: The roll, degrees.
        :type degrees: float
        :raises ValueError: Raised when :meth:`can_roll` is false.
        """
        if not self.can_roll():
            raise ValueError('only a ribbon whose conductors are joined at both ends can be rolled')

        self.db_obj.roll_deg = float(degrees)
        self.obj3d.reload_roll()

    @_check_types.do
    def fan_order(self, start: bool) -> list["_pjt_cable_conductor.PJTCableConductor"]:
        """The conductors of one end in the order they fan out in (their ``start_order`` / ``stop_order``, ties by ``idx``).

        :param start: Which end.
        :type start: bool
        :rtype: list[:class:`_pjt_cable_conductor.PJTCableConductor`]
        """
        return sorted(self.db_obj.conductors, key=lambda conductor: (conductor.start_order if start else conductor.stop_order,
                                                                      conductor.idx))

    @_check_types.do
    def conductor_label(self, conductor: "_pjt_cable_conductor.PJTCableConductor") -> str:
        """A line that says which conductor this is: its name and, when it has one, its colour.

        :param conductor: One of the cable's conductors.
        :type conductor: :class:`_pjt_cable_conductor.PJTCableConductor`
        :rtype: str
        """
        if conductor.is_shield:
            return f'{conductor.name} (shield)'

        try:
            color = conductor.part.color
            name = None if color is None else str(color.name)
        except (KeyError, IndexError, AttributeError):
            name = None

        return conductor.name if not name else f'{conductor.name}  ·  {name}'

    @_check_types.do
    def set_fan_order(self, start: bool, ordered: list["_pjt_cable_conductor.PJTCableConductor"]) -> None:
        """Set the order the conductors of one end fan out in: *ordered* is every conductor of the cable once, first place first.
        On an end that is already split, each conductor's end point moves to its new place.

        :param start: Which end.
        :type start: bool
        :param ordered: The conductors in their new order.
        :type ordered: list[:class:`_pjt_cable_conductor.PJTCableConductor`]
        :raises ValueError: Raised when *ordered* is not the cable's conductors, or something is attached to a lead's free end.
        """
        conductors = self.db_obj.conductors

        if sorted(c.db_id for c in ordered) != sorted(c.db_id for c in conductors):
            raise ValueError('the order must name every conductor of the cable once')

        if not self.can_reorder(start):
            raise ValueError('something is attached to a conductor of this end')

        for place, conductor in enumerate(ordered):
            if start:
                conductor.start_order = place
            else:
                conductor.stop_order = place

        if not self.is_split(start):
            return

        points = self.mainframe.project.ptables.pjt_points3d_table

        for conductor, target in zip(conductors, self.obj3d.fan_out_positions(start)):
            live = points[conductor.start_position3d_id if start else conductor.stop_position3d_id].point
            live += _point.Point(*(float(v) for v in target)) - live

        self._move_board_ends(start)
        self.obj3d.editor3d.Refresh()
        self.objpegboard.pegboard.Refresh()

    @_check_types.do
    def _board_ready(self, start: bool) -> bool:
        """Whether the cable's end segment has a length on the board for a split at one end to be laid out on (a cable placed
        before the board knew cables has none until it is seeded).

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        return len(self.objpegboard.split_positions(start)) == len(self.db_obj.conductors) > 0

    @_check_types.do
    def _move_board_ends(self, start: bool) -> None:
        """Put each conductor's end point of one end on the board where it lands now (its place in the fan-out); nothing
        happens while the end is not laid out on the board.

        :param start: Which end.
        :type start: bool
        """
        if not self._board_ready(start):
            return

        points = self.mainframe.project.ptables.pjt_points_pegboard_table

        for conductor, target in zip(self.db_obj.conductors, self.objpegboard.fan_out_positions(start)):
            # the row is kept while the point moves: the point's write-back to it is a weak callback
            row = points[conductor.start_position_pegboard_id if start else conductor.stop_position_pegboard_id]
            live = row.point
            live += _point.Point(float(target[0]), 0.0, float(target[2])) - live

    @_check_types.do
    def _move_board_split_points(self, start: bool) -> None:
        """Put each conductor's split point of one end on the board's split plane, where the conductor leaves the trunk now;
        nothing happens while the end is not split or not laid out on the board.

        :param start: Which end.
        :type start: bool
        """
        if not self._board_ready(start):
            return

        points = self.mainframe.project.ptables.pjt_points_pegboard_table

        for conductor, plane in zip(self.db_obj.conductors, self.objpegboard.split_positions(start)):
            split_id = conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id

            if split_id is None:
                continue

            row = points[split_id]
            live = row.point
            delta = _point.Point(float(plane[0]), 0.0, float(plane[2])) - live

            if float(np.linalg.norm(delta.as_numpy)) > 1e-9:
                live += delta

    @_check_types.do
    def follow_drag(self, view: str, before_start: np.ndarray, before_stop: np.ndarray) -> None:
        """Let the conductors follow after a drag step moved the cable's points in one view.

        An end that is not split needs nothing: a conductor's end point is a child of the cable's. For a split end the split
        points are laid on the split plane again (the trunk's end segment may have moved or turned) and the free ends of the
        leads are carried along with the cable's end by the distance it moved; a lead that has a terminal or splice on its
        free end stays where it is, as an attached wire end does, and its lead stretches.

        :param view: ``'3d'`` or ``'pegboard'``: the view the drag was in (the other view is not touched).
        :type view: str
        :param before_start: Where the cable's start was in that view before this step.
        :type before_start: :class:`np.ndarray`
        :param before_stop: Where its stop was.
        :type before_stop: :class:`np.ndarray`
        """
        board = view == 'pegboard'
        shown = self.objpegboard if board else self.obj3d

        for start, before, point in ((True, before_start, shown.start_position), (False, before_stop, shown.stop_position)):
            if not self.is_split(start):
                continue

            if board:
                self._move_board_split_points(start)
            else:
                self._sync_split_points(start)

            moved = np.asarray(point.as_numpy, dtype=np.float64) - before

            if float(np.linalg.norm(moved)) > 1e-9:
                self._carry_free_leads(start, moved, board)

    @_check_types.do
    def sync_split_ends(self) -> None:
        """Keep the split points of every split end on the trunk's split plane after the trunk's 3D route changed (a waypoint or an
        end moved, by whatever dragged it): the leads end at the split points, so a split point left behind would leave the lead's end
        apart from the cable. Called by the 3D view whenever one of its points moves; nothing while the cable has no split end (or is
        still being built)."""
        if self.obj3d is None or self.objpegboard is None:
            return

        for start in (True, False):
            if self.is_split(start):
                self._sync_split_points(start)

    @_check_types.do
    def sync_board_split_ends(self) -> None:
        """The same for the board's split points after the board's route changed."""
        if self.obj3d is None or self.objpegboard is None:
            return

        for start in (True, False):
            if self.is_split(start):
                self._move_board_split_points(start)

    @_check_types.do
    def _carry_free_leads(self, start: bool, moved: np.ndarray, board: bool) -> None:
        """Move the free end of each lead of one end by *moved*, except where something is attached to it.

        :param start: Which end.
        :type start: bool
        :param moved: How far the cable's end moved, in the view's space.
        :type moved: :class:`np.ndarray`
        :param board: Whether it is the board's points that move (else the 3D ones).
        :type board: bool
        """
        ptables = self.mainframe.project.ptables
        points = ptables.pjt_points_pegboard_table if board else ptables.pjt_points3d_table
        shift = _point.Point(float(moved[0]), float(moved[1]), float(moved[2]))
        held = []  # the rows stay referenced while their points move: the write-back to a row is a weak callback

        for lead in self.lead_wires(start):
            if lead.start_sibling is not None:
                continue

            end_id = lead.db_obj.start_position_pegboard_id if board else lead.db_obj.start_position3d_id

            if end_id is None:
                continue

            row = points[end_id]
            held.append(row)
            live = row.point
            live += shift

    @_check_types.do
    def _make_split_markers(self, start: bool) -> None:
        """Draw a marker at the end of each lead of a split end, where it joins the trunk: the conductor's split point.

        They are pseudo layouts (:class:`~harness_designer.database.project_db.pseudo_wire_layout.PseudoCableSplitLayout`), not
        rows: the split point is already stored, the markers are only for the eye (sized and coloured as the conductor, not
        picked) and are made again whenever the cable is built or its end split, and dropped when the end is joined.
        One marker per conductor in 3D and one on the board where the split is laid out there.

        :param start: Which end.
        :type start: bool
        """
        import uuid  # NOQA

        from . import wire_layout as _wire_layout_facade  # NOQA -- avoid a cycle at import time
        from ..database.project_db import pseudo_wire_layout as _pseudo  # NOQA -- avoid a cycle at import time

        self._drop_split_markers(start)

        ptables = self.mainframe.project.ptables
        points = ptables.pjt_points3d_table
        board_points = ptables.pjt_points_pegboard_table
        markers = self._split_markers[start]

        for conductor in self.db_obj.conductors:
            split_id = conductor.start_split_point3d_id if start else conductor.stop_split_point3d_id

            if split_id is None:
                continue

            board_id = conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id
            part = conductor.part

            for position3d, position_pegboard in (
                (points[split_id].point, None),
                (None, board_points[board_id].point if board_id is not None else None),
            ):
                if position3d is None and position_pegboard is None:
                    continue

                pseudo = _pseudo.PseudoCableSplitLayout(None, uuid.uuid4().bytes)
                pseudo.configure_split(part, position3d=position3d, position_pegboard=position_pegboard)
                markers.append(_wire_layout_facade.WireLayout(self.mainframe, pseudo))

    @_check_types.do
    def _drop_split_markers(self, start: bool) -> None:
        """Take the drawn markers of one end out of the views (they have no row to delete).

        :param start: Which end.
        :type start: bool
        """
        for marker in self._split_markers[start]:
            self.mainframe.remove_object(marker)

        self._split_markers[start] = []

    @_check_types.do
    def _sync_split_points(self, start: bool) -> None:
        """Put each conductor's split point of one end on the trunk's split plane, where the conductor leaves it now.

        :param start: Which end.
        :type start: bool
        """
        points = self.mainframe.project.ptables.pjt_points3d_table

        for conductor, plane in zip(self.db_obj.conductors, self.obj3d.split_positions(start)):
            split_id = conductor.start_split_point3d_id if start else conductor.stop_split_point3d_id

            if split_id is None:
                continue

            # the row is kept while the point moves: the point's write-back to it is a weak callback
            row = points[split_id]
            live = row.point
            delta = _point.Point(*(float(v) for v in plane)) - live

            if float(np.linalg.norm(delta.as_numpy)) > 1e-9:
                live += delta

        self._move_board_split_points(start)

    @_check_types.do
    def _move_end(self, start: bool, distance: float, inward: bool) -> None:
        """Move one end of the cable along its end segment, in 3D and on the board: *distance* mm toward the next point of the route
        (inward) or away from it. A split moves the end to the split plane, so that the stretch the leads cover is not counted in
        the cable's length as well; a join moves it back.

        :param start: Which end.
        :param distance: How far, mm.
        :param inward: Toward the next point (True) or away from it (False).
        """
        for view in (self.obj3d, self.objpegboard):
            segments = view._segments()  # NOQA

            if not segments:
                continue

            if start:
                p1, p2 = segments[0]
                point = view.start_position
                toward = p2 - p1
            else:
                p1, p2 = segments[-1]
                point = view.stop_position
                toward = p1 - p2

            length = float(np.linalg.norm(toward))

            if length < 1e-9:
                continue

            shift = toward / length * distance

            if not inward:
                shift = -shift

            point += _point.Point(float(shift[0]), float(shift[1]), float(shift[2]))

    @_check_types.do
    def split_end(self, start: bool, distance: float) -> None:
        """Split the conductors out of the cable at one end, *distance* mm from the end.

        The cable's end moves to that plane (the stretch beyond it is the leads' now: counted in their lengths, not the cable's) and
        the split distance records how far beyond it the end was, where the conductors' ends fan out. Each conductor gets a split point on the plane (where
        the conductor is at that plane) and a LEAD: an ordinary wire (``pjt_wires``, ``cable_conductor_id`` set) from the conductor's
        end point to the split point. The end point stops following the cable's end and goes to its own place, spread out across the
        cable's true end. On an end that is already split only the distance changes (the end moves along its segment, the leads
        follow).

        :param start: Which end.
        :type start: bool
        :param distance: Mm from the end to the plane; between 1 and :meth:`max_split_mm`.
        :type distance: float
        :raises ValueError: Raised when the distance is out of range or the cable has no conductors.
        """
        from . import wire as _wire_facade  # NOQA -- avoid a cycle at import time

        db_obj = self.db_obj
        conductors = db_obj.conductors

        if not conductors:
            raise ValueError('the cable has no conductors')

        if distance < _cable_3d.MIN_SPLIT_MM or distance > self.max_split_mm(start):
            raise ValueError(f'the split distance {distance} is out of range')

        already = self.is_split(start)

        if already:
            # the end goes back to where the cable's end was, then in to the new plane; the conductors' ends stay where they are
            before = db_obj.start_split_mm if start else db_obj.stop_split_mm
            self._move_end(start, before, inward=False)

            if start:
                db_obj.start_split_mm = distance
            else:
                db_obj.stop_split_mm = distance

            self._move_end(start, distance, inward=True)
            self.obj3d.reload_splits()
            self.objpegboard.reload_splits()
            self._sync_split_points(start)
            return

        ptables = self.mainframe.project.ptables
        points = ptables.pjt_points3d_table
        board_points = ptables.pjt_points_pegboard_table
        side = 'start' if start else 'stop'

        board = self._board_ready(start)

        # the conductors' end points are the cable's old end, copied: they stay where the end is now (a point that was a child of the
        # cable's end would be carried along when the end moves, so it is cut loose first)
        for conductor in conductors:
            points[conductor.start_position3d_id if start else conductor.stop_position3d_id].detach_from_parent()

        # the cable's end moves to the split plane
        if start:
            db_obj.start_split_mm = distance
        else:
            db_obj.stop_split_mm = distance

        self._move_end(start, distance, inward=True)

        self.obj3d.reload_splits()
        self.objpegboard.reload_splits()

        # the end cross-section at the plane gives the conductors' split points (where the markers go and the leads start); the same
        # cross-section projected onto the copied end, from a light behind it, gives where each conductor's end lands
        planes = self.obj3d.split_positions(start)
        targets = self.obj3d.fan_out_positions(start)
        board_planes = self.objpegboard.split_positions(start) if board else []
        board_targets = self.objpegboard.fan_out_positions(start) if board else []

        for conductor, target in zip(conductors, targets):
            live = points[conductor.start_position3d_id if start else conductor.stop_position3d_id].point
            live += _point.Point(*(float(v) for v in target)) - live

        for index, (conductor, plane) in enumerate(zip(conductors, planes)):
            end_id = conductor.start_position3d_id if start else conductor.stop_position3d_id

            split_row = points.insert(float(plane[0]), float(plane[1]), float(plane[2]))

            if start:
                conductor.start_split_point3d_id = split_row.db_id
            else:
                conductor.stop_split_point3d_id = split_row.db_id

            lead_db = ptables.pjt_wires_table.insert(
                db_obj.part_id, f'{conductor.name} ({side})', None, end_id, split_row.db_id,
                None, None, True, False, None, None, False, cable_conductor_id=conductor.db_id)

            if board:
                # On the board the conductor's end is made now (a point that starts at the origin) and put in its place.
                # The lead row keeps both point rows from here on (asking for the positions makes it hold them): a point's
                # write-back to its row is a weak callback, so a move only persists while something holds the row.
                end_peg_id = conductor.start_position_pegboard_id if start else conductor.stop_position_pegboard_id
                split_peg = board_points.insert(float(board_planes[index][0]), 0.0, float(board_planes[index][2]))

                if start:
                    conductor.start_split_point_pegboard_id = split_peg.db_id
                else:
                    conductor.stop_split_point_pegboard_id = split_peg.db_id

                lead_db.start_position_pegboard_id = end_peg_id
                lead_db.stop_position_pegboard_id = split_peg.db_id

                lead_db.stop_position_pegboard  # NOQA
                end_peg = lead_db.start_position_pegboard
                end_peg += _point.Point(float(board_targets[index][0]), 0.0, float(board_targets[index][2])) - end_peg

            lead = _wire_facade.Wire(self.mainframe, lead_db)
            self.mainframe.project.add_wire(lead)

            # The lead's split end attaches to the conductor, the junction between this lead and the one at the other end.
            node = self.conductor_object(conductor)
            lead.set_sibling(node, lead.obj3d.stop_position)
            node.set_lead(start, lead)


        self._make_split_markers(start)

        self.obj3d.editor3d.Refresh()
        self.objpegboard.pegboard.Refresh()
        self.refresh_browser()

    @_check_types.do
    def join_end(self, start: bool) -> None:
        """Bring the conductors of one end back into the cable: the leads and the split points are deleted and each end
        point goes back onto the cable's end and follows it.

        :param start: Which end.
        :type start: bool
        :raises ValueError: Raised when something is attached to the free end of a lead (see :meth:`can_join`).
        """
        db_obj = self.db_obj

        if not self.is_split(start):
            return

        if not self.can_join(start):
            raise ValueError('something is attached to a conductor of this end')

        points = self.mainframe.project.ptables.pjt_points3d_table
        board_points = self.mainframe.project.ptables.pjt_points_pegboard_table
        parent_id = db_obj.start_position3d_id if start else db_obj.stop_position3d_id
        split_mm = db_obj.start_split_mm if start else db_obj.stop_split_mm

        self._drop_split_markers(start)

        for lead in self.lead_wires(start):
            lead.delete()

        # the cable's end goes back out to where it was before the split, and the conductors join it there
        self._move_end(start, split_mm, inward=False)

        for conductor in db_obj.conductors:
            if start:
                split_id = conductor.start_split_point3d_id
                conductor.start_split_point3d_id = None
            else:
                split_id = conductor.stop_split_point3d_id
                conductor.stop_split_point3d_id = None

            if split_id is not None:
                points[split_id].delete()

            points[conductor.start_position3d_id if start else conductor.stop_position3d_id].attach_to_parent(parent_id)

            # the board's split point goes with the lead; the conductor's board end point stays, to be put in its place again
            # at the next split
            board_split_id = conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id

            if board_split_id is not None:
                if start:
                    conductor.start_split_point_pegboard_id = None
                else:
                    conductor.stop_split_point_pegboard_id = None

                board_points[board_split_id].delete()

        if start:
            db_obj.start_split_mm = 0.0
        else:
            db_obj.stop_split_mm = 0.0

        self.obj3d.reload_splits()
        self.objpegboard.reload_splits()
        self.refresh_browser()

    @property
    @_check_types.do
    def start_sibling(self) -> None:
        """What the cable's start end is attached to: nothing, ever. A cable's ends are free; its conductors attach.

        :rtype: None
        """
        return None

    @property
    @_check_types.do
    def stop_sibling(self) -> None:
        """What the cable's stop end is attached to: nothing, ever. A cable's ends are free; its conductors attach.

        :rtype: None
        """
        return None

    @_check_types.do
    def delete(self) -> None:
        """Delete the cable: its leads, its view, its registry entry, its conductors and its row."""
        for start in (True, False):
            self._drop_split_markers(start)

            for lead in self.lead_wires(start):
                lead.delete()

        for node in self._conductor_objects.values():
            node.delete()

        super().delete()

        self.mainframe.project.delete_cable(self.db_obj.db_id)
        self.db_obj.delete()
