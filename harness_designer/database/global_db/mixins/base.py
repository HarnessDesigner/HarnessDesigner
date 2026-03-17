from ..bases import TableBase


class BaseMixin:
    _table: TableBase = None
    _db_id: int = None
    
    @property
    def table(self):
        return self._table
