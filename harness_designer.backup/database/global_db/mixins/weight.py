from .base import BaseMixin

from ....wrappers.decimal import Decimal as _decimal


class WeightMixin(BaseMixin):

    @property
    def weight(self) -> _decimal:
        return _decimal(self._table.select('weight', id=self._db_id)[0][0])

    @weight.setter
    def weight(self, value: _decimal):
        self._table.update(self._db_id, weight=float(value))
