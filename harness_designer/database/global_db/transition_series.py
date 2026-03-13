from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class TransitionSeriesTable(TableBase):
    __table_name__ = 'transition_series'

    def _table_needs_update(self) -> bool:
        from ..create_database import transition_series

        return transition_series.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import transition_series

        transition_series.table.add_to_db(self)
        transition_series.add_records(self._con, splash)

    def _update_table_in_db(self):
        from ..create_database import transition_series

        transition_series.table.update_fields(self)

    def __iter__(self) -> _Iterable["TransitionSeries"]:
        for db_id in TableBase.__iter__(self):
            yield TransitionSeries(self, db_id)

    def __getitem__(self, item) -> "TransitionSeries":
        if isinstance(item, int):
            if item in self:
                return TransitionSeries(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return TransitionSeries(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str) -> "TransitionSeries":
        db_id = TableBase.insert(self, name=name)
        return TransitionSeries(self, db_id)


class TransitionSeries(EntryBase, NameMixin):
    _table: TransitionSeriesTable = None

