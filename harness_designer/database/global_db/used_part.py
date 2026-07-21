# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Global-DB table class for ``used_parts``.

Tracks accessory parts (TPA lock, CPA lock, cover, terminal) that have
previously been used together with a given housing. Intended to back a
"recently used with this housing" lookup in the UI; see
:mod:`harness_designer.database.create_database.used_parts` for the schema.
"""

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from ..create_database import used_parts as _used_parts


class UsedPartsTable(TableBase):
    """Manage the ``used_parts`` history table."""

    __table_name__ = 'used_parts'

    def _table_needs_update(self) -> bool:
        return _used_parts.table.is_ok(self)

    def _add_table_to_db(self, _):
        _used_parts.table.add_to_db(self)

    def _update_table_in_db(self):
        _used_parts.table.update_fields(self)

    def __iter__(self) -> _Iterable["UsedPart"]:
        for db_id in TableBase.__iter__(self):
            yield UsedPart(self, db_id)

    def __getitem__(self, item: int) -> "UsedPart":
        if item in self:
            return UsedPart(self, item)

        raise KeyError(item)

    def for_housing(self, housing_id: int) -> list["UsedPart"]:
        """Return every recorded usage row for the given housing."""
        rows = self.select('id', housing_id=housing_id)
        return [UsedPart(self, row[0]) for row in rows]

    def insert(self, housing_id: int, tpa_lock_id: int = None, cpa_lock_id: int = None,
               cover_id: int = None, terminal_id: int = None) -> "UsedPart":
        db_id = TableBase.insert(
            self, housing_id=housing_id, tpa_lock_id=tpa_lock_id,
            cpa_lock_id=cpa_lock_id, cover_id=cover_id, terminal_id=terminal_id)

        return UsedPart(self, db_id)


class UsedPart(EntryBase):

    _table: UsedPartsTable = None

    _stored_housing_id: DefaultStoredValueType | int = DefaultStoredValue

    @property
    def housing_id(self) -> int:
        if self._stored_housing_id is DefaultStoredValue:
            self._stored_housing_id = self._table.select('housing_id', id=self._db_id)[0][0]

        return self._stored_housing_id

    _stored_tpa_lock_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def tpa_lock_id(self) -> int | None:
        if self._stored_tpa_lock_id is DefaultStoredValue:
            self._stored_tpa_lock_id = self._table.select('tpa_lock_id', id=self._db_id)[0][0]

        return self._stored_tpa_lock_id

    _stored_cpa_lock_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def cpa_lock_id(self) -> int | None:
        if self._stored_cpa_lock_id is DefaultStoredValue:
            self._stored_cpa_lock_id = self._table.select('cpa_lock_id', id=self._db_id)[0][0]

        return self._stored_cpa_lock_id

    _stored_cover_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def cover_id(self) -> int | None:
        if self._stored_cover_id is DefaultStoredValue:
            self._stored_cover_id = self._table.select('cover_id', id=self._db_id)[0][0]

        return self._stored_cover_id

    _stored_terminal_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def terminal_id(self) -> int | None:
        if self._stored_terminal_id is DefaultStoredValue:
            self._stored_terminal_id = self._table.select('terminal_id', id=self._db_id)[0][0]

        return self._stored_terminal_id
