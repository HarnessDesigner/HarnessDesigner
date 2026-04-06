from .base import BaseMixin

from wx import propgrid as wxpg


class WeightMixin(BaseMixin):

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)

    @property
    def _weight_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import float_prop as _float_prop

        prop = _float_prop.FloatProperty(
            'Weight', 'weight', self.weight, min_value=0.01,
            max_value=999.00, increment=0.01, units='g')

        return prop
