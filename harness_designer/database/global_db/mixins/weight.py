# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


class WeightMixin(BaseMixin):

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)
        self._populate('weight')


class WeightControl(_prop_ctrls.FloatProperty):

    def __init__(self, parent):
        self.db_obj: WeightMixin = None

        super().__init__(parent, 'Weight', min_value=0.01, max_value=999.99, increment=0.01, units='g')

        self.property_changed.connect(self._on_weight)

    def set_obj(self, db_obj: WeightMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(0.0)
            self.Enable(False)
        else:
            self.SetValue(db_obj.weight)
            self.Enable(True)

    def _on_weight(self, evt: _prop_ctrls.PropertyEvent):
        weight = evt.GetValue()
        self.db_obj.weight = weight
