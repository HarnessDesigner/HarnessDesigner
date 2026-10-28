# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Global-DB table class for ``deratings``.

The manufacturer's derating table of a terminal, a wire or a splice, one row
per row of the table. This table class caches them: a part's WHOLE table is
read in one query, by :meth:`DeratingsTable.for_part`, which the terminals,
wires and splices tables call from their ``__getitem__`` as the part is
loaded, so by the time anything asks the part for its table it is already
here. The rows are plain :class:`Derating` values, not row wrappers cached one
at a time. See :mod:`harness_designer.database.create_database.deratings` for
the schema.
"""

from typing import TYPE_CHECKING
from typing import Iterable as _Iterable
from typing import NamedTuple as _NamedTuple

from .bases import TableBase
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ..create_database import deratings as _deratings
    from . import bases as _glb_bases
    from ... import splash_screen as _splash_screen


def _schema() -> "_deratings":
    """The schema module, imported when it is first needed: it brings in the schema of the terminals, wires and
    splices, which the database package cannot do while its own modules are still being imported (the schema modules
    of the other global tables are imported the same late way)."""
    from ..create_database import deratings

    return deratings


# the column of ``deratings`` that points at each kind of part, by the part's own table name
_PART_COLUMNS = {
    'terminals': 'terminal_id',
    'wires': 'wire_id',
    'splices': 'splice_id'
}

# the columns of a row, in the order a ``Derating`` takes them
_COLUMNS = ('id', 'idx', 'terminal_id', 'wire_id', 'splice_id', 'ambient_temp_c', 'conductor_count', 'max_amps',
            'derating_factor')


class Derating(_NamedTuple):
    """One row of a part's derating table. A plain value: the table is the
    manufacturer's, so it is never edited through this."""

    id: bytes

    idx: int
    """The row's position within its part's table."""

    terminal_id: bytes | None
    wire_id: bytes | None
    splice_id: bytes | None
    """Exactly one of these three is set: the part the table belongs to."""

    ambient_temp_c: float | None
    """The ambient temperature, in degrees Celsius, the row applies at; ``None`` when the table does not use one."""

    conductor_count: int | None
    """The number of bundled current-carrying conductors the row applies at; ``None`` for an ambient row."""

    max_amps: float | None
    """The most current, in amps, the part may carry under the row's conditions; ``None`` when the row gives a factor."""

    derating_factor: float | None
    """The fraction of the part's rated current it may carry under the row's conditions; ``None`` when the row gives amps."""


class DeratingsTable(TableBase):
    """Manage the ``deratings`` table, and hold the table of every part that has been loaded."""

    __table_name__ = 'deratings'

    @_check_types.do
    def __init__(self, db: "_glb_bases.GLBTables", table_names: list[str], splash: "_splash_screen.Splash",
                 load_database: bool):
        """Create the table if it is missing and make sure a part's rows can be found without reading every row.

        :param db: Database accessor.
        :type db: :class:`GLBTables`
        :param table_names: The tables the database already has.
        :type table_names: list[str]
        :param splash: The splash screen.
        :type splash: :class:`_splash_screen.Splash`
        :param load_database: Whether to load the database.
        :type load_database: bool
        """
        # part id -> that part's whole derating table (empty when it has none), filled by for_part
        self._by_part: dict[bytes, tuple[Derating, ...]] = {}

        TableBase.__init__(self, db, table_names, splash, load_database)

        # the catalog may have been built by something that knows nothing of these indexes, so ask every start
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
    def __iter__(self) -> _Iterable[Derating]:
        self._con.execute(f'SELECT {", ".join(_COLUMNS)} FROM {self.__table_name__};')

        for row in self._con.fetchall():
            yield Derating(*row)

    @_check_types.do
    def __getitem__(self, item: bytes) -> Derating:
        rows = self.select(*_COLUMNS, id=item)

        if not rows:
            raise KeyError(item)

        return Derating(*rows[0])

    @_check_types.do
    def for_part(self, part_table_name: str, part_id: bytes) -> tuple[Derating, ...]:
        """Return a part's whole derating table, first row first.

        Read from the database in one query the first time a part is asked
        about (a part with no table is remembered as having none, so it is not
        asked about again), then served from memory.

        :param part_table_name: The part's own table: ``'terminals'``, ``'wires'`` or ``'splices'``.
        :type part_table_name: str
        :param part_id: The part's row id.
        :type part_id: bytes
        :returns: The part's rows by ``idx``; empty when the manufacturer gave no table.
        :rtype: tuple[Derating, ...]
        :raises KeyError: *part_table_name* is not a table that has derating rows.
        """
        column = _PART_COLUMNS[part_table_name]

        rows = self._by_part.get(part_id)

        if rows is None:
            self._con.execute(
                f'SELECT {", ".join(_COLUMNS)} FROM {self.__table_name__} WHERE {column} = ? ORDER BY idx;',
                (part_id,))

            rows = tuple(Derating(*row) for row in self._con.fetchall())
            self._by_part[part_id] = rows

        return rows

    @_check_types.do
    def forget(self, part_id: bytes) -> None:
        """Drop a part's table from memory, so the next :meth:`for_part` reads it again.

        :param part_id: The part's row id.
        :type part_id: bytes
        """
        self._by_part.pop(part_id, None)

    @_check_types.do
    def insert(self, idx: int, terminal_id: bytes | None = None, wire_id: bytes | None = None,
               splice_id: bytes | None = None, ambient_temp_c: float | None = None,
               conductor_count: int | None = None, max_amps: float | None = None,
               derating_factor: float | None = None) -> Derating:
        """Add one row of a part's derating table. The part's table in memory, if it has one, is dropped and
        read again the next time it is asked for.

        :param idx: The row's position within its part's table.
        :type idx: int
        :param terminal_id: The terminal the table belongs to.
        :type terminal_id: bytes | None
        :param wire_id: The wire the table belongs to.
        :type wire_id: bytes | None
        :param splice_id: The splice the table belongs to.
        :type splice_id: bytes | None
        :param ambient_temp_c: The ambient temperature the row applies at, in degrees Celsius.
        :type ambient_temp_c: float | None
        :param conductor_count: The number of bundled current-carrying conductors the row applies at.
        :type conductor_count: int | None
        :param max_amps: The most current the part may carry, in amps.
        :type max_amps: float | None
        :param derating_factor: The fraction of the part's rated current it may carry.
        :type derating_factor: float | None
        :returns: The new row.
        :rtype: Derating
        :raises ValueError: Not exactly one of the three part ids is given, or neither
            ``max_amps`` nor ``derating_factor`` is.
        """
        part_ids = [part_id for part_id in (terminal_id, wire_id, splice_id) if part_id is not None]

        if len(part_ids) != 1:
            raise ValueError('a derating row belongs to exactly one of a terminal, a wire or a splice')

        if max_amps is None and derating_factor is None:
            raise ValueError('a derating row needs max_amps or derating_factor')

        db_id = TableBase.insert(
            self, terminal_id=terminal_id, wire_id=wire_id, splice_id=splice_id, idx=idx,
            ambient_temp_c=ambient_temp_c, conductor_count=conductor_count, max_amps=max_amps,
            derating_factor=derating_factor)

        self.forget(part_ids[0])

        return self[db_id]
