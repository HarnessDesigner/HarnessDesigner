from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class PartMixin(BaseMixin):

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)

    @property
    def _part_propgrid(self) -> _prop_grid.Property:
        return self.part.propgrid  # NOQA
