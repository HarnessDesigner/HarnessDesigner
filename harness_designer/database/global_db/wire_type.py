# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import splash as _splash


class WireTypesTable(TableBase):
    """The wire types table ("Wire", "Coaxial", "Ribbon", ...) that ``wires.wire_type_id`` points at."""
    __table_name__ = 'wire_types'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing or differs from its definition."""
        from ..create_database import wire_types

        return wire_types.table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, splash: "_splash.Splash") -> None:
        """Create the table and add its default rows.

        :param splash: Splash screen to report progress on.
        """
        from ..create_database import wire_types

        wire_types.table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Add any columns the table is missing."""
        from ..create_database import wire_types

        wire_types.table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["WireType"]:
        """Iterate over every wire type."""
        for db_id in TableBase.__iter__(self):
            yield WireType(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "WireType":
        """Return a wire type by row id or by name.

        :param item: Row id, or the wire type name.
        :raises KeyError: There is no wire type with that name.
        :raises IndexError: There is no wire type with that id.
        """
        if isinstance(item, (int, bytes)):
            if item in WireType or item in self:
                return WireType(self, item)

            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return WireType(self, db_id[0][0])

        raise KeyError(item)

    @_check_types.do
    def insert(self, name: str) -> "WireType":
        """Add a wire type.

        :param name: Name of the wire type.
        """
        db_id = TableBase.insert(self, name=name)
        return WireType(self, db_id)

    @property
    @_check_types.do
    def choices(self) -> list[str]:
        """Every wire type name."""
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class WireType(EntryBase, NameMixin):
    """One row of the wire types table."""
    _table: WireTypesTable = None
