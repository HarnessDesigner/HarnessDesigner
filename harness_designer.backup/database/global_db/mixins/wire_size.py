from .base import BaseMixin


class WireSizeMixin(BaseMixin):

    @property
    def min_size_mm2(self) -> float | None:
        return self._table.select('min_size_mm2', id=self._db_id)[0][0]

    @min_size_mm2.setter
    def min_size_mm2(self, value: float):
        self._table.update(self._db_id, min_size_mm2=value)

    @property
    def max_size_mm2(self) -> float | None:
        return self._table.select('max_size_mm2', id=self._db_id)[0][0]

    @max_size_mm2.setter
    def max_size_mm2(self, value: float):
        self._table.update(self._db_id, max_size_mm2=value)

    @property
    def min_size_awg(self) -> int | None:
        return self._table.select('min_size_awg', id=self._db_id)[0][0]

    @min_size_awg.setter
    def min_size_awg(self, value: int):
        self._table.update(self._db_id, min_size_awg=value)

    @property
    def max_size_awg(self) -> int | None:
        return self._table.select('max_size_awg', id=self._db_id)[0][0]

    @max_size_awg.setter
    def max_size_awg(self, value: int):
        self._table.update(self._db_id, max_size_awg=value)
