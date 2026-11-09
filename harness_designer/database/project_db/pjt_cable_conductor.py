# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A conductor of a placed cable, and the shielding of a shielded cable.

``PJTCableConductor`` subclasses :class:`~.pjt_wire.PJTWire`: a conductor is wire-like. It is what a circuit contains, it
lands on a terminal or splice at each end and it has a route, so ``pjt_cable_conductors`` has every column of
``pjt_wires`` and the wire's code runs on it unchanged except where a conductor differs (its own resistance, below).
The table adds the cable it is in, its place in the cable, whether it is the shield, the catalog conductor it was copied
from, its own colour / size, and where it splits from the cable's trunk at each end. See ``TWISTED_WIRE_DESIGN.md``
section 8a in the repo root.

A SPLIT end gives the conductor a LEAD there (an ordinary ``pjt_wires`` wire, ``cable_conductor_id`` set), and the conductor
is then the middle of the run, a junction like a wire service loop whose connection points are its two split points
(5b stage 3 / 4): ``PJTCircuitsTable.connected_members`` and ``PJTCircuit`` know it (``cable_conductors``), so a circuit
crosses it from one lead to the other. ``length_mm`` is the conductor's TRUNK, the cable's length less its two splits
(the leads are wires of their own), along the cable's axis (the helix of a twisted conductor, a percent or two, is not
counted); the weights are the cable's divided by its number of conductor rows; ``resistance`` is the row's own
``resistance_1km`` over that length.

A conductor holds none of its own values: its ``part`` is the catalog conductor it is (``wire_conductors``, a
:class:`~..global_db.wire_conductor.WireConductor`, which answers what a ``Wire`` does; the shield, which has no row, is a
:class:`~..global_db.wire_conductor.ShieldConductor`). It is edited in the object editor like any wire; its Part tab is the
cable's catalog wire, whose Conductors tab edits the ``wire_conductors`` rows, so a change is made to the part itself.
"""

from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTTableBase
from .pjt_wire import PJTWire, PJTWiresTable
from ..global_db import wire_conductor as _wire_conductor_part
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from . import pjt_cable as _pjt_cable
    from . import pjt_point3d as _pjt_point3d
    from ..global_db import wire as _wire
    from ..global_db import wire_conductor as _wire_conductor
    from ... import ui as _ui


class PJTCableConductorsTable(PJTWiresTable):
    """Table of the conductors (and shields) of the placed cables (``pjt_cable_conductors``).

    Subclasses :class:`~.pjt_wire.PJTWiresTable` so a lookup by end point (``find_by_start_point3d_id`` ...) and the
    wire's other table code work on conductors; the row class, the schema and the ``insert`` are its own.
    """

    __table_name__ = 'pjt_cable_conductors'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import cable_conductors

        return cable_conductors.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Create the ``pjt_cable_conductors`` table in the database."""
        from ..create_database import cable_conductors

        cable_conductors.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Add any missing fields to the ``pjt_cable_conductors`` table."""
        from ..create_database import cable_conductors

        cable_conductors.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTCableConductor"]:
        """Iterate over every conductor of the open project.

        :returns: An iterator of :class:`PJTCableConductor` rows.
        :rtype: _Iterable['PJTCableConductor']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCableConductor(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTCableConductor":
        """Return the conductor with the given database id.

        :param item: Row id to look up.
        :type item: int | bytes | str
        :returns: The matching row.
        :rtype: :class:`PJTCableConductor`
        :raises KeyError: Raised when ``item`` is not an ``int`` or ``bytes``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTCableConductor or item in self:
                return PJTCableConductor(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def for_cable(self, cable_id: bytes) -> list["PJTCableConductor"]:
        """Return the conductors of a cable, then its shield if it has one: ``idx`` order.

        :param cable_id: The ``pjt_cables`` row.
        :type cable_id: bytes
        :rtype: list[:class:`PJTCableConductor`]
        """
        rows = self.select('id', 'idx', cable_id=cable_id)
        rows.sort(key=lambda row: row[1])

        return [self[row[0]] for row in rows]

    @_check_types.do
    def new_conductor_values(self, part: "_wire.Wire") -> list[dict]:
        """The rows a new cable's conductors take, in ``idx`` order: ``idx``, ``is_shield`` and ``conductor_id`` (the catalog
        conductor the row is; ``None`` for a shield).

        One entry per catalog conductor (``wire_conductors``), then one more for the shield when the part is shielded (a
        shield has no catalog row).

        :param part: The cable's catalog wire.
        :type part: :class:`_wire.Wire`
        :rtype: list[dict]
        """
        values = [dict(idx=conductor.idx, is_shield=False, conductor_id=conductor.id) for conductor in part.conductors]

        if part.shielded:
            values.append(dict(idx=len(values), is_shield=True, conductor_id=None))

        return values

    @_check_types.do
    def insert_for_cable(self, cable: "_pjt_cable.PJTCable") -> list["PJTCableConductor"]:
        """Make the conductor rows (and the shield's) of a placed cable from its catalog part.

        Each conductor gets two end points of its own in 3D, children of the cable's start and stop points
        (``parent_point_id``): they sit on the cable's ends and follow them while nothing is split, but a terminal or
        splice attached to one conductor's end does not take the others with it. The points are made into live ``Point``
        objects here so that they follow their parents from now on; a reloaded project does that when the cable object
        is built. Call it when the cable's own end points are final, not while it is still being placed.

        :param cable: The cable row, with no conductors yet.
        :type cable: :class:`_pjt_cable.PJTCable`
        :returns: The new rows, in ``idx`` order.
        :rtype: list[:class:`PJTCableConductor`]
        """
        points = self.db.pjt_points3d_table
        part = cable.part

        start_parent = points[cable.start_position3d_id]
        stop_parent = points[cable.stop_position3d_id]

        rows = []

        for values in self.new_conductor_values(part):
            start = self._child_point(points, start_parent)
            stop = self._child_point(points, stop_parent)

            if values['is_shield']:
                label = 'Shield'
            else:
                label = str(values['idx'] + 1)

            rows.append(self.insert(
                part.db_id, f'{cable.name} {label}', cable.db_id, values['idx'], values['is_shield'],
                values['conductor_id'], start.db_id, stop.db_id, None, None, True, True))

        return rows

    @staticmethod
    @_check_types.do
    def _child_point(points: "_pjt_point3d.PJTPoints3DTable", parent: "_pjt_point3d.PJTPoint3D") -> "_pjt_point3d.PJTPoint3D":
        """A new 3D point at *parent*'s place that follows *parent* when it moves.

        :param points: The 3D points table.
        :type points: :class:`_pjt_point3d.PJTPoints3DTable`
        :param parent: The point to sit on and follow.
        :type parent: :class:`_pjt_point3d.PJTPoint3D`
        :rtype: :class:`_pjt_point3d.PJTPoint3D`
        """
        child = points.insert(parent.x, parent.y, parent.z)
        child.parent_point_id = parent.db_id

        # the live Point binds the follow-the-parent callback when it is first made
        child.point  # NOQA

        return child

    @_check_types.do
    def insert(self, part_id: bytes, name: str, cable_id: bytes, idx: int, is_shield: bool, conductor_id: bytes | None,
               start_point3d_id: bytes | None, stop_point3d_id: bytes | None,
               start_point_pegboard_id: bytes | None, stop_point_pegboard_id: bytes | None,
               is_visible3d: bool, is_visible_pegboard: bool) -> "PJTCableConductor":
        """Insert one conductor (or shield) row of a cable.

        The row starts in no circuit, with no 2D (schematic) end points, no split points and its ``idx`` as its place in
        both fan-outs. ``new_conductor_values`` gives ``idx``, ``is_shield`` and ``conductor_id``.

        :param part_id: The cable's catalog wire (the cable's own ``part_id``).
        :type part_id: bytes
        :param name: The conductor's name.
        :type name: str
        :param cable_id: The ``pjt_cables`` row it is in.
        :type cable_id: bytes
        :param idx: Its place inside the cable.
        :type idx: int
        :param is_shield: Whether it is the cable's shielding.
        :type is_shield: bool
        :param conductor_id: The catalog conductor (``wire_conductors``) it is; ``None`` for a shield.
        :type conductor_id: bytes | None
        :param start_point3d_id: 3D point where the conductor lands at the cable start.
        :type start_point3d_id: bytes | None
        :param stop_point3d_id: 3D point where it lands at the cable stop.
        :type stop_point3d_id: bytes | None
        :param start_point_pegboard_id: Peg-board point where it lands at the cable start.
        :type start_point_pegboard_id: bytes | None
        :param stop_point_pegboard_id: Peg-board point where it lands at the cable stop.
        :type stop_point_pegboard_id: bytes | None
        :param is_visible3d: Whether it shows in the 3D editor.
        :type is_visible3d: bool
        :param is_visible_pegboard: Whether it shows on the peg board.
        :type is_visible_pegboard: bool
        :returns: The new row.
        :rtype: :class:`PJTCableConductor`
        """
        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name, circuit_id=None, bundle_id=None, transition_id=None,
            start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
            start_point2d_id=None, stop_point2d_id=None,
            start_point_pegboard_id=start_point_pegboard_id, stop_point_pegboard_id=stop_point_pegboard_id,
            layer_view_point_id=None, layer_id=None, is_filler_wire=0, notes='',
            is_visible2d=1, is_visible3d=int(is_visible3d), is_visible_pegboard=int(is_visible_pegboard),
            smooth=None, operating_temp=None,
            cable_id=cable_id, idx=idx, is_shield=int(is_shield), conductor_id=conductor_id,
            start_split_point3d_id=None, stop_split_point3d_id=None,
            start_split_point_pegboard_id=None, stop_split_point_pegboard_id=None,
            start_order=idx, stop_order=idx)

        return PJTCableConductor(self, db_id)


@capturable()
class PJTCableConductor(PJTWire):
    """A conductor of a placed cable, or its shield (``is_shield``). A wire to everything that handles wires."""

    _table: PJTCableConductorsTable = None

    @property
    @_check_types.do
    def cable(self) -> "_pjt_cable.PJTCable":
        """The cable this conductor is in.

        :rtype: :class:`_pjt_cable.PJTCable`
        """
        return self._table.db.pjt_cables_table[self.cable_id]

    @property
    @_check_types.do
    def conductor(self) -> "_wire_conductor.WireConductor | None":
        """The catalog conductor this row is; ``None`` for a shield.

        :rtype: :class:`_wire_conductor.WireConductor` | None
        """
        conductor_id = self.conductor_id

        if conductor_id is None:
            return None

        return self._table.db.global_db.wire_conductors_table[conductor_id]

    @property
    @_check_types.do
    def part(self) -> "_wire_conductor.WireConductor | _wire_conductor.ShieldConductor":
        """The part of this row: the catalog conductor it is (a ``WireConductor``, which answers what a ``Wire`` does, and
        is edited in the catalog: the change is global), or, for the shield, which has no catalog row, a
        ``ShieldConductor``.

        :rtype: :class:`_wire_conductor.WireConductor` | :class:`_wire_conductor.ShieldConductor`
        """
        conductor = self.conductor

        if conductor is not None:
            return conductor

        return _wire_conductor_part.ShieldConductor(self._table.db.global_db.wires_table[self.part_id])

    @property
    @_check_types.do
    def cable_conductor_id(self) -> None:
        """A conductor is not a lead of one (``pjt_cable_conductors`` has no such column): always ``None``.

        :rtype: None
        """
        return None

    @cable_conductor_id.setter
    @_check_types.do
    def cable_conductor_id(self, value: None) -> None:
        """Nothing to store: a conductor is not a lead.

        :param value: Ignored.
        :type value: None
        """

    @property
    @_check_types.do
    def length_mm(self) -> float:
        """The length of the conductor's trunk in mm: the cable's length. A split end of the cable lies at the split plane, so what the
        leads cover (wires of their own) is not in it. Along the cable's axis.

        :rtype: float
        """
        return self.cable.length_mm

    @property
    @_check_types.do
    def weight_g(self) -> float:
        """The weight in grams of this conductor's trunk: the cable's weight per metre shared among its conductors.

        :rtype: float
        """
        return self.part.weight_g_m * self.length_m

    @property
    @_check_types.do
    def weight_lb(self) -> float:
        """The weight in pounds of this conductor's trunk.

        :rtype: float
        """
        return self.part.weight_lb_ft * self.length_ft

    @_check_types.do
    def _resistance_over(self, length_mm: float) -> float:
        """The resistance, in ohms, of *length_mm* of this conductor: the catalog conductor's own ``resistance_1km``.

        :param length_mm: The length in millimeters.
        :type length_mm: float
        :returns: The resistance in ohms.
        :rtype: float
        """
        return self.part.resistance_1km / 1000000.0 * length_mm

    @property
    @dump_property(severity=2)
    @_check_types.do
    def cable_id(self) -> bytes:
        """The id of the cable (``pjt_cables``) this conductor is in.

        :rtype: bytes
        """
        return self._table.select('cable_id', id=self._db_id)[0][0]

    @cable_id.setter
    @_check_types.do
    def cable_id(self, value: bytes) -> None:
        """Set the cable this conductor is in.

        :param value: The new value.
        :type value: bytes
        """
        self._table.update(self._db_id, cable_id=value)
        self._populate('cable_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def idx(self) -> int:
        """The conductor's place inside the cable, 0 first; the shield, when there is one, is last.

        :rtype: int
        """
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    @_check_types.do
    def idx(self, value: int) -> None:
        """Set the conductor's place inside the cable.

        :param value: The new value.
        :type value: int
        """
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def is_shield(self) -> bool:
        """Whether this row is the cable's shielding, not a conductor.

        :rtype: bool
        """
        return bool(self._table.select('is_shield', id=self._db_id)[0][0])

    @is_shield.setter
    @_check_types.do
    def is_shield(self, value: bool) -> None:
        """Set whether this row is the cable's shielding.

        :param value: The new value.
        :type value: bool
        """
        self._table.update(self._db_id, is_shield=int(value))
        self._populate('is_shield')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def conductor_id(self) -> bytes | None:
        """The catalog conductor (``wire_conductors``) this row was copied from; ``None`` for a shield.

        :rtype: bytes | None
        """
        return self._table.select('conductor_id', id=self._db_id)[0][0]

    @conductor_id.setter
    @_check_types.do
    def conductor_id(self, value: bytes | None) -> None:
        """Set the catalog conductor this row was copied from.

        :param value: The new value.
        :type value: bytes | None
        """
        self._table.update(self._db_id, conductor_id=value)
        self._populate('conductor_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_split_point3d_id(self) -> bytes | None:
        """The 3D point where the conductor leaves the cable trunk at the cable start.

        :rtype: bytes | None
        """
        return self._table.select('start_split_point3d_id', id=self._db_id)[0][0]

    @start_split_point3d_id.setter
    @_check_types.do
    def start_split_point3d_id(self, value: bytes | None) -> None:
        """Set the 3D point where the conductor leaves the cable trunk at the cable start.

        :param value: The new value.
        :type value: bytes | None
        """
        self._table.update(self._db_id, start_split_point3d_id=value)
        self._populate('start_split_point3d_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def stop_split_point3d_id(self) -> bytes | None:
        """The 3D point where the conductor leaves the cable trunk at the cable stop.

        :rtype: bytes | None
        """
        return self._table.select('stop_split_point3d_id', id=self._db_id)[0][0]

    @stop_split_point3d_id.setter
    @_check_types.do
    def stop_split_point3d_id(self, value: bytes | None) -> None:
        """Set the 3D point where the conductor leaves the cable trunk at the cable stop.

        :param value: The new value.
        :type value: bytes | None
        """
        self._table.update(self._db_id, stop_split_point3d_id=value)
        self._populate('stop_split_point3d_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_split_point_pegboard_id(self) -> bytes | None:
        """The peg-board point where the conductor leaves the cable trunk at the cable start.

        :rtype: bytes | None
        """
        return self._table.select('start_split_point_pegboard_id', id=self._db_id)[0][0]

    @start_split_point_pegboard_id.setter
    @_check_types.do
    def start_split_point_pegboard_id(self, value: bytes | None) -> None:
        """Set the peg-board point where the conductor leaves the cable trunk at the cable start.

        :param value: The new value.
        :type value: bytes | None
        """
        self._table.update(self._db_id, start_split_point_pegboard_id=value)
        self._populate('start_split_point_pegboard_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def stop_split_point_pegboard_id(self) -> bytes | None:
        """The peg-board point where the conductor leaves the cable trunk at the cable stop.

        :rtype: bytes | None
        """
        return self._table.select('stop_split_point_pegboard_id', id=self._db_id)[0][0]

    @stop_split_point_pegboard_id.setter
    @_check_types.do
    def stop_split_point_pegboard_id(self, value: bytes | None) -> None:
        """Set the peg-board point where the conductor leaves the cable trunk at the cable stop.

        :param value: The new value.
        :type value: bytes | None
        """
        self._table.update(self._db_id, stop_split_point_pegboard_id=value)
        self._populate('stop_split_point_pegboard_id')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_order(self) -> int:
        """The conductor's place in the fan-out at the cable start (``idx`` by default).

        :rtype: int
        """
        return self._table.select('start_order', id=self._db_id)[0][0]

    @start_order.setter
    @_check_types.do
    def start_order(self, value: int) -> None:
        """Set the conductor's place in the fan-out at the cable start.

        :param value: The new value.
        :type value: int
        """
        self._table.update(self._db_id, start_order=value)
        self._populate('start_order')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def stop_order(self) -> int:
        """The conductor's place in the fan-out at the cable stop (``idx`` by default).

        :rtype: int
        """
        return self._table.select('stop_order', id=self._db_id)[0][0]

    @stop_order.setter
    @_check_types.do
    def stop_order(self, value: int) -> None:
        """Set the conductor's place in the fan-out at the cable stop.

        :param value: The new value.
        :type value: int
        """
        self._table.update(self._db_id, stop_order=value)
        self._populate('stop_order')
