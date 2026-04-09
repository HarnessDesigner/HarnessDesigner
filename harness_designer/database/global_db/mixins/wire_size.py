from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class WireSizeMixin(BaseMixin):

    @property
    def min_dia(self) -> float | None:
        return self._table.select('min_dia', id=self._db_id)[0][0]

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)

    @property
    def max_dia(self) -> float | None:
        return self._table.select('max_dia', id=self._db_id)[0][0]

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, max_dia=value)

    @property
    def min_size_mm2(self) -> float | None:
        return self._table.select('min_size_mm2', id=self._db_id)[0][0]

    @min_size_mm2.setter
    def min_size_mm2(self, value: float):
        self._table.update(self._db_id, min_size_mm2=value)

    @property
    def max_size_mm2(self) -> float | None:
        return self._table.select('max_size_mm2', id=self._db_id)[0][0]

    @max_size_mm2.setter
    def max_size_mm2(self, value: float):
        self._table.update(self._db_id, max_size_mm2=value)

    @property
    def min_size_awg(self) -> int | None:
        return self._table.select('min_size_awg', id=self._db_id)[0][0]

    @min_size_awg.setter
    def min_size_awg(self, value: int):
        self._table.update(self._db_id, min_size_awg=value)

    @property
    def max_size_awg(self) -> int | None:
        return self._table.select('max_size_awg', id=self._db_id)[0][0]

    @max_size_awg.setter
    def max_size_awg(self, value: int):
        self._table.update(self._db_id, max_size_awg=value)

    @property
    def _wire_size_propgrid(self) -> _prop_grid.Property:

        group_prop = _prop_grid.Property('Wire Sizes', '')

        min_mm2_prop = _prop_grid.FloatProperty(
            'Minimum Cross', 'min_size_mm2', self.min_size_mm2, min_value=0.05,
            max_value=55.0, increment=0.01, units='mm²')

        max_mm2_prop = _prop_grid.FloatProperty(
            'Maximum Cross', 'max_size_mm2', self.max_size_mm2, min_value=0.05,
            max_value=55.0, increment=0.01, units='mm²')

        min_awg_prop = _prop_grid.IntProperty(
            'Minimum AWG', 'min_size_awg', self.min_size_awg,
            min_value=30, max_value=0, units='awg')

        max_awg_prop = _prop_grid.IntProperty(
            'Maximum AWG', 'max_size_awg', self.max_size_awg,
            min_value=30, max_value=0, units='awg')

        min_dia_prop = _prop_grid.FloatProperty(
            'Minimum Diameter', 'min_dia', self.min_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        max_dia_prop = _prop_grid.FloatProperty(
            'Maximum Diameter', 'max_dia', self.max_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        group_prop.Append(min_mm2_prop)
        group_prop.Append(max_mm2_prop)
        group_prop.Append(min_awg_prop)
        group_prop.Append(max_awg_prop)
        group_prop.Append(min_dia_prop)
        group_prop.Append(max_dia_prop)

        return group_prop
