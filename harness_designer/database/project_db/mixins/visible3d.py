from .base import BaseMixin


class Visible3DMixin(BaseMixin):

    @property
    def is_visible3d(self) -> bool:
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        self._table.update(self._db_id, is_visible3d=int(value))
