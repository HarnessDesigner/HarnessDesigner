from ..pjt_bases import PJTTableBase, PJTEntryBase


class BaseMixin:
    _table: PJTTableBase = None
    _db_id: int = None
    _obj = None

    def _populate(self, tag):
        PJTEntryBase._populate(self, tag)  # NOQA
