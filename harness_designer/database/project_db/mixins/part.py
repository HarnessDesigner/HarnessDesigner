from .base import BaseMixin

from wx import propgrid as wxpg


class PartMixin(BaseMixin):

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)

    @property
    def _part_propgrid(self) -> wxpg.PGProperty:
        return self.part.propgrid  # NOQA
