# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from .objects_schematic import splice as _splice_schematic
from .objects3d import splice as _splice_3d
from .objectspeg import splice as _splice_peg
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_splice as _pjt_splice
    from . import wire as _wire_obj


class Splice(_ObjectBase):
    """Represent a splice in :mod:`harness_designer.objects.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _splice_schematic.Splice = None
    obj3d: _splice_3d.Splice = None
    objpeg: _splice_peg.Splice = None
    db_obj: "_pjt_splice.PJTSplice" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_splice.PJTSplice", project_load=False):
        """Initialise the :class:`Splice` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _splice_schematic.Splice(self, db_obj)
        self.obj3d = _splice_3d.Splice(self, db_obj)
        self.objpeg = _splice_peg.Splice(self, db_obj)

        # Sibling graph: the fixed through-pair (start/stop -- exactly one
        # wire each, set together via set_siblings when this splice is
        # placed into an existing wire) plus the open-ended branch list
        # (add_wire, any number of wires up to whatever the part's
        # diameter allows -- no limit enforced yet, see the "bus vs.
        # crimped" TODO at the top of database.project_db.pjt_splice).
        self._start_sibling_ref = None
        self._stop_sibling_ref = None
        self._branch_wire_refs = []

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def start_sibling(self) -> "_wire_obj.Wire | None":
        return None if self._start_sibling_ref is None else self._start_sibling_ref()

    @property
    @_check_types.do
    def stop_sibling(self) -> "_wire_obj.Wire | None":
        return None if self._stop_sibling_ref is None else self._stop_sibling_ref()

    @property
    @_check_types.do
    def branch_wires(self) -> list["_wire_obj.Wire"]:
        """Every wire attached to this splice's branch point."""
        alive = []
        result = []

        for ref in self._branch_wire_refs:
            obj = ref()
            if obj is not None:
                alive.append(ref)
                result.append(obj)

        self._branch_wire_refs = alive
        return result

    @property
    @_check_types.do
    def wires(self) -> list["_wire_obj.Wire"]:
        """Every wire attached to this splice -- through-pair plus branch."""
        result = []
        if self.start_sibling is not None:
            result.append(self.start_sibling)
        if self.stop_sibling is not None:
            result.append(self.stop_sibling)
        result.extend(self.branch_wires)
        return result

    @_check_types.do
    def set_siblings(self, wire_a: "_wire_obj.Wire", wire_b: "_wire_obj.Wire") -> None:
        """Record *wire_a*/*wire_b* as this splice's through-pair.

        Which of the two goes on the start side vs. the stop side is
        determined by matching each wire's own start/stop point id against
        this splice's ``start_position3d_id``/``stop_position3d_id`` --
        reliable here because the fork that creates *wire_a*/*wire_b*
        (handlers.splice_handler) always builds them with endpoints
        already set to those exact shared point ids.

        One-sided, same as Wire.set_sibling: callers are also responsible
        for calling ``wire.set_sibling(self, end)`` on each wire.
        """
        start_id = self.db_obj.start_position3d_id
        stop_id = self.db_obj.stop_position3d_id

        for wire in (wire_a, wire_b):
            w_start = wire.db_obj.start_position3d_id
            w_stop = wire.db_obj.stop_position3d_id

            if start_id in (w_start, w_stop):
                self._start_sibling_ref = weakref.ref(wire)
            elif stop_id in (w_start, w_stop):
                self._stop_sibling_ref = weakref.ref(wire)

    @_check_types.do
    def add_wire(self, wire: "_wire_obj.Wire") -> None:
        """Attach *wire* to this splice's branch point.

        No stub geometry or WireLayout is created -- the wire's endpoint
        lands exactly on the splice's own branch point, the splice's own
        mesh already marks the junction.
        """
        self._branch_wire_refs.append(weakref.ref(wire))

    @_check_types.do
    def replace_wire(self, old_wire: "_wire_obj.Wire", new_wire: "_wire_obj.Wire") -> None:
        """Swap *old_wire* for *new_wire* wherever it currently sits
        (start, stop, or branch), preserving position/role.

        Used when a wire attached to this splice gets forked or merged
        elsewhere along its length (handlers.wire_topology) -- this
        splice's own end of the relationship doesn't change, only which
        Wire object represents that end now.
        """
        if self._start_sibling_ref is not None and self._start_sibling_ref() is old_wire:
            self._start_sibling_ref = weakref.ref(new_wire)
            return

        if self._stop_sibling_ref is not None and self._stop_sibling_ref() is old_wire:
            self._stop_sibling_ref = weakref.ref(new_wire)
            return

        for i, ref in enumerate(self._branch_wire_refs):
            if ref() is old_wire:
                self._branch_wire_refs[i] = weakref.ref(new_wire)
                return

    @_check_types.do
    def delete(self):
        """Reconnect the through-pair back into a single wire (undoing
        the fork handlers.splice_handler made when this splice was
        placed), and give each branch wire its own fresh point at the
        same location before actually deleting this splice -- a branch
        is a dead end, not a through-path, so those wires are simply left
        dangling rather than reconnected to anything.
        """
        from ..handlers import wire_topology as _wire_topology

        project = self.mainframe.project
        ptables = project.ptables

        wire_a = self.start_sibling
        wire_b = self.stop_sibling
        if wire_a is not None and wire_b is not None:
            _wire_topology.merge_wires(project, wire_a, wire_b)

        branch_point_id = self.db_obj.branch_position3d_id
        branch_pos = self.db_obj.branch_position3d

        for branch_wire in self.branch_wires:
            is_start = branch_wire.obj3d.start_position.db_id[:-2] == branch_point_id

            new_point = ptables.pjt_points3d_table.insert(
                branch_pos.x, branch_pos.y, branch_pos.z)

            if is_start:
                branch_wire.db_obj.start_position3d_id = new_point.db_id
                branch_wire.obj3d.set_start_position(new_point.point)
            else:
                branch_wire.db_obj.stop_position3d_id = new_point.db_id
                branch_wire.obj3d.set_stop_position(new_point.point)

        super().delete()
        project.delete_splice(self.db_obj.db_id)
        self.db_obj.delete()
