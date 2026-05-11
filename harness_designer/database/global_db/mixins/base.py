# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ..bases import TableBase, EntryBase


class BaseMixin:
    _table: TableBase = None
    _db_id: int = None

    @property
    def table(self):
        return self._table

    def _populate(self, tag):
        EntryBase._populate(self, tag)  # NOQA
