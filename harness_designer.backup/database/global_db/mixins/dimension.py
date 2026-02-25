from .base import BaseMixin


class DimensionMixin(BaseMixin):

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)

    @property
    def width(self) -> float:
        return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        self._table.update(self._db_id, width=value)

    @property
    def height(self) -> float:
        return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        self._table.update(self._db_id, height=value)

