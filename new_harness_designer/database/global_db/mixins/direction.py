from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import direction as _direction  # NOQA


class DirectionMixin(BaseMixin):

    @property
    def direction(self) -> "_direction.Direction":
        from .. import direction as _direction  # NOQA

        direction_id = self._table.select('direction_id', id=self._db_id)
        return _direction.Direction(self._table.db.directions_table, direction_id[0][0])

    @direction.setter
    def direction(self, value: "_direction.Direction"):
        self._table.update(self._db_id, direction_id=value.db_id)

    @property
    def direction_id(self) -> int:
        return self._table.select('direction_id', id=self._db_id)[0][0]

    @direction_id.setter
    def direction_id(self, value: int):
        self._table.update(self._db_id, direction_id=value)


