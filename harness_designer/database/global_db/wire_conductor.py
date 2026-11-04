# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Global-DB table class for ``wire_conductors``.

The individual conductors inside a multi-conductor wire, one row per conductor. This table class caches them: a
wire's WHOLE set of conductors is read in one query, by :meth:`WireConductorsTable.for_wire`, which the wires table
calls from its ``__getitem__`` as the wire is loaded, so by the time anything asks the wire for its conductors they
are already here. The rows are plain :class:`WireConductor` values, not row wrappers cached one at a time. See
:mod:`harness_designer.database.create_database.wire_conductors` for the schema.
"""

from typing import TYPE_CHECKING
from typing import Iterable as _Iterable
from typing import NamedTuple as _NamedTuple

from .bases import TableBase
from .. import id_generator as _id_generator
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ..create_database import wire_conductors as _wire_conductors
    from . import bases as _glb_bases
    from ... import splash_screen as _splash_screen


def _schema() -> "_wire_conductors":
    """The schema module, imported when it is first needed: it brings in the schema of the wires, which the database
    package cannot do while its own modules are still being imported (the schema modules of the other global tables
    are imported the same late way)."""
    from ..create_database import wire_conductors

    return wire_conductors


# the columns of a row, in the order a ``WireConductor`` takes them
_COLUMNS = ('id', 'wire_id', 'idx', 'color_id', 'stripe_color_id', 'core_material_id', 'material_id', 'wire_size_dia',
            'wire_size_cross', 'wire_size_awg', 'strands', 'od_mm', 'resistance_1km')


class WireConductor(_NamedTuple):
    """One conductor inside a multi-conductor wire. A plain value: the catalog is the manufacturer's, so it is
    never edited through this."""

    id: bytes

    wire_id: bytes
    """The cable this conductor sits in."""

    idx: int
    """The conductor's position within the cable; the first is ``0``."""

    color_id: bytes
    """The colour of this conductor's insulation."""

    stripe_color_id: bytes
    """The colour of its stripe; ``id_generator.NO_COLOR_UUID`` when it has none."""

    core_material_id: bytes
    """The plating of the metal (a ``platings`` row)."""

    material_id: bytes
    """The insulation (a ``materials`` row)."""

    wire_size_dia: float | None
    """The diameter of the stranded metal, in mm."""

    wire_size_cross: float | None
    """The cross-section of the metal, in mm^2."""

    wire_size_awg: int | None
    """The AWG size; negative for 0/00 sizes (-2 is 2/0)."""

    strands: int
    """The number of strands."""

    od_mm: float
    """The diameter over this conductor's insulation, in mm."""

    resistance_1km: float
    """The resistance per km of cable, in ohms."""

    @property
    def has_stripe(self) -> bool:
        """Whether the conductor has a stripe."""
        return self.stripe_color_id != _id_generator.NO_COLOR_UUID.bytes


class WireConductorsTable(TableBase):
    """Manage the ``wire_conductors`` table, and hold the conductors of every wire that has been loaded."""

    __table_name__ = 'wire_conductors'

    @_check_types.do
    def __init__(self, db: "_glb_bases.GLBTables", table_names: list[str], splash: "_splash_screen.Splash",
                 load_database: bool):
        """Create the table if it is missing and make sure a wire's rows can be found without reading every row.

        :param db: Database accessor.
        :type db: :class:`GLBTables`
        :param table_names: The tables the database already has.
        :type table_names: list[str]
        :param splash: The splash screen.
        :type splash: :class:`_splash_screen.Splash`
        :param load_database: Whether to load the database.
        :type load_database: bool
        """
        # wire id -> that wire's conductors (empty when it has none), filled by for_wire
        self._by_wire: dict[bytes, tuple[WireConductor, ...]] = {}

        TableBase.__init__(self, db, table_names, splash, load_database)

        # the catalog may have been built by something that knows nothing of this index, so ask every start
        _schema().add_indexes(self)

    @_check_types.do
    def _table_needs_update(self) -> bool:
        return _schema().table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, _: "_splash_screen.Splash") -> None:
        _schema().table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        _schema().table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable[WireConductor]:
        self._con.execute(f'SELECT {", ".join(_COLUMNS)} FROM {self.__table_name__};')

        for row in self._con.fetchall():
            yield WireConductor(*row)

    @_check_types.do
    def __getitem__(self, item: bytes) -> WireConductor:
        rows = self.select(*_COLUMNS, id=item)

        if not rows:
            raise KeyError(item)

        return WireConductor(*rows[0])

    @_check_types.do
    def for_wire(self, wire_id: bytes) -> tuple[WireConductor, ...]:
        """Return a wire's conductors, first conductor first.

        Read from the database in one query the first time a wire is asked about (a wire with no conductors rows
        is remembered as having none, so it is not asked about again), then served from memory.

        :param wire_id: The wire's row id.
        :type wire_id: bytes
        :returns: The wire's conductors by ``idx``; empty for a single-conductor wire.
        :rtype: tuple[WireConductor, ...]
        """
        rows = self._by_wire.get(wire_id)

        if rows is None:
            self._con.execute(
                f'SELECT {", ".join(_COLUMNS)} FROM {self.__table_name__} WHERE wire_id = ? ORDER BY idx;',
                (wire_id,))

            rows = tuple(WireConductor(*row) for row in self._con.fetchall())
            self._by_wire[wire_id] = rows

        return rows

    @_check_types.do
    def forget(self, wire_id: bytes) -> None:
        """Drop a wire's conductors from memory, so the next :meth:`for_wire` reads them again.

        :param wire_id: The wire's row id.
        :type wire_id: bytes
        """
        self._by_wire.pop(wire_id, None)

    @_check_types.do
    def insert(self, wire_id: bytes, idx: int, color_id: bytes, stripe_color_id: bytes, core_material_id: bytes,
               material_id: bytes, wire_size_dia: float | None = None, wire_size_cross: float | None = None,
               wire_size_awg: int | None = None, strands: int = 1, od_mm: float = 0.0,
               resistance_1km: float = 0.0) -> WireConductor:
        """Add one conductor to a wire. The wire's conductors in memory, if it has any, are dropped and read again
        the next time they are asked for.

        :param wire_id: The cable the conductor sits in.
        :type wire_id: bytes
        :param idx: The conductor's position within the cable.
        :type idx: int
        :param color_id: The colour of the conductor's insulation.
        :type color_id: bytes
        :param stripe_color_id: The colour of its stripe; ``id_generator.NO_COLOR_UUID`` for none.
        :type stripe_color_id: bytes
        :param core_material_id: The plating of the metal.
        :type core_material_id: bytes
        :param material_id: The insulation.
        :type material_id: bytes
        :param wire_size_dia: The diameter of the stranded metal, in mm.
        :type wire_size_dia: float | None
        :param wire_size_cross: The cross-section of the metal, in mm^2.
        :type wire_size_cross: float | None
        :param wire_size_awg: The AWG size.
        :type wire_size_awg: int | None
        :param strands: The number of strands.
        :type strands: int
        :param od_mm: The diameter over the conductor's insulation, in mm.
        :type od_mm: float
        :param resistance_1km: The resistance per km of cable, in ohms.
        :type resistance_1km: float
        :returns: The new row.
        :rtype: WireConductor
        """
        db_id = TableBase.insert(
            self, wire_id=wire_id, idx=idx, color_id=color_id, stripe_color_id=stripe_color_id,
            core_material_id=core_material_id, material_id=material_id, wire_size_dia=wire_size_dia,
            wire_size_cross=wire_size_cross, wire_size_awg=wire_size_awg, strands=strands, od_mm=od_mm,
            resistance_1km=resistance_1km)

        self.forget(wire_id)

        return self[db_id]
