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

import weakref

import numpy as np

from . import ObjectBase as _ObjectBase
from . import cable_conductor as _cable_conductor
from ..geometry import point as _point
from .objects_3d import cable as _cable_3d
from .objects_pegboard import cable as _cable_pegboard
from .objects_schematic import cable as _cable_schematic
from ..shapes import sleeve as _sleeve_shape
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
    objschematic: _cable_schematic.Cable = None
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

        # an inert placeholder: a cable is not drawn in the schematic (its conductors are), but it can be the selected object there
        self.objschematic = _cable_schematic.Cable(self, db_obj)

        # Keeps the board's route as long as the cable really is, the way a wire's own handler does: a move of any of its points
        # (either view) re-fits the route (slack bowed in when the ends are closer than its length, the far end pulled when they would
        # be further apart); see handlers.wire_slack_handler. Before the views seed or lay out anything, so it is there to be asked.
        from ..handlers import wire_slack_handler as _wire_slack_handler  # NOQA -- avoid a cycle at import time

        self._slack_handler = _wire_slack_handler.WireSlackHandler(self)

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
    def conductor_wires(self) -> list["_wire.Wire"]:
        """Every wire object that belongs to one of this cable's conductors, at both ends: the leads and, when a splice or a wire
        service loop was put in a lead, the pieces beyond it (they all carry the conductor's id).

        :rtype: list[:class:`_wire.Wire`]
        """
        wires_table = self.mainframe.project.ptables.pjt_wires_table
        result = []

        for conductor in self.db_obj.conductors:
            for wire_db in wires_table.leads_of(conductor.db_id):
                wire = wire_db.get_object()

                if wire is not None and wire not in result:
                    result.append(wire)

        return result

    @_check_types.do
    def can_join(self, start: bool) -> bool:
        """Whether the conductors of one end can be brought back into the cable: no terminal is attached to any of their leads. A
        splice or a wire service loop in a lead does not stop it: they are taken out with the lead (see :meth:`join_end`).

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        return not any(self.lead_chain(lead)[2] for lead in self.lead_wires(start))

    @_check_types.do
    def lead_chain(self, lead: "_wire.Wire") -> tuple[list["_wire.Wire"], list, bool]:
        """Follow a lead outward from the split plane through the splices and wire service loops put in it.

        :param lead: The lead proper (the piece that ends on the split point).
        :type lead: :class:`_wire.Wire`
        :returns: ``(pieces, junctions, blocked)``: the wires of the conductor from the lead outward (the lead first), the splices and
            loops between them, and whether the chain ends on something that is not the conductor's to take away (a terminal, or an
            object that is not a splice or a loop). Where a splice has other wires on it, those are not part of the chain.
        :rtype: tuple[list[:class:`_wire.Wire`], list, bool]
        """
        conductor_id = lead.db_obj.cable_conductor_id
        pieces = [lead]
        junctions = []
        wire = lead

        while True:
            sibling = wire.start_sibling

            if sibling is None:
                return pieces, junctions, False

            if not (sibling.is_splice or sibling.is_wire_service_loop):
                return pieces, junctions, True

            junctions.append(sibling)
            following = None

            for candidate in (sibling.start_sibling, sibling.stop_sibling):
                if candidate is not None and candidate is not wire and candidate.db_obj.cable_conductor_id == conductor_id:
                    following = candidate

            if following is None or following in pieces:
                return pieces, junctions, False

            pieces.append(following)
            wire = following

    @_check_types.do
    def _remove_junctions(self, junctions: list) -> None:
        """Delete the splices and loops that were in a conductor's lead, once the wires of the conductor are gone: a wire service
        loop always goes; a splice goes only when no other wire is left on it.

        :param junctions: What :meth:`lead_chain` found.
        :type junctions: list
        """
        done = []

        for junction in junctions:
            if any(junction is other for other in done):
                continue

            done.append(junction)

            if junction.is_wire_service_loop:
                junction.delete()
            elif junction.is_splice and not junction.wires:
                junction.delete()

    @_check_types.do
    def can_reorder(self, start: bool) -> bool:
        """Whether the fan-out order of one end can be changed: always before the end is split (it is used when it is), and
        after, while nothing is attached to the free end of any lead (a terminal or splice there would be left behind when the
        end points move). Never for a ribbon, whose conductors tear off the web in pin order.

        :param start: Which end.
        :type start: bool
        :rtype: bool
        """
        if any(lead.start_sibling is not None for lead in self.lead_wires(start)):
            return False

        return not self.db_obj.part.is_ribbon

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

        # the sleeve of this end (and its pigtail) lies on the same plane
        self._sync_board_sleeve(start)

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
        self._sync_shield_sleeve(start)

    @_check_types.do
    def _move_end(self, start: bool, distance: float, inward: bool) -> None:
        """Move one end of the cable along its end segment, in 3D and on the board: *distance* mm toward the next point of the route
        (inward) or away from it. A split moves the end to the split plane, so that the stretch the leads cover is not counted in
        the cable's length as well; a join moves it back.

        :param start: Which end.
        :param distance: How far, mm.
        :param inward: Toward the next point (True) or away from it (False).
        """
        # the end moves in 3D, then on the board: the length the board must be follows the first, so the route is fitted once both are done
        with self._slack_handler.suspended():
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

        self._slack_handler.reconcile()

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
        # The rows are kept in this list until the end points are in their places: a point's write-back to its row is a weak
        # callback, so a row that nothing holds can be dropped before the move is written and the point is read back, later, at
        # the cable's old end (every conductor of the end at one point).
        end_rows = []

        for conductor in conductors:
            row = points[conductor.start_position3d_id if start else conductor.stop_position3d_id]
            row.detach_from_parent()
            end_rows.append(row)

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

        for row, target in zip(end_rows, targets):
            live = row.point
            live += _point.Point(*(float(v) for v in target)) - live

        for index, (conductor, plane) in enumerate(zip(conductors, planes)):
            end_id = conductor.start_position3d_id if start else conductor.stop_position3d_id

            split_row = points.insert(float(plane[0]), float(plane[1]), float(plane[2]))

            if start:
                conductor.start_split_point3d_id = split_row.db_id
            else:
                conductor.stop_split_point3d_id = split_row.db_id

            # a clipped shield (``shield_clipped`` column) has no lead: it is not connected at this end
            no_lead = conductor.is_shield and db_obj.shield_end_clipped(start)

            lead_db = None if no_lead else ptables.pjt_wires_table.insert(
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

                if lead_db is not None:
                    lead_db.start_position_pegboard_id = end_peg_id
                    lead_db.stop_position_pegboard_id = split_peg.db_id

                    lead_db.stop_position_pegboard  # NOQA
                    end_peg = lead_db.start_position_pegboard
                    end_peg += _point.Point(float(board_targets[index][0]), 0.0, float(board_targets[index][2])) - end_peg

            if lead_db is None:
                continue

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
        :raises ValueError: Raised when a terminal is attached to a lead (see :meth:`can_join`).

        Every piece of each conductor's lead goes, with the wire service loops in them; a splice goes too unless other wires are still
        on it.
        """
        db_obj = self.db_obj

        if not self.is_split(start):
            return

        if not self.can_join(start):
            raise ValueError('something is attached to a conductor of this end')

        # the sleeve sits on the split plane: with the end joined there is none (user, 2026-11-11), and a clipped shield is
        # unclipped again: clip, sleeve and Unclip all belong to a split end
        self.remove_shield_sleeve(start)
        db_obj.set_shield_end_clipped(start, False)

        points = self.mainframe.project.ptables.pjt_points3d_table
        board_points = self.mainframe.project.ptables.pjt_points_pegboard_table
        parent_id = db_obj.start_position3d_id if start else db_obj.stop_position3d_id
        split_mm = db_obj.start_split_mm if start else db_obj.stop_split_mm

        self._drop_split_markers(start)

        junctions = []

        for lead in self.lead_wires(start):
            pieces, found, _blocked = self.lead_chain(lead)
            junctions.extend(found)

            for piece in pieces:
                piece.delete()

        self._remove_junctions(junctions)

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

    # ------------------------------------------------------------------ solder sleeve on a shielded, split end
    # (SHIELD_SLEEVE_DESIGN.md: the sleeve is a splice, `pjt_cables.start_shield_splice_id` / `stop_shield_splice_id` say which)

    @_check_types.do
    def shield_sleeve(self, start: bool):
        """The solder sleeve (the splice's facade) on one end of the cable; ``None`` when that end has none.

        :param start: Which end.
        :type start: bool
        """
        sleeve_id = self.db_obj.shield_splice_id(start)

        if sleeve_id is None:
            return None

        return self.mainframe.project.ptables.pjt_splices_table[sleeve_id].get_object()

    @_check_types.do
    def _shield_lead(self, start: bool):
        """The lead (the wire) of the shield conductor at one end; ``None`` when the end is not split or the shield has none."""
        shield = next((conductor for conductor in self.db_obj.conductors if conductor.is_shield), None)

        if shield is None:
            return None

        return next((lead for lead in self.lead_wires(start) if lead.db_obj.cable_conductor_id == shield.db_id), None)

    @_check_types.do
    def can_add_shield_sleeve(self, start: bool) -> bool:
        """Whether a solder sleeve can be put on one end: the cable's part is shielded, the end is split (the sleeve sits at the split
        plane, where the conductors leave), has no sleeve yet, and nothing is connected to the shield's own lead (the sleeve takes its
        place: the shield is finished by the sleeve and the pigtail, not by a lead).

        :param start: Which end.
        :type start: bool
        """
        db_obj = self.db_obj

        if not (bool(db_obj.part.shielded) and self.is_split(start) and db_obj.shield_splice_id(start) is None and
                not db_obj.shield_end_clipped(start) and any(conductor.is_shield for conductor in db_obj.conductors)):
            return False

        lead = self._shield_lead(start)

        if lead is None:
            return True

        pieces, junctions, blocked = self.lead_chain(lead)
        return len(pieces) == 1 and not junctions and not blocked

    @_check_types.do
    def shield_clipped(self, start: bool) -> bool:
        """Whether the shield is clipped off at one end (the cable's ``shield_clipped`` column, bit 1 for the start, bit 2 for the
        stop): a clipped end has no sleeve and, once split, no lead for the shield. Both ends can be clipped (user, 2026-11-11: a
        shield used only as a protective jacket is not connected anywhere).

        :param start: Which end.
        :type start: bool
        """
        db_obj = self.db_obj

        return bool(db_obj.part.shielded) and db_obj.shield_end_clipped(start)

    @_check_types.do
    def can_clip_shield(self, start: bool) -> bool:
        """Whether the shield can be clipped off at one end (the way a split is the end's own state, nothing here works unless the end
        is split): the cable is shielded and has a shield, the end is split, not clipped yet and has no sleeve (user, 2026-11-11: with a
        sleeve on it the clip is greyed out), and nothing is connected to the shield's lead (it is deleted by the clip).

        :param start: Which end.
        :type start: bool
        """
        db_obj = self.db_obj

        if not (bool(db_obj.part.shielded) and any(conductor.is_shield for conductor in db_obj.conductors) and self.is_split(start) and
                not db_obj.shield_end_clipped(start) and db_obj.shield_splice_id(start) is None):
            return False

        lead = self._shield_lead(start)

        if lead is None:
            return True

        pieces, junctions, blocked = self.lead_chain(lead)
        return len(pieces) == 1 and not junctions and not blocked

    @_check_types.do
    def clip_shield(self, start: bool) -> None:
        """Cut the shield off at one end: the end's bit of ``shield_clipped`` is set and the shield's own lead is deleted. The end gets
        no sleeve. Either end, or both, can be clipped; :meth:`unclip_shield` makes the lead again.

        :param start: Which end.
        :type start: bool
        :raises ValueError: Raised when the end cannot be clipped (see :meth:`can_clip_shield`).
        """
        if not self.can_clip_shield(start):
            raise ValueError("the shield can be clipped on a split end of a shielded cable that has no sleeve and nothing connected "
                             "to the shield's lead")

        self.db_obj.set_shield_end_clipped(start, True)
        lead = self._shield_lead(start)

        if lead is not None:
            lead.delete()

        self.obj3d.editor3d.Refresh()
        self.refresh_browser()

    @_check_types.do
    def can_unclip_shield(self, start: bool) -> bool:
        """Whether the clip of one end can be taken back: the end is split and clipped.

        :param start: Which end.
        :type start: bool
        """
        return self.shield_clipped(start) and self.is_split(start)

    @_check_types.do
    def unclip_shield(self, start: bool) -> None:
        """Take the clip off one end: the shield is whole there again, so its lead is made again, from the conductor's end point to
        its split point (as :meth:`split_end` makes it), ready to be connected.

        :param start: Which end.
        :type start: bool
        :raises ValueError: Raised when the end is not split or not clipped (see :meth:`can_unclip_shield`).
        """
        if not self.can_unclip_shield(start):
            raise ValueError('the clip can be taken off a split end whose shield is clipped')

        self.db_obj.set_shield_end_clipped(start, False)
        self._make_shield_lead(start)

        self.obj3d.editor3d.Refresh()
        self.objpegboard.pegboard.Refresh()
        self.refresh_browser()

    @_check_types.do
    def _make_shield_lead(self, start: bool) -> None:
        """Make the lead of the shield conductor of a split end that has none (a clip taken off): an ordinary wire from the conductor's
        end point to its split point on the plane, attached to the conductor's junction, as :meth:`split_end` makes each lead."""
        from . import wire as _wire_facade  # NOQA -- avoid a cycle at import time

        db_obj = self.db_obj
        conductor = next((c for c in db_obj.conductors if c.is_shield), None)

        if conductor is None or self._shield_lead(start) is not None:
            return

        split_id = conductor.start_split_point3d_id if start else conductor.stop_split_point3d_id

        if split_id is None:
            return

        end_id = conductor.start_position3d_id if start else conductor.stop_position3d_id
        wires_table = self.mainframe.project.ptables.pjt_wires_table
        side = 'start' if start else 'stop'

        lead_db = wires_table.insert(
            db_obj.part_id, f'{conductor.name} ({side})', None, end_id, split_id, None, None, True, False, None, None, False,
            cable_conductor_id=conductor.db_id)

        split_peg_id = conductor.start_split_point_pegboard_id if start else conductor.stop_split_point_pegboard_id

        if split_peg_id is not None:
            # the row keeps both board points from here on (a point's write-back to its row is a weak callback)
            lead_db.start_position_pegboard_id = conductor.start_position_pegboard_id if start else conductor.stop_position_pegboard_id
            lead_db.stop_position_pegboard_id = split_peg_id

            lead_db.stop_position_pegboard  # NOQA
            lead_db.start_position_pegboard  # NOQA

        lead = _wire_facade.Wire(self.mainframe, lead_db)
        self.mainframe.project.add_wire(lead)

        node = self.conductor_object(conductor)
        lead.set_sibling(node, lead.obj3d.stop_position)
        node.set_lead(start, lead)

        # the shield's end point goes to its place in the fan-out on the board
        self._move_board_ends(start)

    @_check_types.do
    def _sleeve_pose(self, start: bool, length: float) -> tuple[np.ndarray, np.ndarray] | None:
        """Where the sleeve of one end lies: from the split plane (its start, where the conductors leave) a *length* into the trunk
        (its stop); ``None`` while the end's frame is not known."""
        frame = self.obj3d._end_frame(start)  # NOQA

        if frame is None:
            return None

        end = np.asarray(frame[0], dtype=np.float64)
        inward = np.asarray(frame[1], dtype=np.float64)

        return end, end + inward * length

    @_check_types.do
    def _pigtail_part_id(self, sleeve_part) -> bytes | None:
        """The catalog wire for the pigtail of a sleeve that comes with one: a plain wire (one conductor, no shield) of the gauge the
        sleeve's lead takes (the middle of its AWG range; 20 AWG when the part gives none). ``None`` when the catalog has no such wire."""
        known = [value for value in (sleeve_part.wire_size_awg_min, sleeve_part.wire_size_awg_max) if value is not None]
        target = sum(known) / len(known) if known else 20.0

        rows = self.mainframe.project.ptables.global_db.wires_table.select(
            'id', 'wire_size_awg', num_conductors=1, shielded=0)
        rows = [row for row in rows if row[1] is not None]

        if not rows:
            return None

        return min(rows, key=lambda row: abs(row[1] - target))[0]

    @_check_types.do
    def _build_sleeve(self, start: bool, part_id: bytes, part, pose: tuple[np.ndarray, np.ndarray], branch_id: bytes | None):
        """Make the splice of a sleeve (its rows, the cable's column, the object) between the two points of *pose*; its branch point
        is the row *branch_id* when given (a sleeve put in its new place keeps it, with the pigtail on it), else a new one at the
        start of the pose."""
        from . import splice as _splice_facade  # NOQA -- avoid a cycle at import time

        ptables = self.mainframe.project.ptables
        points = ptables.pjt_points3d_table

        start_row = points.insert(*(float(v) for v in pose[0]))
        stop_row = points.insert(*(float(v) for v in pose[1]))

        if branch_id is None:
            branch_id = points.insert(*(float(v) for v in pose[0])).db_id

        splice_db = ptables.pjt_splices_table.insert(
            part_id, f'{part.manufacturer.name} {part.part_number}', start_row.db_id, stop_row.db_id, branch_id, None, None)

        # on the board the sleeve lies at the board's split plane of this end (before its board view is made: the view is turned once,
        # when it is made, and a point that is still at the origin would be seeded from the 3D position)
        self._place_sleeve_on_board(start, splice_db, part)

        # in the schematic a sleeve is shown once its pigtail is connected to something (``wire_routing.reroute.on_wire_attached`` shows
        # it and puts it beside what the pigtail is connected to); stored, so it stays hidden after a reload (the view's own
        # ``is_visible`` setter writes a column that does not exist)
        splice_db.is_visible2d = False

        # the cable knows its sleeve before the view is made: the view sizes itself from the cable it is on
        self.db_obj.set_shield_splice_id(start, splice_db.db_id)

        sleeve = _splice_facade.Splice(self.mainframe, splice_db)
        self.mainframe.project.add_splice(sleeve)

        return sleeve

    @_check_types.do
    def _board_sleeve_pose(self, start: bool, length: float) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """Where the sleeve of one end lies on the board: from the split plane (its start, where the conductors leave) a *length* into
        the trunk (its stop), and the direction out of the trunk (the way a pigtail leaves it). ``None`` while the end has no length on
        the board."""
        frame = self.objpegboard._end_frame(start)  # NOQA

        if frame is None:
            return None

        plane = np.asarray(frame[3], dtype=np.float64)
        inward = np.asarray(frame[1], dtype=np.float64)

        return plane, plane + inward * length, -inward

    @_check_types.do
    def _place_sleeve_on_board(self, start: bool, splice_db, part) -> bool:
        """Put the three board points of a sleeve's row (start, stop, branch) where the sleeve lies on the board (user, 2026-11-12: they
        were left at the origin, so the sleeve was not on the board). ``False`` while the end has no place on the board.

        :param start: Which end of the cable.
        :type start: bool
        :param splice_db: The sleeve's row.
        :param part: The catalog sleeve.
        """
        shape = _sleeve_shape.sizes(float(self.db_obj.part.trunk_size[0]), part.min_dia, part.max_dia, part.length)
        pose = self._board_sleeve_pose(start, shape['length'])

        if pose is None:
            return False

        points = self.mainframe.project.ptables.pjt_points_pegboard_table
        held = []  # the rows stay referenced while their points move: the write-back to a row is a weak callback

        for point_id, target in ((splice_db.start_position_pegboard_id, pose[0]), (splice_db.stop_position_pegboard_id, pose[1]),
                                 (splice_db.branch_position_pegboard_id, pose[0])):
            row = points[point_id]
            held.append(row)
            live = row.point
            delta = _point.Point(float(target[0]), 0.0, float(target[2])) - live

            if float(np.linalg.norm(delta.as_numpy)) > 1e-9:
                live += delta

        return True

    @_check_types.do
    def _sync_board_sleeve(self, start: bool) -> None:
        """Keep the sleeve of one end, and its pigtail, on the board's split plane after the cable moved on the board.

        The sleeve's three board points go to their place and its view turns to the new direction. The end of a pigtail that is on the
        sleeve goes to the plane; the other end goes along by the distance the plane moved, unless something is attached to it (it stays,
        and the pigtail stretches), as the free ends of the leads do (:meth:`_carry_free_leads`). A pigtail with no place on the board yet
        (made before the board knew sleeves: its ends are at the origin) is laid out straight from the sleeve."""
        sleeve = self.shield_sleeve(start)

        if sleeve is None:
            return

        row = sleeve.db_obj
        part = row.part
        shape = _sleeve_shape.sizes(float(self.db_obj.part.trunk_size[0]), part.min_dia, part.max_dia, part.length)
        pose = self._board_sleeve_pose(start, shape['length'])

        if pose is None:
            return

        plane = _point.Point(float(pose[0][0]), 0.0, float(pose[0][2]))
        old = row.start_position_pegboard
        shift = plane - old

        self._place_sleeve_on_board(start, row, part)
        sleeve.objpegboard.reload_pose()

        points = self.mainframe.project.ptables.pjt_points_pegboard_table
        branch3d_id = row.branch_position3d_id
        held = []

        for wire in sleeve.branch_wires:
            wire_db = wire.db_obj
            at_stop = wire_db.stop_position3d_id == branch3d_id

            near = points[wire_db.stop_position_pegboard_id if at_stop else wire_db.start_position_pegboard_id]
            far = points[wire_db.start_position_pegboard_id if at_stop else wire_db.stop_position_pegboard_id]
            held.extend((near, far))

            near_live = near.point
            near_live += plane - near_live

            attached = wire.start_sibling is not None if at_stop else wire.stop_sibling is not None

            if attached:
                continue

            far_live = far.point

            if abs(float(far_live.x)) < 1e-9 and abs(float(far_live.z)) < 1e-9:
                reach = max(float(wire_db.length_mm), 1.0)
                target = _point.Point(float(plane.x + pose[2][0] * reach), 0.0, float(plane.z + pose[2][2] * reach))
                far_live += target - far_live
            elif float(np.linalg.norm(shift.as_numpy)) > 1e-9:
                far_live += shift

    @_check_types.do
    def _pigtail_start_length(self, start: bool, sleeve_length: float) -> float:
        """How long a catalog pigtail is when it is made (user, 2026-11-12): the same as the other conductors' leads of that end, but never
        past the cap: 150 mm measured from the MIDDLE of the sleeve (``sleeve.PIGTAIL_LENGTH_MM``), so at most 150 - length / 2 from the
        sleeve's end where the pigtail leaves it. It can be made shorter (and a drag can only shorten it past the cap).

        :param start: Which end.
        :type start: bool
        :param sleeve_length: The sleeve's length on the cable, mm.
        :type sleeve_length: float
        :returns: Mm from the sleeve's end at the split plane to the free end; at least 1.
        :rtype: float
        """
        cap = _sleeve_shape.PIGTAIL_LENGTH_MM - sleeve_length / 2.0

        # the other leads of the end (the shield's own is deleted by now)
        lengths = [float(lead.db_obj.length_mm) for lead in self.lead_wires(start) if lead.db_obj.length_mm]

        if lengths:
            reference = max(lengths)
        else:
            # no other lead to copy: how far the conductors fan out from the split plane
            reference = float(self.db_obj.start_split_mm if start else self.db_obj.stop_split_mm)

        if reference <= 0.0:
            reference = cap

        return max(min(reference, cap), 1.0)

    @_check_types.do
    def _make_pigtail(self, sleeve, pose: tuple[np.ndarray, np.ndarray], length: float, part_id: bytes, start: bool | None = None) -> None:
        """Make the pigtail of a sleeve that comes with one: a plain wire of the catalog part *part_id*, *length* mm long, leaving the
        sleeve's branch point (the sleeve's end at the split plane) straight out along the cable's axis. Its end on the sleeve is
        pinned (``WireDragMixin.is_anchor_point``); its free end is the user's to move, as any wire's."""
        from . import wire as _wire_facade  # NOQA -- avoid a cycle at import time

        ptables = self.mainframe.project.ptables
        outward = pose[0] - pose[1]
        outward = outward / max(float(np.linalg.norm(outward)), 1e-9)
        free = pose[0] + outward * length

        free_row = ptables.pjt_points3d_table.insert(*(float(v) for v in free))
        wire_db = ptables.pjt_wires_table.insert(
            part_id, 'Pigtail', None, free_row.db_id, sleeve.db_obj.branch_position3d_id, None, None, True, False, None, None, False)

        # on the board its end on the sleeve is the board's split plane and its free end is *length* out of the trunk (user, 2026-11-12: the
        # lead was at the origin on the board); the points are set before the wire's board view is made
        board = None if start is None else self._board_sleeve_pose(start, 0.0)

        if board is not None:
            pegs = ptables.pjt_points_pegboard_table
            free_peg = pegs.insert(float(board[0][0] + board[2][0] * length), 0.0, float(board[0][2] + board[2][2] * length))
            wire_db.start_position_pegboard_id = free_peg.db_id

            # the end on the sleeve is the sleeve's own branch point (already on the plane: _build_sleeve), as in 3D, so the
            # rope pull sees the lead as the sleeve's wire
            wire_db.stop_position_pegboard_id = sleeve.db_obj.branch_position_pegboard_id

        # in the schematic its end on the sleeve is the sleeve's own point (user's bug, 2026-11-12: it was a point of its own, so the
        # lead did not follow the sleeve when it was dragged and was not routed again), as a wire snapped onto a splice has it
        wire_db.stop_position2d_id = sleeve.db_obj.position2d_id

        wire = _wire_facade.Wire(self.mainframe, wire_db)
        self.mainframe.project.add_wire(wire)

        sleeve.add_wire(wire)
        wire.set_sibling(sleeve, wire.obj3d.stop_position)

    @_check_types.do
    def add_shield_sleeve(self, start: bool, part_id: bytes):
        """Put a solder sleeve on a split end of the shielded cable: a splice (``part_id`` is a ``splices`` row whose type is a shielding
        solder sleeve) lying along the trunk from the split plane, sized by the cable's diameter. The sleeve finishes the shield, so the
        shield's own lead is deleted. A sleeve that comes with a pigtail gets it: a plain wire as long as the other conductors' leads of
        that end (:meth:`_pigtail_start_length`), at most 150 mm from the middle of the sleeve
        (``sleeve.PIGTAIL_LENGTH_MM``, which is also the longest a drag can make it), set onto the sleeve's branch point at the split
        plane (that end is pinned). One without is
        a snap point: the user adds whatever wire they want to it (the snap rule is ``wire_snap.check_splice_compat``, one wire).

        :param start: Which end.
        :type start: bool
        :param part_id: The catalog splice.
        :type part_id: bytes
        :returns: The sleeve (the splice's facade).
        :raises ValueError: Raised when the cable cannot take one there (see :meth:`can_add_shield_sleeve`), when the part is not a
            solder sleeve, when the cable is not within the part's range of diameters or when the sleeve has a pigtail and the catalog
            has no wire for it.
        """
        db_obj = self.db_obj

        if not self.can_add_shield_sleeve(start):
            raise ValueError('a solder sleeve needs a shielded cable with this end split, no sleeve on it yet and nothing connected '
                             'to the shield\'s lead')

        ptables = self.mainframe.project.ptables
        part = ptables.global_db.splices_table[part_id]

        if not part.is_shielding_sleeve:
            raise ValueError('that part is not a shielding solder sleeve (type "Shielding Solder Sleeve")')

        diameter = float(db_obj.part.trunk_size[0])

        if not part.fits_cable(diameter):
            raise ValueError(f'a cable of {diameter:.2f} mm does not fit this sleeve ({part.min_dia:.2f} to {part.max_dia:.2f} mm)')

        shape = _sleeve_shape.sizes(diameter, part.min_dia, part.max_dia, part.length)
        pose = self._sleeve_pose(start, shape['length'])

        if pose is None:
            raise ValueError('the direction of the cable at this end is not known')

        pigtail_part = None

        if part.has_pigtail:
            pigtail_part = self._pigtail_part_id(part)

            if pigtail_part is None:
                raise ValueError('the catalog has no plain wire for the pigtail of this sleeve')

        # the sleeve takes the place of the shield's own lead
        lead = self._shield_lead(start)

        if lead is not None:
            lead.delete()

        sleeve = self._build_sleeve(start, part_id, part, pose, None)

        if pigtail_part is not None:
            self._make_pigtail(sleeve, pose, self._pigtail_start_length(start, shape['length']), pigtail_part, start)

        # in the schematic the cable's wires are routed together, side by side, once the cable has a sleeve (user, 2026-11-12)
        from ..wire_routing import reroute as _wire_reroute  # NOQA -- avoid a cycle at import time

        _wire_reroute.route_shield_group(self.mainframe.project, self)

        self.obj3d.editor3d.Refresh()
        return sleeve

    @_check_types.do
    def remove_shield_sleeve(self, start: bool, with_pigtail: bool = False) -> None:
        """Take the solder sleeve off one end. A pigtail that has nothing connected at its far end goes with the sleeve; one that is
        connected stays (it is left as a wire of its own, as with any splice), unless *with_pigtail*: the cable is being deleted, and
        the pigtail goes whatever it is connected to (user's bug, 2026-11-12: it was left behind). The shield's own lead is not made
        again: join the end and split it again for that.

        :param start: Which end.
        :type start: bool
        :param with_pigtail: Delete every wire on the sleeve, connected or not.
        :type with_pigtail: bool
        """
        sleeve = self.shield_sleeve(start)

        if sleeve is None:
            return

        branch_id = sleeve.db_obj.branch_position3d_id

        for wire in list(sleeve.branch_wires):
            far = wire.start_sibling if wire.db_obj.stop_position3d_id == branch_id else wire.stop_sibling

            if far is None or with_pigtail:
                wire.delete()

        sleeve.delete()
        self.obj3d.editor3d.Refresh()

    @_check_types.do
    def _sync_shield_sleeve(self, start: bool) -> None:
        """Keep the sleeve of one end on the split plane after the end moved (the cable was dragged, a waypoint moved, the split
        distance changed). A splice's angle is only worked out when it is made, so a sleeve that is out of place is made again; its
        branch point is kept and moved (the pigtail's end on it goes along), and the pigtail is put on the new sleeve."""
        sleeve = self.shield_sleeve(start)

        if sleeve is None:
            return

        row = sleeve.db_obj
        part = row.part
        shape = _sleeve_shape.sizes(float(self.db_obj.part.trunk_size[0]), part.min_dia, part.max_dia, part.length)
        pose = self._sleeve_pose(start, shape['length'])

        if pose is None:
            return

        near = (float(np.linalg.norm(row.start_position3d.as_numpy - pose[0])) < 1e-3 and
                float(np.linalg.norm(row.stop_position3d.as_numpy - pose[1])) < 1e-3)

        if near:
            return

        part_id = row.part_id
        branch_id = row.branch_position3d_id

        # the row is kept while the point moves: the point's write-back to it is a weak callback
        branch_row = self.mainframe.project.ptables.pjt_points3d_table[branch_id]
        live = branch_row.point
        delta = _point.Point(*(float(v) for v in pose[0])) - live

        if float(np.linalg.norm(delta.as_numpy)) > 1e-9:
            live += delta

        pigtails = sleeve.branch_wires

        # where the sleeve is in the schematic, and whether it is shown: the new row takes both over
        old_2d = row.position2d
        schematic_place = (float(old_2d.x), float(old_2d.y), float(old_2d.z))
        schematic_shown = bool(row.is_visible2d)
        ring_state = (row.ring_size, row.ring_dir, row.ring_hard)

        sleeve.delete(keep_branch=True)
        moved = self._build_sleeve(start, part_id, part, pose, branch_id)

        new_2d = moved.db_obj.position2d
        new_2d += _point.Point(*schematic_place) - new_2d
        moved.db_obj.is_visible2d = schematic_shown

        # the shield ring in the schematic (placed by the router, or by the user: hard set) belongs to the sleeve
        moved.db_obj.ring_size, moved.db_obj.ring_dir, moved.db_obj.ring_hard = ring_state
        moved.objschematic.reload_ring()

        for wire in pigtails:
            moved.add_wire(wire)
            at_stop = wire.db_obj.stop_position3d_id == branch_id
            end = wire.obj3d.stop_position if at_stop else wire.obj3d.start_position
            wire.set_sibling(moved, end)

            # on the board the lead's end is the new sleeve's branch point (the old one went with the old sleeve's row)
            board_branch = moved.db_obj.branch_position_pegboard

            if at_stop:
                wire.db_obj.stop_position_pegboard_id = moved.db_obj.branch_position_pegboard_id
                wire.objpegboard.set_stop_position(board_branch)
                wire.db_obj.stop_position2d_id = moved.db_obj.position2d_id
                wire.objschematic.set_stop_position(moved.db_obj.position2d)
            else:
                wire.db_obj.start_position_pegboard_id = moved.db_obj.branch_position_pegboard_id
                wire.objpegboard.set_start_position(board_branch)
                wire.db_obj.start_position2d_id = moved.db_obj.position2d_id
                wire.objschematic.set_start_position(moved.db_obj.position2d)

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
        self._slack_handler.release()

        for start in (True, False):
            self.remove_shield_sleeve(start, with_pigtail=True)

        junctions = []

        for start in (True, False):
            self._drop_split_markers(start)

            for lead in self.lead_wires(start):
                junctions.extend(self.lead_chain(lead)[1])

        # a row of a conductor's wire that has no object (it never loaded) would be left pointing at a conductor that is gone, and
        # the project would not open again
        wires_table = self.mainframe.project.ptables.pjt_wires_table
        without_object = []

        for conductor in self.db_obj.conductors:
            for wire_db in wires_table.leads_of(conductor.db_id):
                if wire_db.get_object() is None:
                    without_object.append(wire_db)

        for piece in self.conductor_wires():
            piece.delete()

        for wire_db in without_object:
            wire_db.delete()

        self._remove_junctions(junctions)

        for node in self._conductor_objects.values():
            node.delete()

        super().delete()

        self.mainframe.project.delete_cable(self.db_obj.db_id)
        self.db_obj.delete()
