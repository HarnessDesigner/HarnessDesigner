from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class WeightMixin(BaseMixin):

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)

    @property
    def _weight_propgrid(self) -> _prop_grid.Property:

        prop = _prop_grid.FloatProperty(
            'Weight', 'weight', self.weight, min_value=0.01,
            max_value=999.00, increment=0.01, units='g')

        return prop
