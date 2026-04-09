
from ....ui.editor_obj import prop_grid as _prop_grid
from .base import BaseMixin


class Visible2DMixin(BaseMixin):

    @property
    def is_visible2d(self) -> bool:
        return bool(self._table.select('is_visible2d', id=self._db_id)[0][0])

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        self._table.update(self._db_id, is_visible2d=int(value))

    @property
    def _visible2d_propgrid(self) -> _prop_grid.Property:

        visible_prop = _prop_grid.BoolProperty('Visible 2D', 'is_visible2d', self.is_visible2d)

        return visible_prop
