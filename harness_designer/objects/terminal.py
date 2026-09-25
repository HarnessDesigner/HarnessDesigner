# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import weakref

from . import ObjectBase as _ObjectBase
from .objects_schematic import terminal as _terminal_schematic
from .objects_3d import terminal as _terminal_3d
from .objects_pegboard import terminal as _terminal_pegboard
from .objects_pegboard import base_pegboard as _base_pegboard
from ..wire_routing import reroute as _wire_reroute
from . import wire_layout as _wire_layout
from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_terminal as _pjt_terminal
    from . import wire as _wire_obj


# The editors (``CanvasBase._editor_name``) in which selecting a terminal selects
# the cavity it sits in instead -- see Terminal.set_selected.
_CAVITY_SELECTING_EDITORS = ('editor3d', 'editor_pegboard')


class Terminal(_ObjectBase):
    """Represent a terminal in :mod:`harness_designer.objects.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _terminal_schematic.Terminal = None
    obj3d: _terminal_3d.Terminal = None
    objpegboard: _terminal_pegboard.Terminal = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_terminal.PJTTerminal", project_load=False):
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj3d = _terminal_3d.Terminal(self, db_obj)
        self.objpegboard = _terminal_pegboard.Terminal(self, db_obj)
        self.objschematic = _terminal_schematic.Terminal(self, db_obj)

        # Sibling graph: every Wire currently crimped into this terminal
        # (open-ended -- a terminal has no fixed start/stop shape, any
        # number of wires up to the combined cross-section max). See
        # add_wire and Wire.set_sibling.
        self._wire_refs: list[weakref.ReferenceType] = []

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def wires(self) -> list["_wire_obj.Wire"]:
        """Every Wire currently attached to this terminal."""
        alive = []
        result = []

        for ref in self._wire_refs:
            obj = ref()
            if obj is not None:
                alive.append(ref)
                result.append(obj)

        self._wire_refs = alive
        return result

    @_check_types.do
    def replace_wire(self, old_wire: "_wire_obj.Wire", new_wire: "_wire_obj.Wire") -> None:
        """Swap *old_wire* for *new_wire* in this terminal's own attached-
        wire list, in place, preserving position.

        Used when a wire attached to this terminal gets forked or merged
        elsewhere along its length (handlers.wire_topology) -- the
        terminal's own end of the relationship doesn't change, only
        which Wire object represents that end now.
        """
        for i, ref in enumerate(self._wire_refs):
            if ref() is old_wire:
                self._wire_refs[i] = weakref.ref(new_wire)
                return

    @_check_types.do
    def add_wire(self, wire: "_wire_obj.Wire", end: str) -> bool:
        """Attach *wire*'s *end* ('start' or 'stop') to this terminal.

        Extends *wire*'s own route through this terminal's back point
        (``wire_point3d_id``) and, when seated in a cavity, on through the
        cavity's own wire-position point -- as interior waypoints on this
        *same* wire (no new ``pjt_wires`` rows), each marked with its own
        :class:`~harness_designer.objects.wire_layout.WireLayout`. No 2D
        waypoints are added -- the wire's 2D endpoint is simply this
        terminal's own ``wire_position2d_id`` (the far end of its
        wire-stub line, past every cavity name in the housing -- see
        ``objects_schematic/terminal.py``'s ``Terminal.__init__``/
        ``Terminal.render`` -- distinct from ``position2d_id``, this
        terminal's own name anchor).

        When this is not the first wire on the terminal, the back/cavity
        points can't be shared directly (one point row can only carry one
        wire's own ``wire_id``/``idx`` tag at a time) -- a fresh point is
        cloned at the same location for this wire instead, same as a
        splice's branch wires need on removal (see ``objects.splice.
        Splice.delete``'s TODO).

        Never refuses based on combined cross-section exceeding the
        terminal's own ``wire_size_cross_max`` -- confirmed 2026-08-06:
        only the upper bound is ever a concern, and even that should never
        actually block the connection (there's no way to know whether more
        wires are still going to be attached later; a future design-rules
        checker is the right place to flag it, not here). See
        ``handlers.wire_snap.check_terminal_compat``, which the interactive
        placement/drag code already calls before this to show a
        non-blocking capacity warning -- this method itself always
        performs the attachment.

        :returns: Always ``True`` -- kept as a return value (rather than
            ``None``) since existing callers already check it.
        """
        if end not in ('start', 'stop'):
            raise ValueError(f"end must be 'start' or 'stop', got {end!r}")

        existing_wires = self.wires

        ptables = self.mainframe.project.ptables
        project = self.mainframe.project
        is_first_wire = not existing_wires

        self._make_room_for_second_wire(len(existing_wires))

        attach_point = ptables.pjt_points3d_table[self.db_obj.attach_position3d_id]
        attach_point_pegboard = ptables.pjt_points_pegboard_table[
            self.db_obj.attach_position_pegboard_id]

        if end == 'start':
            wire.db_obj.start_position3d_id = attach_point.db_id
            wire.db_obj.start_position2d_id = self.db_obj.wire_position2d_id
            wire.db_obj.start_position_pegboard_id = attach_point_pegboard.db_id
            wire.obj3d.set_start_position(attach_point.point)
            wire.objschematic.set_start_position(self.db_obj.wire_position2d)
            wire.objpegboard.set_start_position(attach_point_pegboard.point)
        else:
            wire.db_obj.stop_position3d_id = attach_point.db_id
            wire.db_obj.stop_position2d_id = self.db_obj.wire_position2d_id
            wire.db_obj.stop_position_pegboard_id = attach_point_pegboard.db_id
            wire.obj3d.set_stop_position(attach_point.point)
            wire.objschematic.set_stop_position(self.db_obj.wire_position2d)
            wire.objpegboard.set_stop_position(attach_point_pegboard.point)

        new_point_ids = [self._own_or_cloned_point_id(
            ptables.pjt_points3d_table, self.db_obj.wire_position3d_id, is_first_wire)]
        new_point_pegboard_ids = [self._own_or_cloned_point_id(
            ptables.pjt_points_pegboard_table, self.db_obj.wire_position_pegboard_id,
            is_first_wire)]

        pjt_cavity = self.db_obj.cavity
        if pjt_cavity is not None:
            new_point_ids.append(self._own_or_cloned_point_id(
                ptables.pjt_points3d_table, pjt_cavity.wire_position3d_id, is_first_wire))
            new_point_pegboard_ids.append(self._own_or_cloned_point_id(
                ptables.pjt_points_pegboard_table, pjt_cavity.wire_position_pegboard_id,
                is_first_wire))

        # Walking start->stop: a start-attach puts the back/cavity points
        # first (before whatever waypoints already exist); a stop-attach
        # puts them last, in the opposite order (cavity before back).
        if end == 'stop':
            new_point_ids.reverse()
            new_point_pegboard_ids.reverse()

        existing_waypoints = wire.db_obj.waypoints3d
        n_new = len(new_point_ids)

        if end == 'start':
            for point in existing_waypoints:
                point.idx = point.idx + n_new
            offsets = range(n_new)
        else:
            base = len(existing_waypoints)
            offsets = range(base, base + n_new)

        for point_id, idx in zip(new_point_ids, offsets):
            point = ptables.pjt_points3d_table[point_id]
            point.wire_id = wire.db_obj.db_id
            point.idx = idx

            layout_db = ptables.pjt_wire_layouts_table.insert(point3d_id=point_id)
            layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

        # Peg-board waypoints are independent rows/idx sequence in their
        # own points table (see database.create_database.points_pegboard's
        # own module docstring on why waypoint counts genuinely differ
        # per view) -- offsets computed the same way, against the
        # peg-board view's own existing waypoint count, not the 3D one's.
        existing_waypoints_pegboard = wire.db_obj.waypoints_pegboard
        n_new_pegboard = len(new_point_pegboard_ids)

        if end == 'start':
            for point in existing_waypoints_pegboard:
                point.idx = point.idx + n_new_pegboard
            offsets_pegboard = range(n_new_pegboard)
        else:
            base = len(existing_waypoints_pegboard)
            offsets_pegboard = range(base, base + n_new_pegboard)

        for point_id, idx in zip(new_point_pegboard_ids, offsets_pegboard):
            point = ptables.pjt_points_pegboard_table[point_id]
            point.wire_id = wire.db_obj.db_id
            point.idx = idx

            layout_db = ptables.pjt_wire_layouts_table.insert(point_pegboard_id=point_id)
            layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

        wire.obj3d.refresh_waypoints()
        wire.objpegboard.refresh_waypoints()

        wire.set_sibling(self, end)
        self._wire_refs.append(weakref.ref(wire))

        # This terminal just became a junction (see
        # _make_room_for_second_wire, which already ran above): the ONE
        # wire that was already attached here had its route settled back
        # when this terminal still had its short, un-pushed stub -- its
        # own endpoint moved for free (it's bound to the same
        # wire_position2d Point this new wire now shares), but its
        # interior bends, if any, are stale relative to the new, further-
        # out attach point. Route it fresh FIRST -- junction wires claim
        # their lanes before anything else, see wire_routing.reroute.
        # is_junction_wire's own docstring -- so the new wire below routes
        # around an already-correct sibling instead of the other way
        # around.
        if len(existing_wires) == 1:
            _wire_reroute.reroute_wire(project, existing_wires[0])

        _wire_reroute.on_wire_attached(project, wire)

        cavity_db = self.db_obj.cavity
        if cavity_db is not None:
            cavity_obj = cavity_db.get_object()
            if cavity_obj is not None and cavity_obj.housing is not None:
                _base_pegboard.notify_table_wires_changed(cavity_obj.housing.db_obj)

        return True

    # How close (in scene units, in any one view) a wire's free end has to be
    # to a newly placed terminal's wire-side point for reconnect_free_wires
    # to infer the wire was cut from a terminal that used to sit there.
    _RECONNECT_TOLERANCE = 0.5

    @_check_types.do
    def detach_wires(self) -> None:
        """Cut every wire attached to this terminal free, in all three views.

        Which point is the cut depends on the view (see :meth:`add_wire`,
        which builds this route):

        - 3D/peg-board: the wire's real end is the terminal's crimp point
          (``attach_position``), with interior waypoints (each with its own
          WireLayout) at the terminal's own back point and, when seated, the
          cavity's wire-side point. The wire is trimmed back to the
          outermost of those -- the cavity's when seated, otherwise the
          terminal's own -- which becomes the wire's new free end, and the
          waypoints at/inside it (with their layouts) are removed.
        - Schematic: the wire's end is the terminal's ``wire_position2d``
          (the far end of its stub). The wire keeps that location as its
          free end.

        In every view the free end gets its own brand-new point row, so
        nothing is left shared with this terminal or its cavity. That
        location is what :meth:`reconnect_free_wires` later matches a
        replacement terminal against.

        Which end of the wire was attached comes from the sibling graph, not
        from proximity.
        """
        for wire in list(self.wires):
            if wire.start_sibling is self:
                end = 'start'
            elif wire.stop_sibling is self:
                end = 'stop'
            else:
                continue

            self._detach_wire_waypoints(wire, end, '3d')
            self._detach_wire_waypoints(wire, end, 'pegboard')
            self._detach_wire_2d(wire, end)

            wire.set_sibling(None, end)

        self._wire_refs = []

    @_check_types.do
    def _detach_wire_waypoints(self, wire: "_wire_obj.Wire", end: str, view: str) -> None:
        """3D (``view='3d'``) or peg-board (``view='pegboard'``) half of
        :meth:`detach_wires` for one wire end."""
        ptables = self.mainframe.project.ptables
        db_obj = self.db_obj
        cavity = db_obj.cavity
        wire_db = wire.db_obj

        if view == '3d':
            points_table = ptables.pjt_points3d_table
            layout_column = 'point3d_id'
            waypoints = wire_db.waypoints3d
            view_obj = wire.obj3d
            end_attr = f'{end}_position3d_id'
            back_id = db_obj.wire_position3d_id_raw

            if cavity is not None:
                cavity_id = cavity.wire_position3d_id_raw
            else:
                cavity_id = None
        else:
            points_table = ptables.pjt_points_pegboard_table
            layout_column = 'point_pegboard_id'
            waypoints = wire_db.waypoints_pegboard
            view_obj = wire.objpegboard
            end_attr = f'{end}_position_pegboard_id'
            back_id = db_obj.wire_position_pegboard_id_raw

            if cavity is not None:
                cavity_id = cavity.wire_position_pegboard_id_raw
            else:
                cavity_id = None

        # The canonical rows belong to the terminal/cavity, not to the wire:
        # they are only untagged from it, never deleted (the cavity keeps its
        # own wire-side point for the next terminal/wire). Any other wire
        # attached here got its own child row (parent_point_id, see
        # _own_or_cloned_point_id), which is the wire's own to delete.
        canonical_ids = {i for i in (back_id, cavity_id) if i is not None}
        if not canonical_ids:
            return

        if cavity_id is not None:
            outer_id = cavity_id
        else:
            outer_id = back_id

        new_point = points_table.insert(*points_table[outer_id].point.as_float)
        setattr(wire_db, end_attr, new_point.db_id)

        if end == 'start':
            view_obj.set_start_position(new_point.point)
        else:
            view_obj.set_stop_position(new_point.point)

        removed = []
        remaining = []

        for wp in waypoints:
            if wp.db_id in canonical_ids or wp.parent_point_id in canonical_ids:
                removed.append(wp)
            else:
                remaining.append(wp)

        layouts_table = ptables.pjt_wire_layouts_table

        for wp in removed:
            for row in layouts_table.select('id', **{layout_column: wp.db_id}):
                layout_db = layouts_table[row[0]]
                layout_obj = layout_db.get_object()

                if layout_obj is not None:
                    layout_obj.delete()
                else:
                    layout_db.delete()
                break

            wp.wire_id = None
            wp.idx = None

            if wp.db_id not in canonical_ids:
                wp.delete()

        for i, wp in enumerate(remaining):
            wp.idx = i

        view_obj.refresh_waypoints()

    @_check_types.do
    def _detach_wire_2d(self, wire: "_wire_obj.Wire", end: str) -> None:
        """Schematic half of :meth:`detach_wires` for one wire end."""
        ptables = self.mainframe.project.ptables
        stub_id = self.db_obj.wire_position2d_id_raw

        if stub_id is None:
            return

        new_point = ptables.pjt_points2d_table.insert(
            *ptables.pjt_points2d_table[stub_id].point.as_float)

        if end == 'start':
            wire.db_obj.start_position2d_id = new_point.db_id
            wire.objschematic.set_start_position(new_point.point)
        else:
            wire.db_obj.stop_position2d_id = new_point.db_id
            wire.objschematic.set_stop_position(new_point.point)

    @_check_types.do
    def reconnect_free_wires(self) -> None:
        """Reattach any wire whose free end sits where this newly placed
        terminal's wire-side point is -- the "wrong terminal, replace it"
        case (see :meth:`detach_wires`, which leaves a cut wire's end at
        exactly that spot).

        Seated in a cavity, the spot is the cavity's own wire-side point;
        otherwise it is this terminal's own back point. A wire end matches
        when it is within ``_RECONNECT_TOLERANCE`` of that spot in any one
        of the three views (the schematic one is only compared when this
        terminal's stub point has actually been computed) and is not already
        attached to something.
        """
        project = self.mainframe.project
        db_obj = self.db_obj
        cavity = db_obj.cavity

        if cavity is not None:
            target3d = cavity.wire_position3d
            target_pegboard = cavity.wire_position_pegboard
        else:
            target3d = db_obj.wire_position3d
            target_pegboard = db_obj.wire_position_pegboard

        if db_obj.wire_position2d_id_raw is not None:
            target2d = db_obj.wire_position2d
        else:
            target2d = None

        matches = []

        for wire in project.wires:
            wire_db = wire.db_obj

            for end in ('start', 'stop'):
                if end == 'start':
                    sibling = wire.start_sibling
                else:
                    sibling = wire.stop_sibling

                if sibling is not None:
                    continue

                ends = (
                    (target3d, getattr(wire_db, f'{end}_position3d')),
                    (target_pegboard, getattr(wire_db, f'{end}_position_pegboard')),
                    (target2d, getattr(wire_db, f'{end}_position2d')))

                for target, end_point in ends:
                    if target is None or end_point is None:
                        continue

                    if math.dist(target.as_float, end_point.as_float) <= self._RECONNECT_TOLERANCE:
                        matches.append((wire, end))
                        break

        ptables = project.ptables

        for wire, end in matches:
            wire_db = wire.db_obj

            stale_ends = (
                (ptables.pjt_points3d_table, getattr(wire_db, f'{end}_position3d_id')),
                (ptables.pjt_points_pegboard_table, getattr(wire_db, f'{end}_position_pegboard_id')),
                (ptables.pjt_points2d_table, getattr(wire_db, f'{end}_position2d_id')))

            self.add_wire(wire, end)

            # add_wire pointed the wire at this terminal's own points; the
            # free-end rows detach_wires made are now unused. delete() is a
            # no-op for anything still referenced.
            for table, point_id in stale_ends:
                if point_id is not None:
                    table[point_id].delete()

    # The floor on how far _junction_push_length pushes wire_position2d out,
    # as a multiple of this terminal's own original (un-extended) stub
    # length -- see that method's own docstring for when it pushes further.
    _JUNCTION_PUSH_MULTIPLIER = 3.0

    @_check_types.do
    def _make_room_for_second_wire(self, existing_wire_count: int) -> None:
        """Schematic-view only: push this terminal's own ``wire_position2d``
        further out, once, the moment it is about to gain its SECOND wire.

        Unlike the 3D/peg-board views (see :meth:`_own_or_cloned_point_id`),
        a terminal has no per-wire clone of its own wire attach point in the
        schematic view -- ``add_wire`` points every wire's own
        ``start_position2d_id``/``stop_position2d_id`` straight at this
        SAME shared ``wire_position2d`` (see that method's own docstring).
        A single wire there is fine -- but a second one arriving at that
        exact point, right at the terminal's own pin edge, has nowhere to
        run without overlapping the first wire's own mandatory exit stub.
        So the moment a terminal's wire count is about to go from one to
        two, this moves that ONE shared point further out (see
        :meth:`_junction_push_length` for how far), straight along the
        direction the rendered wire-stub cylinder is already headed --
        giving every wire that ends there (the existing one included,
        since they all share this one Point) room to actually fan out and
        keep proper lane spacing from each other. A 3rd/4th/... wire finds
        it already moved and this is a no-op.

        Deliberately nothing more than moving a Point already in place for
        exactly this purpose, plus a purely visual marker at the new spot
        (see ``Terminal.render``'s own ``wire_junction`` sphere pass) -- no
        new object, no new database row/table.
        """
        if existing_wire_count != 1:
            return

        term_schematic = self.objschematic
        cyl_start = term_schematic._cylinder_start  # NOQA
        wire_pos = self.db_obj.wire_position2d

        if cyl_start is None or wire_pos is None:
            return

        dx = float(wire_pos.x) - float(cyl_start.x)
        dz = float(wire_pos.z) - float(cyl_start.z)
        base_length = math.hypot(dx, dz)
        if base_length < 1e-6:
            return

        push_length = self._junction_push_length(base_length)
        ux, uz = dx / base_length, dz / base_length

        with wire_pos:
            wire_pos.x = float(cyl_start.x) + ux * push_length
            wire_pos.z = float(cyl_start.z) + uz * push_length

        # The rendered stub cylinder's own length/angle aren't bound to
        # wire_position2d itself -- only recomputed when this terminal's own
        # housing-relative geometry is (see Terminal._update_position's own
        # docstring) -- so ask for that same recompute now, rather than
        # leaving the cylinder pointing at its old, un-extended length until
        # something else happens to move this terminal next.
        term_schematic._update_position(term_schematic.position)  # NOQA

    @_check_types.do
    def _junction_push_length(self, base_length: float) -> float:
        """How far out (from this terminal's own ``_cylinder_start``, along
        the shared stub direction) :meth:`_make_room_for_second_wire`
        should push ``wire_position2d`` -- always a whole-number MULTIPLE
        of *base_length* (this terminal's own original, un-extended stub
        length, the same for every terminal in the housing -- see
        ``Terminal``'s own docstring), starting at
        ``_JUNCTION_PUSH_MULTIPLIER`` (3x) and stepped up one whole
        multiple at a time (4x, 5x, ...) only as far as needed.

        A STATIC 3x was enough to just barely cause a real bug: every
        terminal in a housing shares the same stub direction and the same
        row pitch (``geometry.cavity_layout.compute_stack_geometry``), so a
        fixed multiplier can land this terminal's own junction point at the
        exact same depth a NEIGHBOURING terminal's wire(s) already need to
        bend at -- landing two different wires' routed 90-degree turns
        (and their ``WireLayout`` handles) on top of each other (confirmed
        2026-09-22, Kevin).

        Since every terminal in this housing starts from that SAME
        *base_length*, a neighbour's own current reach -- pushed out
        itself, if it's a junction too -- already sits on that same whole-
        multiple step lattice; there's never a need to land in between two
        steps. So: look at whichever terminal seated in an IMMEDIATELY
        ADJACENT cavity row (directly above or below this one in the
        housing's own stack order -- found by row pitch, not name/index,
        since natural-sort stack order isn't stored on ``CavityGeometry``
        itself) reaches furthest along that same shared direction, and if
        this terminal's own starting multiplier wouldn't already clear past
        it, this terminal's own multiplier becomes that neighbour's own
        multiplier PLUS one whole step -- otherwise the starting multiplier
        is already enough, unchanged.

        Only DIRECT neighbours are considered, not a recursive walk further
        out the stack -- a neighbour's own reach already accounts for ITS
        neighbours (this exact method, run for it whenever IT became a
        junction), so it's already the furthest anything on its far side
        can be.
        """
        multiplier = self._JUNCTION_PUSH_MULTIPLIER

        cavity = self.db_obj.cavity
        if cavity is None:
            return base_length * multiplier

        housing = cavity.housing
        if housing is None:
            return base_length * multiplier

        geometry = housing.cavity_geometry.get(cavity.db_id)
        if geometry is None:
            return base_length * multiplier

        pitch = geometry.cavity_height
        this_z = geometry.position[1]

        for other_cavity in housing.cavities:
            if other_cavity.db_id == cavity.db_id:
                continue

            other_geometry = housing.cavity_geometry.get(other_cavity.db_id)
            if other_geometry is None:
                continue

            # Immediate stack neighbour: exactly one row-pitch away, not any
            # other cavity in the housing.
            if abs(abs(other_geometry.position[1] - this_z) - pitch) > 1e-3:
                continue

            neighbor_terminal_row = other_cavity.terminal
            if neighbor_terminal_row is None:
                continue

            neighbor = neighbor_terminal_row.get_object()
            if neighbor is None:
                continue

            n_cyl_start = neighbor.objschematic._cylinder_start  # NOQA
            n_wire_pos = neighbor.db_obj.wire_position2d

            if n_cyl_start is None or n_wire_pos is None:
                continue

            reach = math.hypot(float(n_wire_pos.x) - float(n_cyl_start.x),
                               float(n_wire_pos.z) - float(n_cyl_start.z))

            # Rounded, not floor-divided: float noise from the rotate/
            # translate math that produced n_cyl_start/n_wire_pos (the same
            # accumulation noted in reroute._terminal_exit_stub_point's own
            # docstring) could otherwise knock an exact multiple down by a
            # whole step.
            neighbor_multiplier = round(reach / base_length)

            if neighbor_multiplier >= multiplier:
                multiplier = neighbor_multiplier + 1

        return base_length * multiplier

    @staticmethod
    @_check_types.do
    def _own_or_cloned_point_id(points_table: object, shared_point_id: bytes, is_first_wire: bool) -> bytes:
        """The first wire on a terminal reuses its shared back/cavity
        point row directly (so it keeps tracking the terminal/cavity if
        the housing moves); every subsequent wire gets its own fresh point
        cloned at the same location, since a point row can only carry one
        wire's own wire_id/idx tag at a time.

        The clone's own ``parent_point_id`` is set to *shared_point_id* --
        the real, canonical point -- so it still tracks that point's own
        future movement instead of being left behind: see
        ``pjt_housing.PJTHousing._update_position3d``/``_update_angle3d``,
        which look up every clone of a terminal's/cavity's own wire-side
        points by this column and move them along with their parent.

        :param points_table: The specific points table this shared point
            belongs to (``pjt_points3d_table`` or
            ``pjt_points_pegboard_table``) -- both share the same
            ``x``/``y``/``z``/``insert``/``parent_point_id`` shape, so
            this works unchanged for either.
        """
        if is_first_wire:
            return shared_point_id

        shared = points_table[shared_point_id]
        cloned = points_table.insert(shared.x, shared.y, shared.z)
        cloned.parent_point_id = shared_point_id
        return cloned.db_id

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Selecting a terminal selects its owning cavity instead.

        That is so in the 3D view and the peg board only -- all manipulation
        of a terminal there happens through the cavity it's placed in. In the
        schematic a terminal's name is its own click target (see
        objects_schematic/terminal.py), so the terminal itself is selected.
        The editor a click came from is what the mouse handler leaves in
        ``mainframe._selection_source_editor`` just before it selects (see
        MouseHandlerBase.on_left_up).
        """
        if flag and self.mainframe._selection_source_editor in _CAVITY_SELECTING_EDITORS:  # NOQA
            cavity = self.db_obj.cavity
            cavity_obj = cavity.get_object() if cavity is not None else None
            if cavity_obj is not None:
                cavity_obj.set_selected(True)
                return

        super().set_selected(flag)

    @property
    @_check_types.do
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.wire_position3d

    @_check_types.do
    def delete(self):
        seal = self.db_obj.seal
        if seal is not None:
            seal_obj = seal.get_object()
            if seal_obj is not None:
                seal_obj.delete()

        # Cut attached wires free before anything view-side is torn down --
        # needs the terminal's own points and cavity link still intact.
        self.detach_wires()

        super().delete()
        self.mainframe.project.delete_terminal(self.db_obj.db_id)
        self.db_obj.delete()
