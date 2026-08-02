# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from .objects2d import terminal as _terminal_2d
from .objects3d import terminal as _terminal_3d
from .objectspeg import terminal as _terminal_peg
from . import wire_layout as _wire_layout
from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_terminal as _pjt_terminal
    from . import wire as _wire_obj


class Terminal(_ObjectBase):
    """Represent a terminal in :mod:`harness_designer.objects.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _terminal_2d.Terminal = None
    obj3d: _terminal_3d.Terminal = None
    objpeg: _terminal_peg.Terminal = None
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

        self.obj2d = _terminal_2d.Terminal(self, db_obj)
        self.obj3d = _terminal_3d.Terminal(self, db_obj)
        self.objpeg = _terminal_peg.Terminal(self, db_obj)

        # Sibling graph: every Wire currently crimped into this terminal
        # (open-ended -- a terminal has no fixed start/stop shape, any
        # number of wires up to the combined cross-section max). See
        # add_wire and Wire.set_sibling.
        self._wire_refs = []

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
        :class:`~harness_designer.objects.wire_layout.WireLayout`. The
        terminal has only one 2D anchor (``position2d_id`` -- no separate
        attach/back distinction in the schematic view), so no 2D waypoints
        are added; the wire's 2D endpoint is simply ``position2d_id``.

        When this is not the first wire on the terminal, the back/cavity
        points can't be shared directly (one point row can only carry one
        wire's own ``wire_id``/``idx`` tag at a time) -- a fresh point is
        cloned at the same location for this wire instead, same as a
        splice's branch wires need on removal (see ``objects.splice.
        Splice.delete``'s TODO).

        :returns: False (adding nothing) if the combined cross-section of
            every wire already on this terminal plus *wire* would exceed
            the terminal's own ``wire_size_cross_max``.
        """
        if end not in ('start', 'stop'):
            raise ValueError(f"end must be 'start' or 'stop', got {end!r}")

        existing_wires = self.wires

        term_part = self.db_obj.part
        wire_part = wire.db_obj.part
        if term_part is not None and wire_part is not None and wire_part.size_mm2 is not None:
            cross_max = term_part.wire_size_cross_max
            if cross_max is not None:
                existing_cross = sum(
                    w.db_obj.part.size_mm2 for w in existing_wires
                    if w.db_obj.part is not None and w.db_obj.part.size_mm2 is not None)

                if existing_cross + wire_part.size_mm2 > cross_max:
                    return False

        ptables = self.mainframe.project.ptables
        project = self.mainframe.project
        is_first_wire = not existing_wires

        attach_point = ptables.pjt_points3d_table[self.db_obj.attach_point3d_id]

        if end == 'start':
            wire.db_obj.start_position3d_id = attach_point.db_id
            wire.db_obj.start_position2d_id = self.db_obj.position2d_id
            wire.obj3d.set_start_position(attach_point.point)
            wire.obj2d.set_start_position(self.db_obj.position2d)
        else:
            wire.db_obj.stop_position3d_id = attach_point.db_id
            wire.db_obj.stop_position2d_id = self.db_obj.position2d_id
            wire.obj3d.set_stop_position(attach_point.point)
            wire.obj2d.set_stop_position(self.db_obj.position2d)

        new_point_ids = [self._own_or_cloned_point_id(
            ptables, self.db_obj.wire_point3d_id, is_first_wire)]

        pjt_cavity = self.db_obj.cavity
        if pjt_cavity is not None:
            new_point_ids.append(self._own_or_cloned_point_id(
                ptables, pjt_cavity.wire_position3d_id, is_first_wire))

        # Walking start->stop: a start-attach puts the back/cavity points
        # first (before whatever waypoints already exist); a stop-attach
        # puts them last, in the opposite order (cavity before back).
        if end == 'stop':
            new_point_ids.reverse()

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

            layout_db = ptables.pjt_wire_layouts_table.insert(point_id)
            layout_obj = _wire_layout.WireLayout(self.mainframe, layout_db)
            project.add_wire_layout(layout_obj)

        wire.obj3d.refresh_waypoints()

        wire.set_sibling(self, end)
        self._wire_refs.append(weakref.ref(wire))

        return True

    @staticmethod
    @_check_types.do
    def _own_or_cloned_point_id(ptables, shared_point_id: int, is_first_wire: bool) -> int:
        """The first wire on a terminal reuses its shared back/cavity
        point row directly (so it keeps tracking the terminal/cavity if
        the housing moves); every subsequent wire gets its own fresh point
        cloned at the same location, since a point row can only carry one
        wire's own wire_id/idx tag at a time."""
        if is_first_wire:
            return shared_point_id

        shared = ptables.pjt_points3d_table[shared_point_id]
        cloned = ptables.pjt_points3d_table.insert(shared.x, shared.y, shared.z)
        return cloned.db_id

    @_check_types.do
    def set_selected(self, flag):
        """Selecting a terminal selects its owning cavity instead.

        Terminals are never directly selectable — all manipulation of a
        terminal happens through the cavity it's placed in.
        """
        if flag:
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
        # The attached-wire dangling/repointing and the internal wire-routing
        # stub/layout cleanup (see handlers.wire_handler._route_from_terminal)
        # live on obj3d's own _delete() -- that's 3D-view geometry/position
        # work, not wrapper-level cascade.
        seal = self.db_obj.seal
        if seal is not None:
            seal_obj = seal.get_object()
            if seal_obj is not None:
                seal_obj.delete()

        super().delete()
        self.mainframe.project.delete_terminal(self.db_obj.db_id)
        self.db_obj.delete()
