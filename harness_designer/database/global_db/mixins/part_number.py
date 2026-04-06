from .base import BaseMixin

from wx import propgrid as wxpg


class PartNumberMixin(BaseMixin):

    @property
    def part_number(self) -> str:
        return self._table.select('part_number', id=self._db_id)[0][0]

    @property
    def _part_number_propgrid(self) -> wxpg.PGProperty:
        prop = wxpg.StringProperty('Part Number', 'part_number', self.part_number)

        return prop
