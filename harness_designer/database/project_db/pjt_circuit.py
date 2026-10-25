# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Any, Iterable as _Iterable, TYPE_CHECKING, Union as _Union

from collections import deque
import contextlib
import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import (
    PJTEntryBase, PJTTableBase,
    DefaultStoredValue, DefaultStoredValueType
)
from . import circuit_solver as _circuit_solver
from ...geometry.decimal import Decimal as _d
from .mixins import (
    NameMixin,
    NotesMixin, NotesControl
)
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from ...objects import circuit as _circuit_obj
    from ...objects import project as _project_obj
    from ...ui.prop_ctrls import events as _prop_events


# What the Return Path field shows for each ReturnType.
_RETURN_TYPE_LABELS = {
    _circuit_solver.ReturnType.CHASSIS: 'Chassis',
    _circuit_solver.ReturnType.MIRRORED: 'Mirrored',
}


class PJTCircuitsTable(PJTTableBase):
    """Represent a PJT circuits table in :mod:`harness_designer.database.project_db.pjt_circuit`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_circuits'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import circuits

        return circuits.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import circuits

        circuits.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import circuits

        circuits.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTCircuit"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTCircuit']
        """

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCircuit(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTCircuit":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTCircuit`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTCircuit or item in self:
                return PJTCircuit(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(
            self, circuit_num: int, name: str = '', description: str = '',
            return_type: _circuit_solver.ReturnType = _circuit_solver.ReturnType.CHASSIS) -> "PJTCircuit":
        """Insert a circuit row.

        Does not check ``circuit_num`` for a duplicate -- look the number up
        with :meth:`get_by_num` first, or take :meth:`next_circuit_num`.

        :param circuit_num: The circuit's number within the project.
        :type circuit_num: int
        :param name: The circuit's name.
        :type name: str
        :param description: The circuit's description.
        :type description: str
        :param return_type: How the circuit's current returns to its source.
        :type return_type: :class:`_circuit_solver.ReturnType`
        :returns: The new circuit row.
        :rtype: :class:`PJTCircuit`
        """
        db_id = PJTTableBase.insert(
            self, circuit_num=circuit_num, name=name, notes='',
            description=description, return_type=int(return_type))

        return PJTCircuit(self, db_id)

    @_check_types.do
    def get_by_num(self, circuit_num: int) -> _Union["PJTCircuit", None]:
        """Return this project's circuit with the given number.

        The table cache holds only this project's rows, so no id-range
        filter is needed.

        :param circuit_num: The circuit number to look up.
        :type circuit_num: int
        :returns: The circuit, or ``None`` when no circuit has that number.
        :rtype: :class:`PJTCircuit` | None
        """
        db_ids = self.select('id', circuit_num=circuit_num)
        if not db_ids:
            return None

        return self[db_ids[0][0]]

    @_check_types.do
    def get_by_name(self, name: str) -> _Union["PJTCircuit", None]:
        """Return this project's circuit with the given name.

        :param name: The circuit name to look up.
        :type name: str
        :returns: The circuit, or ``None`` when no circuit has that name.
        :rtype: :class:`PJTCircuit` | None
        """
        db_ids = self.select('id', name=name)
        if not db_ids:
            return None

        return self[db_ids[0][0]]

    @_check_types.do
    def next_circuit_num(self) -> int:
        """Return the lowest circuit number above every number in use.

        :returns: ``1`` for a project with no circuits, otherwise the highest
            circuit number plus one.
        :rtype: int
        """
        rows = self.select('circuit_num')
        if not rows:
            return 1

        return max(row[0] for row in rows) + 1

    @_check_types.do
    def members_changed(self, *circuit_ids: bytes | None) -> None:
        """Drop the cached member lists of the named circuits.

        Called by every wire, service loop, splice and terminal when it
        joins, leaves or is deleted from a circuit, and by a terminal when its
        ``is_start`` flips. A circuit with no live :class:`PJTCircuit` has
        nothing cached, so it is skipped.

        :param circuit_ids: The circuits whose membership changed. ``None``
            (a member with no circuit) is ignored.
        :type circuit_ids: bytes | None
        """
        for circuit_id in circuit_ids:
            if circuit_id is None:
                continue

            if circuit_id in PJTCircuit:
                PJTCircuit(self, circuit_id).invalidate_members()

    # how many callers are holding chain propagation off (see propagation_paused)
    _propagation_paused: int = 0

    @contextlib.contextmanager
    def propagation_paused(self):
        """Hold chain propagation off while the caller places members itself.

        A ``circuit_id`` setter calls :meth:`propagate`; code that moves several members, or that has rules of its own about the
        order (``PJTCircuit.add_member``'s start terminal), pauses it, does its moves, and calls :meth:`propagate` once at the end.
        """
        self._propagation_paused += 1

        try:
            yield
        finally:
            self._propagation_paused -= 1

    @_check_types.do
    def connected_members(self, member: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> list[_Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop"]]:
        """Return *member* and every wire, splice, wire service loop and terminal connected to it.

        This is the whole chain, whatever circuit anything in it is in. Connectivity is read from the 3D point ids every view writes
        when a wire is attached (the same ones ``PJTCircuit._trace_full`` uses): a terminal has one connection point, a splice three,
        a wire service loop two, and a wire joins the junctions that own its two end points. It walks the way :func:`_walk_circuit`
        does, through every connection point of a junction.

        :param member: The row to start from.
        :type member: :class:`_pjt_wire.PJTWire` | :class:`_pjt_splice.PJTSplice` | :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: *member* first, then the rest in the order the walk reaches them.
        :rtype: list
        """
        db = self.db

        terminals = db.pjt_terminals_table
        splices = db.pjt_splices_table
        loops = db.pjt_wire_service_loops_table
        wires = db.pjt_wires_table

        node_ports = {}
        wire_ends = {}
        tables = {}

        for row in terminals.select('id', 'attach_point3d_id'):
            node_ports[row[0]] = [row[1]]
            tables[row[0]] = terminals

        for row in splices.select('id', 'start_point3d_id', 'stop_point3d_id', 'branch_point3d_id'):
            node_ports[row[0]] = list(row[1:])
            tables[row[0]] = splices

        for row in loops.select('id', 'start_point3d_id', 'stop_point3d_id'):
            node_ports[row[0]] = list(row[1:])
            tables[row[0]] = loops

        for row in wires.select('id', 'start_point3d_id', 'stop_point3d_id'):
            wire_ends[row[0]] = (row[1], row[2])
            tables[row[0]] = wires

        if member.db_id not in tables:
            return [member]

        children = _walk_circuit(member.db_id, node_ports, wire_ends)

        return [member if node_id == member.db_id else tables[node_id][node_id] for node_id in children]

    @_check_types.do
    def propagate(self, member: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop"], circuit_id: bytes | None) -> None:
        """Give every object connected to *member* the circuit *member* now has.

        A circuit is one connected chain, so when it is added to a wire, splice, wire service loop or terminal, or changes for one,
        the whole chain follows: everything :meth:`connected_members` reaches that is not in the circuit yet joins it, whatever it was
        in before. That is what the four ``circuit_id`` setters call, and ``PJTCircuit.add_member`` and ``merge_from`` call it
        themselves once they have placed their own members. One write: the moves share a single gesture.

        Taking a circuit away (``circuit_id`` ``None``, which is what ``PJTCircuit.detach_members`` does) does not spread; it is
        not propagated. Nothing happens while :meth:`propagation_paused` is holding it off.

        :param member: The row whose circuit was just set.
        :type member: :class:`_pjt_wire.PJTWire` | :class:`_pjt_splice.PJTSplice` | :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :param circuit_id: The circuit it now has. ``None`` does nothing.
        :type circuit_id: bytes | None
        """
        if circuit_id is None or self._propagation_paused:
            return

        pending = [row for row in self.connected_members(member)
                   if row.db_id != member.db_id and row.circuit_id != circuit_id]

        if not pending:
            return

        with self.propagation_paused(), self.db.gesture():
            self[circuit_id].adopt(pending)


@_check_types.do
def _walk_circuit(
        root_id: bytes,
        node_ports: dict[bytes, list[bytes | None]],
        wire_ends: dict[bytes, tuple[bytes | None, bytes | None]]) -> dict[bytes, list[bytes]]:
    """Walk a circuit outward from its start terminal and return the tree it makes.

    A circuit is wires joining junctions (terminals, splices, wire service
    loops) at shared connection points. *node_ports* gives each junction's
    connection points; every point of one junction is electrically common, so
    the walk may leave a splice through any of its points, whichever it came
    in by. A wire joins the junctions that own its two end points; an end no
    junction owns is a dangling end.

    The walk is breadth-first and visits every wire and every junction once.
    A loop in the wiring (two wires between the same two junctions, a ring) is
    cut where it closes: the closing wire stays in the tree as a leaf, and the
    junction it points back at is not visited again. Where the closing wire
    joins the same two junctions as a wire already in the tree, the two are
    side by side and :func:`_parallel_wires` finds them, so they can share the
    current; a ring through three or more junctions stays cut.

    :param root_id: The id of the start terminal.
    :type root_id: bytes
    :param node_ports: Every junction's id mapped to its connection point ids
        (``None`` for a point it does not have yet).
    :type node_ports: dict[bytes, list[bytes | None]]
    :param wire_ends: Every wire's id mapped to its start and stop point ids.
    :type wire_ends: dict[bytes, tuple[bytes | None, bytes | None]]
    :returns: Every visited id, root first and in visit order, mapped to the
        ids visited directly from it.
    :rtype: dict[bytes, list[bytes]]
    """
    port_owner = {}
    for node_id, ports in node_ports.items():
        for port in ports:
            if port is not None:
                port_owner[port] = node_id

    wires_at = {}
    for wire_id in sorted(wire_ends):
        for end in set(wire_ends[wire_id]):
            if end is not None:
                wires_at.setdefault(end, []).append(wire_id)

    children = {root_id: []}
    queue = deque([root_id])

    while queue:
        current = queue.popleft()
        next_ids = []

        if current in wire_ends:
            for end in wire_ends[current]:
                owner = port_owner.get(end)

                if owner is not None and owner not in children and owner not in next_ids:
                    next_ids.append(owner)
        else:
            for port in node_ports[current]:
                for wire_id in wires_at.get(port, []):
                    if wire_id not in children and wire_id not in next_ids:
                        next_ids.append(wire_id)

        for next_id in next_ids:
            children[current].append(next_id)
            children[next_id] = []
            queue.append(next_id)

    return children


@_check_types.do
def _parallel_wires(
        children: dict[bytes, list[bytes]],
        node_ports: dict[bytes, list[bytes | None]],
        wire_ends: dict[bytes, tuple[bytes | None, bytes | None]]) -> dict[bytes, list[bytes]]:
    """Find the wires that run side by side with a wire of the tree.

    Two or more wires between the same two junctions (a load fed by two or
    three wires that meet again at another terminal or splice) carry the
    load between them. The walk puts one of them in the tree as the way from
    one junction to the other and leaves the rest as leaves (see
    :func:`_walk_circuit`); this names which leaf belongs with which wire.
    A wire whose two ends are on one junction, a dangling wire, and a wire
    closing a ring through three or more junctions are none of them side by
    side with anything, and are left out.

    :param children: The tree :func:`_walk_circuit` made.
    :type children: dict[bytes, list[bytes]]
    :param node_ports: Every junction's id mapped to its connection point ids.
    :type node_ports: dict[bytes, list[bytes | None]]
    :param wire_ends: Every wire's id mapped to its start and stop point ids.
    :type wire_ends: dict[bytes, tuple[bytes | None, bytes | None]]
    :returns: A wire of the tree mapped to the other wires between the same
        two junctions, in id order. Only wires that have such company appear.
    :rtype: dict[bytes, list[bytes]]
    """
    port_owner = {}
    for node_id, ports in node_ports.items():
        for port in ports:
            if port is not None:
                port_owner[port] = node_id

    parent = {}
    for node_id, next_ids in children.items():
        for next_id in next_ids:
            parent[next_id] = node_id

    # the wire of the tree that joins each pair of junctions
    joins = {}
    for wire_id in children:
        if wire_id in wire_ends and wire_id in parent and len(children[wire_id]) == 1:
            joins.setdefault(frozenset((parent[wire_id], children[wire_id][0])), wire_id)

    groups = {}
    for wire_id in sorted(children):
        if wire_id not in wire_ends or children[wire_id]:
            continue

        owners = {port_owner.get(end) for end in wire_ends[wire_id]}
        owners.discard(None)

        if len(owners) != 2 or not owners.issubset(children):
            continue

        primary = joins.get(frozenset(owners))

        if primary is not None and primary != wire_id:
            groups.setdefault(primary, []).append(wire_id)

    return groups


@_check_types.do
def _nest(children: dict[bytes, list[bytes]], rows: dict[bytes, Any], node_id: bytes) -> list[Any]:
    """Return the part of the walk under *node_id* as the nested list
    :attr:`PJTCircuit.circuit_map` documents: *node_id*'s row, then each row
    it leads to in turn, and at a fork a single list holding one list per
    branch.

    :param children: The tree :func:`_walk_circuit` made.
    :type children: dict[bytes, list[bytes]]
    :param rows: Every member row, by id.
    :type rows: dict[bytes, Any]
    :param node_id: Where to start.
    :type node_id: bytes
    :returns: The nested list.
    :rtype: list[Any]
    """
    nested = [rows[node_id]]
    next_ids = children[node_id]

    while len(next_ids) == 1:
        node_id = next_ids[0]
        nested.append(rows[node_id])
        next_ids = children[node_id]

    if next_ids:
        nested.append([_nest(children, rows, next_id) for next_id in next_ids])

    return nested


@capturable()
class PJTCircuit(PJTEntryBase, NameMixin, NotesMixin):
    """Represent a PJT circuit in :mod:`harness_designer.database.project_db.pjt_circuit`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTCircuitsTable = None

    @_check_types.do
    def get_object(self) -> "_circuit_obj.Circuit":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_circuit_obj.Circuit`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_circuit_obj.Circuit") -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_circuit_obj.Circuit`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @dump_property(severity=1)
    @_check_types.do
    def volts(self) -> float:
        """Return the volts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        terminal = self.start_terminal
        if terminal is None:
            return 0.0

        return terminal.volts

    @property
    @dump_property(severity=1)
    @_check_types.do
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        resistance = _d(0)

        for terminal in self.terminals:
            resistance += _d(terminal.resistance)

        for splice in self.splices:
            resistance += _d(splice.resistance)

        for wire in self.wires:
            resistance += _d(wire.resistance)

        for loop in self.wire_service_loops:
            resistance += _d(loop.resistance)

        return float(resistance)

    # Member id lists, read from the table caches on first use and dropped by
    # PJTCircuitsTable.members_changed() whenever a wire, service loop, splice
    # or terminal joins, leaves or is deleted from this circuit (or a
    # terminal's is_start flips). Ids only -- the rows themselves are
    # singletons, so the properties below rebuild the lists from them.
    _stored_wire_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue
    _stored_wire_service_loop_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue
    _stored_splice_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue
    _stored_terminal_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue
    _stored_start_terminal_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue
    _stored_load_terminal_ids: list[bytes] | DefaultStoredValueType = DefaultStoredValue

    @_check_types.do
    def invalidate_members(self) -> None:
        """Forget every cached member id list, then tell anything bound to the
        ``'members'`` tag (the object browser keeps this circuit's member
        listing current that way).

        Reach this through :meth:`PJTCircuitsTable.members_changed` rather
        than calling it directly, so a circuit with no live row is skipped.
        """
        self._stored_wire_ids = DefaultStoredValue
        self._stored_wire_service_loop_ids = DefaultStoredValue
        self._stored_splice_ids = DefaultStoredValue
        self._stored_terminal_ids = DefaultStoredValue
        self._stored_start_terminal_ids = DefaultStoredValue
        self._stored_load_terminal_ids = DefaultStoredValue

        self._populate('members')

    @_check_types.do
    def _load_terminal_ids(self) -> tuple[list[bytes], list[bytes], list[bytes]]:
        """Fill the terminal, start-terminal and load-terminal id lists from
        one pass over this circuit's terminals.

        :returns: The three lists, as ``(terminals, start terminals, load
            terminals)``. Callers use these instead of re-reading the
            attributes: the circuit editor dock reads a circuit from a worker
            thread, and the UI thread can invalidate the attributes between a
            fill and the next read.
        :rtype: tuple[list[bytes], list[bytes], list[bytes]]
        """
        rows = self._table.db.pjt_terminals_table.select(
            'id', 'is_start', circuit_id=self._db_id)

        terminal_ids = [row[0] for row in rows]
        start_ids = [row[0] for row in rows if row[1]]
        load_ids = [row[0] for row in rows if not row[1]]

        self._stored_terminal_ids = terminal_ids
        self._stored_start_terminal_ids = start_ids
        self._stored_load_terminal_ids = load_ids

        return terminal_ids, start_ids, load_ids

    @_check_types.do
    def detach_members(self) -> None:
        """Clear ``circuit_id`` on every wire, service loop, splice and
        terminal in this circuit.

        Runs inside one gesture so the whole detach is a single write
        instead of one commit per member.
        """
        with self._table.db.gesture():
            for members in (self.wires, self.wire_service_loops,
                            self.splices, self.terminals):
                for member in members:
                    member.circuit_id = None

    @_check_types.do
    def delete(self) -> None:
        """Delete this circuit row after detaching its members.

        The member tables hold a foreign key to this row, so a member left
        pointing at it would reference a deleted circuit.
        """
        self.detach_members()

        super().delete()

    @_check_types.do
    def add_member(
            self,
            member: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> None:
        """Put *member* into this circuit.

        A terminal is inserted ``is_start=1`` (``PJTTerminalsTable.insert``)
        and cannot carry a load while it is a start terminal, so one joining
        here is demoted first. It is promoted again only when this circuit
        has no start terminal yet and the terminal carries no load; a
        circuit has exactly one start terminal.

        Everything connected to *member* joins this circuit too, whatever it was in
        before (see :meth:`PJTCircuitsTable.propagate`).

        :param member: The row to add. A member already in this circuit is
            left alone.
        :type member: :class:`_pjt_wire.PJTWire` | :class:`_pjt_splice.PJTSplice` |
            :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """
        if member.circuit_id == self._db_id:
            return

        # the member's own placement, its start-terminal rule included, comes first; the rest of its chain follows
        with self._table.propagation_paused():
            if isinstance(member, _pjt_terminal.PJTTerminal):
                has_start = self.start_terminal is not None

                member.is_start = False
                member.circuit_id = self._db_id

                if not has_start and not member.load:
                    member.is_start = True
            else:
                member.circuit_id = self._db_id

        self._table.propagate(member, self._db_id)

    @_check_types.do
    def merge_from(self, other: "PJTCircuit") -> None:
        """Move every member of *other* into this circuit.

        *other* is left in place and empty; delete it through
        :meth:`Project.merge_circuits` (or ``Circuit.delete``) so its object
        and object-browser node go too. Runs inside one gesture so the move is
        a single write. When this circuit already has a start terminal, every
        start terminal of *other* is demoted; otherwise the first one is kept.

        :param other: The circuit to absorb.
        :type other: :class:`PJTCircuit`
        """
        has_start = self.start_terminal is not None
        moved = []

        with self._table.propagation_paused(), self._table.db.gesture():
            for terminal in other.terminals:
                if not terminal.is_start:
                    continue

                if has_start:
                    terminal.is_start = False
                else:
                    has_start = True

            for members in (other.wires, other.wire_service_loops,
                            other.splices, other.terminals):
                for member in members:
                    member.circuit_id = self._db_id
                    moved.append(member)

        # one walk for the whole move, not one per member: anything connected to what moved joins too
        if moved:
            self._table.propagate(moved[0], self._db_id)

    @_check_types.do
    def adopt(self, rows: list[_Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop"]]) -> None:
        """Move *rows*, the chain of a member that just joined, into this circuit.

        The start-terminal rule is :meth:`merge_from`'s: a circuit has exactly one. A start terminal that joins is demoted, and when
        the circuit has no start terminal once everything has joined, the first of those start terminals that carries no load is
        promoted. A circuit that already has one keeps it.

        :param rows: The rows to add, none of them in this circuit yet.
        :type rows: list
        """
        former_starts = []

        for row in rows:
            if isinstance(row, _pjt_terminal.PJTTerminal) and row.is_start:
                row.is_start = False
                former_starts.append(row)

            row.circuit_id = self._db_id

        if self.start_terminal is None:
            for terminal in former_starts:
                if not terminal.load:
                    terminal.is_start = True
                    break

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_terminal(self) -> _Union["_pjt_terminal.PJTTerminal", None]:
        """Return the start terminal.

        :returns: The first terminal in this circuit flagged ``is_start``,
            or ``None`` when the circuit has none.
        :rtype: :class:`_pjt_terminal.PJTTerminal` | None
        """
        start_ids = self._stored_start_terminal_ids
        if start_ids is DefaultStoredValue:
            start_ids = self._load_terminal_ids()[1]

        if start_ids:
            return self._table.db.pjt_terminals_table[start_ids[0]]

        return None

    @property
    @_check_types.do
    def voltage_drop(self) -> float:
        """Return the voltage drop.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        drop = 0.0

        for terminal in self.load_terminals:
            drop = max(terminal.voltage_drop, drop)

        return drop

    @property
    @dump_property(severity=2)
    @_check_types.do
    def load_terminals(self) -> list["_pjt_terminal.PJTTerminal"]:
        """Return the load terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_terminal.PJTTerminal']
        """
        load_ids = self._stored_load_terminal_ids
        if load_ids is DefaultStoredValue:
            load_ids = self._load_terminal_ids()[2]

        terminals_table = self._table.db.pjt_terminals_table
        return [terminals_table[db_id] for db_id in load_ids]

    @_check_types.do
    def _trace(self) -> tuple[dict[bytes, list[bytes]], dict[bytes, Any]]:
        """The tree and the member rows of :meth:`_trace_full`, for everything that does not
        need to know about wires side by side.

        :rtype: tuple[dict[bytes, list[bytes]], dict[bytes, Any]]
        """
        children, rows, _ = self._trace_full()

        return children, rows

    @_check_types.do
    def _trace_full(self) -> tuple[dict[bytes, list[bytes]], dict[bytes, Any], dict[bytes, list[bytes]]]:
        """Walk this circuit outward from its start terminal.

        Connectivity is read from the 3D point ids every view writes when a
        wire is attached (see ``Terminal.add_wire``, ``Splice.add_wire``), so
        it does not matter which editor drew the wire.

        :returns: ``(children, rows, parallel)``: the tree :func:`_walk_circuit`
            makes, every member row by id, and the wires side by side that
            :func:`_parallel_wires` finds. All are empty when the circuit has
            no start terminal. A member the walk never reaches (it is not
            wired to the start terminal through members of this circuit) is in
            ``rows`` but not in ``children``.
        :rtype: tuple[dict[bytes, list[bytes]], dict[bytes, Any], dict[bytes, list[bytes]]]
        """
        start = self.start_terminal
        if start is None:
            return {}, {}, {}

        db = self._table.db
        rows = {}
        node_ports = {}
        wire_ends = {}

        for terminal in self.terminals:
            rows[terminal.db_id] = terminal
            node_ports[terminal.db_id] = list(db.pjt_terminals_table.select(
                'attach_point3d_id', id=terminal.db_id)[0])

        for splice in self.splices:
            rows[splice.db_id] = splice
            node_ports[splice.db_id] = list(db.pjt_splices_table.select(
                'start_point3d_id', 'stop_point3d_id', 'branch_point3d_id',
                id=splice.db_id)[0])

        for loop in self.wire_service_loops:
            rows[loop.db_id] = loop
            node_ports[loop.db_id] = list(db.pjt_wire_service_loops_table.select(
                'start_point3d_id', 'stop_point3d_id', id=loop.db_id)[0])

        for wire in self.wires:
            rows[wire.db_id] = wire
            wire_ends[wire.db_id] = db.pjt_wires_table.select(
                'start_point3d_id', 'stop_point3d_id', id=wire.db_id)[0]

        children = _walk_circuit(start.db_id, node_ports, wire_ends)

        return children, rows, _parallel_wires(children, node_ports, wire_ends)

    @property
    @_check_types.do
    def circuit_map(self) -> list[Any]:
        """Return the circuit as a nested list, walked out from the start
        terminal.

        ``[start_terminal, wire, splice, wire, terminal]`` for a straight run.
        At a fork the list ends with one list holding a branch list per
        branch: ``[start_terminal, wire, splice, [[wire, terminal], [wire,
        loop, wire, terminal]]]``. A wire with a dangling far end is just the
        last row of its branch. Only members wired to the start terminal
        appear, each once (see :func:`_walk_circuit` for loops).

        :returns: The nested list, or ``[]`` when the circuit has no start
            terminal.
        :rtype: list[Any]
        """
        children, rows = self._trace()

        if not children:
            return []

        return _nest(children, rows, next(iter(children)))

    @_check_types.do
    def get_circuit_end_terminals(
        self, target: _Union["_pjt_terminal.PJTTerminal", "_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> list["_pjt_terminal.PJTTerminal"]:
        """Return every terminal at or beyond *target*, walking away from the
        start terminal.

        :param target: A member of this circuit. Pass a wire to get the loads
            it feeds; *target* itself is included when it is a terminal.
        :type target: :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire.PJTWire` |
            :class:`_pjt_splice.PJTSplice` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: The terminals, nearest the start terminal first.
        :rtype: list[:class:`_pjt_terminal.PJTTerminal`]
        :raises ValueError: *target* is not wired to this circuit's start
            terminal.
        """
        children, rows = self._trace()

        if target.db_id not in children:
            raise ValueError(
                f'{target.db_id!r} is not wired to the start terminal of circuit {self._db_id!r}')

        terminals = []
        stack = [target.db_id]

        while stack:
            node_id = stack.pop()

            if isinstance(rows[node_id], _pjt_terminal.PJTTerminal):
                terminals.append(rows[node_id])

            stack.extend(reversed(children[node_id]))

        return terminals

    @_check_types.do
    def get_circuit(
        self, target: _Union["_pjt_terminal.PJTTerminal", "_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> list:
        """Return the path from the start terminal to *target*, inclusive.

        :param target: A member of this circuit.
        :type target: :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire.PJTWire` |
            :class:`_pjt_splice.PJTSplice` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: Every row on the way, start terminal first, *target* last.
        :rtype: list
        :raises ValueError: *target* is not wired to this circuit's start
            terminal.
        """
        children, rows = self._trace()

        if target.db_id not in children:
            raise ValueError(
                f'{target.db_id!r} is not wired to the start terminal of circuit {self._db_id!r}')

        parents = {}
        for node_id, next_ids in children.items():
            for next_id in next_ids:
                parents[next_id] = node_id

        path = [target.db_id]
        while path[-1] in parents:
            path.append(parents[path[-1]])

        path.reverse()

        return [rows[node_id] for node_id in path]

    @_check_types.do
    def _prepare_solve(self) -> tuple[_Union["_circuit_solver.CircuitInput", None], dict[bytes, Any]]:
        """Collect what the solver needs to solve this circuit: the tree, what each member says
        about itself (``part_data()``), the loads and the voltage.

        :returns: ``(input, rows)``; ``input`` is ``None`` when the circuit has no voltage
            terminal, and ``rows`` is empty then.
        :rtype: tuple[:class:`_circuit_solver.CircuitInput` | None, dict[bytes, Any]]
        """
        children, rows, parallel = self._trace_full()

        if not children:
            return None, rows

        parts = {}
        loads = {}

        for node_id in children:
            row = rows[node_id]
            parts[node_id] = row.part_data()

            if isinstance(row, _pjt_terminal.PJTTerminal):
                rated = float(row.load or 0.0)

                if rated > 0.0:
                    loads[node_id] = _circuit_solver.LoadData(rated, row.load_type)

        volts = float(rows[next(iter(children))].volts or 0.0)

        return _circuit_solver.CircuitInput(children, parts, loads, volts, self.return_type, parallel), rows

    @_check_types.do
    def _bundle_component(self) -> tuple[dict[bytes, "PJTCircuit"], list["_circuit_solver.BundleData"]]:
        """Find every bundle this circuit's wires run through, and every circuit that shares one,
        and the bundles those circuits run through in turn: the circuits that heat each other.

        :returns: ``(circuits, bundles)``: the circuits by id, this one included, and the bundles.
            ``bundles`` is empty when none of this circuit's wires is in a bundle.
        :rtype: tuple[dict[bytes, PJTCircuit], list[:class:`_circuit_solver.BundleData`]]
        """
        wires_table = self._table.db.pjt_wires_table
        circuits = {self._db_id: self}
        bundles = {}
        queue = deque([self])

        while queue:
            circuit = queue.popleft()

            for wire in circuit.wires:
                for bundle in wire.bundles:
                    if bundle.db_id in bundles:
                        continue

                    data = bundle.thermal_data()
                    bundles[bundle.db_id] = data

                    for wire_id in data.wire_ids:
                        circuit_id = wires_table.select('circuit_id', id=wire_id)[0][0]

                        if circuit_id is not None and circuit_id not in circuits:
                            circuits[circuit_id] = self._table[circuit_id]
                            queue.append(circuits[circuit_id])

        return circuits, list(bundles.values())

    @_check_types.do
    def _solve_traced(self) -> tuple[_Union["_circuit_solver.CircuitSolution", None], dict[bytes, Any]]:
        """Solve the circuit and return the member rows with the solution.

        Wires that share a bundle with wires of other circuits are warmed by them, so those
        circuits are solved together (see :func:`_circuit_solver.solve_bundled`); a circuit
        none of whose wires is in a bundle is solved alone, as before.

        :returns: ``(solution, rows)``; ``solution`` is ``None`` when the
            circuit has no voltage terminal, and ``rows`` is empty then.
        :rtype: tuple[:class:`_circuit_solver.CircuitSolution` | None, dict[bytes, Any]]
        """
        prepared, rows = self._prepare_solve()

        if prepared is None:
            return None, rows

        circuits, bundles = self._bundle_component()

        if not bundles:
            return _circuit_solver.solve_circuit(
                prepared.children, prepared.parts, prepared.loads, prepared.volts, prepared.return_type,
                prepared.parallel), rows

        inputs = {self._db_id: prepared}

        for circuit_id, circuit in circuits.items():
            if circuit_id != self._db_id:
                other = circuit._prepare_solve()[0]

                if other is not None:
                    inputs[circuit_id] = other

        return _circuit_solver.solve_bundled(inputs, bundles)[self._db_id], rows

    @_check_types.do
    def solve(self) -> _Union["_circuit_solver.CircuitSolution", None]:
        """Work out the current, voltage and temperature of everything in this
        circuit.

        Starts at the voltage terminal and covers every wire, splice, wire
        service loop and terminal wired to it (the same walk as
        :attr:`circuit_map`). Each member describes itself through its
        ``part_data()`` (resistance, thermal resistance, operating
        temperature, rated maximum); a terminal's load is the current its
        device is rated for at the voltage terminal's voltage, reacting to
        the voltage that really reaches it as its ``load_type`` says. See
        :mod:`harness_designer.database.project_db.circuit_solver` for the
        model.

        :returns: The solution, or ``None`` when the circuit has no voltage
            terminal.
        :rtype: :class:`_circuit_solver.CircuitSolution` | None
        """
        return self._solve_traced()[0]

    @_check_types.do
    def load_at(
        self, target: _Union["_pjt_terminal.PJTTerminal", "_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> float:
        """Return the load at *target*, in amps.

        For a wire, splice or wire service loop that is the current flowing
        through it: what the load terminals from there outward draw, at the
        voltage that actually reaches them. Everything between the voltage
        terminal and *target* is left out of the number, though the drop it
        causes is why that voltage is lower than the supply. For a terminal it
        is what that terminal itself draws.

        :param target: A member of this circuit.
        :type target: :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire.PJTWire` |
            :class:`_pjt_splice.PJTSplice` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: The current in amps. ``0.0`` when the circuit has no voltage
            terminal, or *target* is not wired to it.
        :rtype: float
        """
        solution = self.solve()

        if solution is None:
            return 0.0

        if isinstance(target, _pjt_terminal.PJTTerminal):
            return solution.draw.get(target.db_id, 0.0)

        return solution.amps.get(target.db_id, 0.0)

    @_check_types.do
    def voltage_at(
        self, target: _Union["_pjt_terminal.PJTTerminal", "_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> float:
        """Return the voltage where *target* is entered: the voltage
        terminal's voltage less the drop through everything between them.

        :param target: A member of this circuit.
        :type target: :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire.PJTWire` |
            :class:`_pjt_splice.PJTSplice` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: The voltage. ``0.0`` when the circuit has no voltage
            terminal, or *target* is not wired to it.
        :rtype: float
        """
        solution = self.solve()

        if solution is None:
            return 0.0

        return solution.volts.get(target.db_id, 0.0)

    @_check_types.do
    def temperature_at(
        self, target: _Union["_pjt_terminal.PJTTerminal", "_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_wire_service_loop.PJTWireServiceLoop"]) -> float:
        """Return how hot *target* runs, in degrees Celsius: its ambient
        (operating) temperature plus its own rise at the current through it.

        :param target: A member of this circuit.
        :type target: :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire.PJTWire` |
            :class:`_pjt_splice.PJTSplice` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        :returns: The temperature. Just the ambient when the circuit has no
            voltage terminal, or *target* is not wired to it.
        :rtype: float
        """
        solution = self.solve()

        if solution is not None and target.db_id in solution.temperature:
            return solution.temperature[target.db_id]

        return target.ambient_c

    @_check_types.do
    def over_temperature_members(self) -> list:
        """Return every member that runs hotter than it is rated for.

        A member with no rated maximum is never listed. A member the circuit
        does not reach (or every member, when there is no voltage terminal) is
        judged on the air around it alone.

        :returns: The rows, wires then service loops then splices then
            terminals.
        :rtype: list
        """
        solution = self.solve()

        flagged = []

        for members in (self.wires, self.wire_service_loops, self.splices, self.terminals):
            for member in members:
                rated = member.max_temp_c

                if rated is None:
                    continue

                if solution is not None and member.db_id in solution.temperature:
                    temperature = solution.temperature[member.db_id]
                else:
                    temperature = member.ambient_c

                if temperature > rated:
                    flagged.append(member)

        return flagged

    @property
    @_check_types.do
    def table(self) -> PJTCircuitsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCircuitsTable`
        """
        return self._table

    @property
    @_check_types.do
    def circuit_num(self) -> int:
        """Return the circuit num.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('circuit_num', id=self._db_id)[0][0]

    @circuit_num.setter
    @_check_types.do
    def circuit_num(self, value: int) -> None:
        """Set the circuit num.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, circuit_num=value)
        self._populate('circuit_num')

    @property
    @_check_types.do
    def description(self) -> str:
        """Return the description.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    @_check_types.do
    def description(self, value: str) -> None:
        """Set the description.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, description=value)
        self._populate('description')

    @property
    @_check_types.do
    def return_type(self) -> _circuit_solver.ReturnType:
        """Return how this circuit's current returns to its source: a chassis
        return that is not modelled, or one mirroring the supply wires (see
        :class:`_circuit_solver.ReturnType`).

        :returns: The return type.
        :rtype: :class:`_circuit_solver.ReturnType`
        :raises ValueError: The stored integer is not a return type.
        """
        return _circuit_solver.ReturnType(
            self._table.select('return_type', id=self._db_id)[0][0])

    @return_type.setter
    @_check_types.do
    def return_type(self, value: _circuit_solver.ReturnType) -> None:
        """Set how this circuit's current returns to its source.

        :param value: The return type.
        :type value: :class:`_circuit_solver.ReturnType`
        """
        self._table.update(self._db_id, return_type=int(value))
        self._populate('return_type')

    @property
    @_check_types.do
    def label(self) -> str:
        """Return how the circuit is shown to the user: ``'#3 Fuel pump'``, or
        just ``'#3'`` while it has no name.

        :returns: The label.
        :rtype: str
        """
        name = self.name

        if name:
            return f'#{self.circuit_num} {name}'

        return f'#{self.circuit_num}'

    @property
    @_check_types.do
    def total_circuit_load(self) -> float:
        """Return the current, in amps, the circuit draws from its voltage
        terminal.

        The whole circuit is covered (see :meth:`solve`): every wire, splice,
        wire service loop and terminal wired to the voltage terminal, with
        their resistances, and every terminal that has a load.

        :returns: The current in amps; ``0.0`` when the circuit has no voltage
            terminal or no voltage is set on it.
        :rtype: float
        """
        solution = self.solve()

        if solution is None:
            return 0.0

        return solution.total_amps

    @property
    @_check_types.do
    def total_circuit_weight_g(self) -> float:
        """Return the total circuit weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.terminal_weight_g + self.wire_weight_g + self.splice_weight_g

    @property
    @_check_types.do
    def total_circuit_weight_lb(self) -> float:
        """Return the total circuit weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.terminal_weight_lb + self.wire_weight_lb + self.splice_weight_lb

    @property
    @_check_types.do
    def wire_length_mm(self) -> float:
        """Return the wire length mm.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        wire_length = sum([wire.length_mm for wire in self.wires])
        wire_length += sum([loop.length_mm for loop in self.wire_service_loops])
        return wire_length

    @property
    @_check_types.do
    def wire_length_m(self) -> float:
        """Return the wire length m.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.wire_length_mm / 1000.0

    @property
    @_check_types.do
    def wire_length_ft(self) -> float:
        """Return the wire length ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.wire_length_m * 3.28084

    @property
    @_check_types.do
    def wire_weight_g(self) -> float:
        """Return the wire weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        wire_weight = sum([wire.weight_g for wire in self.wires])
        wire_weight += sum([loop.weight_g for loop in self.wire_service_loops])
        return wire_weight

    @property
    @_check_types.do
    def wire_weight_lb(self) -> float:
        """Return the wire weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        # from the gram total, which counts the wire service loops too (the pound total used to sum the wires alone)
        return self.wire_weight_g * 0.00220462

    @property
    @_check_types.do
    def terminal_weight_g(self) -> float:
        """Return the terminal weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return sum([terminal.part.weight for terminal in self.terminals])

    @property
    @_check_types.do
    def terminal_weight_lb(self) -> float:
        """Return the terminal weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight_g = self.terminal_weight_g
        return weight_g * 0.00220462

    @property
    @_check_types.do
    def splice_weight_g(self) -> float:
        """Return the splice weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return sum([splice.part.weight for splice in self.splices])

    @property
    @_check_types.do
    def splice_weight_lb(self) -> float:
        """Return the splice weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        weight_g = self.splice_weight_g
        return weight_g * 0.00220462

    @property
    @_check_types.do
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire.PJTWire']
        """
        wire_ids = self._stored_wire_ids
        if wire_ids is DefaultStoredValue:
            rows = self._table.db.pjt_wires_table.select('id', circuit_id=self._db_id)
            wire_ids = [row[0] for row in rows]
            self._stored_wire_ids = wire_ids

        wires_table = self._table.db.pjt_wires_table
        return [wires_table[db_id] for db_id in wire_ids]

    @property
    @_check_types.do
    def wire_service_loops(self) -> list["_pjt_wire_service_loop.PJTWireServiceLoop"]:
        """Return the wire service loops.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire_service_loop.PJTWireServiceLoop']
        """
        loop_ids = self._stored_wire_service_loop_ids
        if loop_ids is DefaultStoredValue:
            rows = self._table.db.pjt_wire_service_loops_table.select(
                'id', circuit_id=self._db_id)
            loop_ids = [row[0] for row in rows]
            self._stored_wire_service_loop_ids = loop_ids

        loops_table = self._table.db.pjt_wire_service_loops_table
        return [loops_table[db_id] for db_id in loop_ids]

    @property
    @_check_types.do
    def splices(self) -> list["_pjt_splice.PJTSplice"]:
        """Return the splices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_splice.PJTSplice']
        """
        splice_ids = self._stored_splice_ids
        if splice_ids is DefaultStoredValue:
            rows = self._table.db.pjt_splices_table.select('id', circuit_id=self._db_id)
            splice_ids = [row[0] for row in rows]
            self._stored_splice_ids = splice_ids

        splices_table = self._table.db.pjt_splices_table
        return [splices_table[db_id] for db_id in splice_ids]

    @property
    @_check_types.do
    def terminals(self) -> list["_pjt_terminal.PJTTerminal"]:
        """Return the terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_terminal.PJTTerminal']
        """
        terminal_ids = self._stored_terminal_ids
        if terminal_ids is DefaultStoredValue:
            terminal_ids = self._load_terminal_ids()[0]

        terminals_table = self._table.db.pjt_terminals_table
        return [terminals_table[db_id] for db_id in terminal_ids]


class PJTCircuitControl(QtWidgets.QTabWidget):
    """Represent a PJT circuit control in :mod:`harness_designer.database.project_db.pjt_circuit`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def _get_project(self) -> "_project_obj.Project":
        """Return the loaded project, reached through the host row's object.

        :returns: The project the host row belongs to.
        :rtype: :class:`_project_obj.Project`
        """
        return self.host.get_object().mainframe.project

    @_check_types.do
    def _assign(self, circuit: PJTCircuit) -> None:
        """Put the host row into *circuit* and refresh the control. Everything connected to the host
        row joins *circuit* too (see :meth:`PJTCircuit.add_member`).

        :param circuit: The circuit the host row now belongs to.
        :type circuit: :class:`PJTCircuit`
        """
        circuit.add_member(self.host)

        self.set_obj(self.host)

    @_check_types.do
    def _confirm_move(self, circuit: "PJTCircuit | None", label: str) -> bool:
        """Ask before *circuit* takes over connected objects that are in another circuit.

        Choosing a circuit for the host row moves everything connected to it (see :meth:`PJTCircuitsTable.propagate`), so any of
        those objects that is in a different circuit would change circuit. Nothing is asked when none is, or when the host row
        is already in *circuit* (nothing moves then). Asked before a circuit is created for a name or number that does not
        exist yet, so answering No leaves nothing behind.

        :param circuit: The circuit being chosen, or ``None`` when it does not exist yet.
        :type circuit: :class:`PJTCircuit` | None
        :param label: What to call that circuit in the question.
        :type label: str
        :returns: ``True`` to go ahead, ``False`` when the user declined.
        :rtype: bool
        """
        host = self.host
        table = host.table.db.pjt_circuits_table
        target_id = None if circuit is None else circuit.db_id

        if target_id is not None and host.circuit_id == target_id:
            return True

        moving = 0
        other_ids = []

        for row in table.connected_members(host):
            if row.db_id == host.db_id:
                continue

            circuit_id = row.circuit_id

            if circuit_id is None or circuit_id == target_id:
                continue

            moving += 1

            if circuit_id not in other_ids:
                other_ids.append(circuit_id)

        if not moving:
            return True

        labels = ', '.join(table[circuit_id].label for circuit_id in other_ids)
        noun = 'object is' if moving == 1 else 'objects are'
        kind = 'circuit' if len(other_ids) == 1 else 'circuits'

        button = QtWidgets.QMessageBox.question(
            self, 'Move Connected Objects',
            f'{moving} connected {noun} in {kind} {labels}.\n\n'
            f'Moving this part to circuit {label} moves them too.\n\nContinue?')

        return button != QtWidgets.QMessageBox.StandardButton.No

    @_check_types.do
    def _on_circuit_num(self, evt: "_prop_events.PropertyEvent") -> None:
        """Assign the host row to the circuit with the chosen number.

        A number no circuit has yet creates one, with no name and no
        description. Asks first when that would move connected objects out of
        another circuit (see :meth:`_confirm_move`); No changes nothing.

        :param evt: The property event.
        :type evt: :class:`_prop_events.PropertyEvent`
        """
        try:
            num = int(evt.GetValue())
        except ValueError:
            self.set_obj(self.host)
            return

        circuit = self.host.table.db.pjt_circuits_table.get_by_num(num)

        if not self._confirm_move(circuit, f'#{num}' if circuit is None else circuit.label):
            self.set_obj(self.host)
            return

        if circuit is None:
            circuit = self._get_project().create_circuit(num).db_obj

        self._assign(circuit)

    @_check_types.do
    def _on_description(self, evt: "_prop_events.PropertyEvent") -> None:
        """Store the description on the host row's circuit.

        :param evt: The property event.
        :type evt: :class:`_prop_events.PropertyEvent`
        """
        self.db_obj.description = evt.GetValue()

    @_check_types.do
    def _on_operating_temp(self, evt: "_prop_events.PropertyEvent") -> None:
        """Store the temperature the host row works in.

        :param evt: The property event.
        :type evt: :class:`_prop_events.PropertyEvent`
        """
        self.host.operating_temp = evt.GetValue()

        self.set_obj(self.host)

    @_check_types.do
    def _on_return_type(self, evt: "_prop_events.PropertyEvent") -> None:
        """Store how the host row's circuit gets its current back to the
        source. Anything typed that is not one of the two choices is dropped.

        :param evt: The property event.
        :type evt: :class:`_prop_events.PropertyEvent`
        """
        label = evt.GetValue()

        for return_type, name in _RETURN_TYPE_LABELS.items():
            if name == label:
                self.db_obj.return_type = return_type
                break

        self.set_obj(self.host)

    @_check_types.do
    def _on_name(self, evt: "_prop_events.PropertyEvent") -> None:
        """Assign the host row to the circuit with the chosen name.

        A name no circuit has yet creates one, numbered with the next free
        circuit number. This picks or creates a circuit; it does not rename
        the host row's current one. The control only sends the event when
        Enter is pressed or a name is picked from the list, so a circuit is
        never created for half-typed text. It also asks first when the choice
        would move connected objects out of another circuit (see
        :meth:`_confirm_move`); No changes nothing.

        :param evt: The property event.
        :type evt: :class:`_prop_events.PropertyEvent`
        """
        name = evt.GetValue()

        if not name:
            return

        circuit = self.host.table.db.pjt_circuits_table.get_by_name(name)

        if not self._confirm_move(circuit, f'"{name}"' if circuit is None else circuit.label):
            self.set_obj(self.host)
            return

        if circuit is None:
            circuit = self._get_project().create_circuit(name=name).db_obj

        self._assign(circuit)

    @_check_types.do
    def set_obj(
            self,
            host: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop", None]) -> None:
        """Show the circuit of *host*, and let the user move *host* to another.

        The description and notes belong to the circuit, so they are
        disabled while *host* has none.

        :param host: The wire, splice, terminal or service loop row the panel
            is showing, or ``None`` to clear the control.
        :type host: :class:`_pjt_wire.PJTWire` | :class:`_pjt_splice.PJTSplice` |
            :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop` | None
        """
        self.host = host

        db_obj = None
        circuit_nums = []
        names = []

        if host is not None:
            circuits_table = host.table.db.pjt_circuits_table

            circuit_id = host.circuit_id
            if circuit_id is not None:
                db_obj = circuits_table[circuit_id]

            rows = circuits_table.select('circuit_num', 'name')
            circuit_nums = [str(num) for num in sorted(row[0] for row in rows)]
            names = sorted({row[1] for row in rows if row[1]})

        self.db_obj = db_obj

        self.notes_ctrl.set_obj(db_obj)

        self.description_ctrl.setEnabled(db_obj is not None)
        self.return_type_ctrl.setEnabled(db_obj is not None)
        self.notes_ctrl.setEnabled(db_obj is not None)

        self.name_ctrl.SetItems(names)
        self.circuit_num_ctrl.SetItems(circuit_nums)

        if db_obj is None:
            self.name_ctrl.SetValue('')
            self.circuit_num_ctrl.SetValue('')

            self.description_ctrl.SetValue('')
            self.return_type_ctrl.SetValue('')
            self.voltage_drop_ctrl.SetValue('')
            self.voltage_ctrl.SetValue('')
            self.total_circuit_resistance_ctrl.SetValue('')
            self.total_circuit_load_ctrl.SetValue('')
            self.total_circuit_weight_g_ctrl.SetValue('')
            self.total_circuit_weight_lb_ctrl.SetValue('')
            self.wire_length_mm_ctrl.SetValue('')
            self.wire_length_m_ctrl.SetValue('')
            self.wire_length_ft_ctrl.SetValue('')
            self.wire_weight_g_ctrl.SetValue('')
            self.wire_weight_lb_ctrl.SetValue('')
            self.terminal_weight_g_ctrl.SetValue('')
            self.terminal_weight_lb_ctrl.SetValue('')
            self.splice_weight_g_ctrl.SetValue('')
            self.splice_weight_lb_ctrl.SetValue('')
            self.over_temp_count_ctrl.SetValue('')

        else:
            self.name_ctrl.SetValue(db_obj.name)
            self.circuit_num_ctrl.SetValue(str(db_obj.circuit_num))
            self.description_ctrl.SetValue(db_obj.description)
            self.return_type_ctrl.SetValue(_RETURN_TYPE_LABELS[db_obj.return_type])
            self.voltage_drop_ctrl.SetValue(str(db_obj.voltage_drop))
            self.voltage_ctrl.SetValue(str(db_obj.volts))
            self.total_circuit_resistance_ctrl.SetValue(str(db_obj.resistance))
            self.total_circuit_load_ctrl.SetValue(str(db_obj.total_circuit_load))
            self.total_circuit_weight_g_ctrl.SetValue(str(db_obj.total_circuit_weight_g))
            self.total_circuit_weight_lb_ctrl.SetValue(str(db_obj.total_circuit_weight_lb))
            self.wire_length_mm_ctrl.SetValue(str(db_obj.wire_length_mm))
            self.wire_length_m_ctrl.SetValue(str(db_obj.wire_length_m))
            self.wire_length_ft_ctrl.SetValue(str(db_obj.wire_length_ft))
            self.wire_weight_g_ctrl.SetValue(str(db_obj.wire_weight_g))
            self.wire_weight_lb_ctrl.SetValue(str(db_obj.wire_weight_lb))
            self.terminal_weight_g_ctrl.SetValue(str(db_obj.terminal_weight_g))
            self.terminal_weight_lb_ctrl.SetValue(str(db_obj.terminal_weight_lb))
            self.splice_weight_g_ctrl.SetValue(str(db_obj.splice_weight_g))
            self.splice_weight_lb_ctrl.SetValue(str(db_obj.splice_weight_lb))
            self.over_temp_count_ctrl.SetValue(str(len(db_obj.over_temperature_members())))

        self._show_part_temperature(host)

    @_check_types.do
    def _show_part_temperature(
            self,
            host: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop", None]) -> None:
        """Show the host row's own temperature: where it works, how hot it
        runs, what it is rated for and whether that is exceeded.

        :param host: The row the panel is showing, or ``None``.
        :type host: :class:`_pjt_wire.PJTWire` | :class:`_pjt_splice.PJTSplice` |
            :class:`_pjt_terminal.PJTTerminal` | :class:`_pjt_wire_service_loop.PJTWireServiceLoop` | None
        """
        if host is None:
            self.operating_temp_ctrl.setEnabled(False)
            self.operating_temp_ctrl.SetValue(_circuit_solver.DEFAULT_AMBIENT_C)
            self.part_temp_ctrl.SetValue('')
            self.rated_temp_ctrl.SetValue('')
            self.temp_status_ctrl.SetValue('')
            return

        self.operating_temp_ctrl.setEnabled(True)
        self.operating_temp_ctrl.SetValue(host.ambient_c)
        self.part_temp_ctrl.SetValue(f'{host.temperature_c:.1f}')

        rated = host.max_temp_c

        if rated is None:
            self.rated_temp_ctrl.SetValue('Unknown')
            self.temp_status_ctrl.SetValue('Unrated')
        elif host.over_temperature:
            self.rated_temp_ctrl.SetValue(f'{rated:g}')
            self.temp_status_ctrl.SetValue('OVER TEMPERATURE')
        else:
            self.rated_temp_ctrl.SetValue(f'{rated:g}')
            self.temp_status_ctrl.SetValue('OK')

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`PJTCircuitControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self._parent = parent
        self.db_obj: PJTCircuit | None = None
        self.host: _Union["_pjt_wire.PJTWire", "_pjt_splice.PJTSplice", "_pjt_terminal.PJTTerminal", "_pjt_wire_service_loop.PJTWireServiceLoop", None] = None

        QtWidgets.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')

        self.name_ctrl = _prop_ctrls.ComboBoxProperty(general_page, 'Name')
        self.circuit_num_ctrl = _prop_ctrls.ComboBoxProperty(general_page, 'Circuit Number')
        self.description_ctrl = _prop_ctrls.LongStringProperty(general_page, 'Description')
        self.return_type_ctrl = _prop_ctrls.ComboBoxProperty(general_page, 'Return Path')
        self.notes_ctrl = NotesControl(general_page)

        self.return_type_ctrl.SetItems(list(_RETURN_TYPE_LABELS.values()))
        self.return_type_ctrl.setToolTip(
            'Chassis: the return path is not modelled (a chassis or body '
            'return).\nMirrored: the return is as long and as heavy as the '
            'supply wires, so every voltage drop doubles.')

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.circuit_num_ctrl)
        general_page.addWidget(self.description_ctrl)
        general_page.addWidget(self.return_type_ctrl)
        general_page.addWidget(self.notes_ctrl)

        self.name_ctrl.propertyChanged.connect(self._on_name)
        self.circuit_num_ctrl.propertyChanged.connect(self._on_circuit_num)
        self.description_ctrl.propertyChanged.connect(self._on_description)
        self.return_type_ctrl.propertyChanged.connect(self._on_return_type)

        electrical_page = _prop_ctrls.Category(self, 'Electrical')

        self.voltage_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Voltage', units='V', read_only=True)
        self.voltage_drop_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Voltage Drop', units='V', read_only=True)
        self.total_circuit_load_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Total Circuit Load', units='A', read_only=True)
        self.total_circuit_resistance_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Total Circuit Resistance', units='Ω', read_only=True)

        electrical_page.addWidget(self.voltage_ctrl)
        electrical_page.addWidget(self.voltage_drop_ctrl)
        electrical_page.addWidget(self.total_circuit_load_ctrl)
        electrical_page.addWidget(self.total_circuit_resistance_ctrl)

        self.over_temp_count_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Parts Over Temperature', read_only=True)
        self.operating_temp_ctrl = _prop_ctrls.FloatProperty(electrical_page, 'Operating Temperature', min_value=-100.0, max_value=1000.0, increment=0.5, units='\u00b0C')
        self.part_temp_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Part Temperature', units='\u00b0C', read_only=True)
        self.rated_temp_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Rated Maximum', units='\u00b0C', read_only=True)
        self.temp_status_ctrl = _prop_ctrls.StringProperty(electrical_page, 'Temperature Status', read_only=True)

        electrical_page.addWidget(self.over_temp_count_ctrl)
        electrical_page.addWidget(self.operating_temp_ctrl)
        electrical_page.addWidget(self.part_temp_ctrl)
        electrical_page.addWidget(self.rated_temp_ctrl)
        electrical_page.addWidget(self.temp_status_ctrl)

        self.operating_temp_ctrl.propertyChanged.connect(self._on_operating_temp)

        weight_page = _prop_ctrls.Category(self, 'Weight')

        circuit_weight_group = _prop_ctrls.Property(weight_page, 'Total Circuit Weight', orientation='vertical')
        weight_page.addWidget(circuit_weight_group)

        self.total_circuit_weight_g_ctrl = _prop_ctrls.StringProperty(circuit_weight_group, 'Grams', read_only=True)
        self.total_circuit_weight_lb_ctrl = _prop_ctrls.StringProperty(circuit_weight_group, 'Pounds', read_only=True)

        circuit_weight_group.addWidget(self.total_circuit_weight_g_ctrl)
        circuit_weight_group.addWidget(self.total_circuit_weight_lb_ctrl)

        wire_weight_group = _prop_ctrls.Property(weight_page, 'Total Wire Weight', orientation='vertical')
        weight_page.addWidget(wire_weight_group)

        self.wire_weight_g_ctrl = _prop_ctrls.StringProperty(wire_weight_group, 'Grams', read_only=True)
        self.wire_weight_lb_ctrl = _prop_ctrls.StringProperty(wire_weight_group, 'Pounds', read_only=True)

        wire_weight_group.addWidget(self.wire_weight_g_ctrl)
        wire_weight_group.addWidget(self.wire_weight_lb_ctrl)

        terminal_weight_group = _prop_ctrls.Property(weight_page, 'Total Terminal Weight', orientation='vertical')
        weight_page.addWidget(terminal_weight_group)

        self.terminal_weight_g_ctrl = _prop_ctrls.StringProperty(terminal_weight_group, 'Grams', read_only=True)
        self.terminal_weight_lb_ctrl = _prop_ctrls.StringProperty(terminal_weight_group, 'Pounds', read_only=True)

        terminal_weight_group.addWidget(self.terminal_weight_g_ctrl)
        terminal_weight_group.addWidget(self.terminal_weight_lb_ctrl)

        splice_weight_group = _prop_ctrls.Property(weight_page, 'Total Splice Weight', orientation='vertical')
        weight_page.addWidget(splice_weight_group)

        self.splice_weight_g_ctrl = _prop_ctrls.StringProperty(splice_weight_group, 'Grams', read_only=True)
        self.splice_weight_lb_ctrl = _prop_ctrls.StringProperty(splice_weight_group, 'Pounds', read_only=True)

        splice_weight_group.addWidget(self.splice_weight_g_ctrl)
        splice_weight_group.addWidget(self.splice_weight_lb_ctrl)

        length_page = _prop_ctrls.Category(self, 'Length')

        total_length_group = _prop_ctrls.Property(weight_page, 'Total Wire Length', orientation='vertical')
        length_page.addWidget(total_length_group)

        self.wire_length_mm_ctrl = _prop_ctrls.StringProperty(total_length_group, 'Millimeters', read_only=True)
        self.wire_length_m_ctrl = _prop_ctrls.StringProperty(total_length_group, 'Meters', read_only=True)
        self.wire_length_ft_ctrl = _prop_ctrls.StringProperty(total_length_group, 'Feet', read_only=True)

        total_length_group.addWidget(self.wire_length_mm_ctrl)
        total_length_group.addWidget(self.wire_length_m_ctrl)
        total_length_group.addWidget(self.wire_length_ft_ctrl)

        for page in (
            general_page,
            electrical_page,
            weight_page,
            length_page
        ):
            self.addTab(page, page.GetLabel())


from . import pjt_wire as _pjt_wire  # NOQA
from . import pjt_splice as _pjt_splice  # NOQA
from . import pjt_terminal as _pjt_terminal  # NOQA
from . import pjt_housing as _pjt_housing  # NOQA
from . import pjt_wire_service_loop as _pjt_wire_service_loop  # NOQA
