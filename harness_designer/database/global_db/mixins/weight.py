from .base import BaseMixin


class WeightMixin(BaseMixin):

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)
