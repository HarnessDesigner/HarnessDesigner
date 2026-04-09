from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class PartNumberMixin(BaseMixin):

    @property
    def part_number(self) -> str:
        return self._table.select('part_number', id=self._db_id)[0][0]

    @property
    def _part_number_propgrid(self) -> _prop_grid.Property:
        prop = _prop_grid.StringProperty('Part Number', 'part_number', self.part_number)

        return prop
