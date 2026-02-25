from .. import TableBase


class BaseMixin:
    _table: TableBase = None
    _db_id: int = None
