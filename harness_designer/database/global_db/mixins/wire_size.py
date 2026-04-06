from .base import BaseMixin

from wx import propgrid as wxpg


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
    def _wire_size_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import float_prop as _float_prop
        from ....ui.editor_obj.prop_grid import int_prop as _int_prop

        group_prop = wxpg.PGProperty('Wire Sizes', '')

        min_mm2_prop = _float_prop.FloatProperty(
            'Minimum Cross', 'min_size_mm2', self.min_size_mm2, min_value=0.05,
            max_value=55.0, increment=0.01, units='mm²')

        max_mm2_prop = _float_prop.FloatProperty(
            'Maximum Cross', 'max_size_mm2', self.max_size_mm2, min_value=0.05,
            max_value=55.0, increment=0.01, units='mm²')

        min_awg_prop = _int_prop.IntProperty(
            'Minimum AWG', 'min_size_awg', self.min_size_awg,
            min_value=30, max_value=0, units='awg')

        max_awg_prop = _int_prop.IntProperty(
            'Maximum AWG', 'max_size_awg', self.max_size_awg,
            min_value=30, max_value=0, units='awg')

        min_dia_prop = _float_prop.FloatProperty(
            'Minimum Diameter', 'min_dia', self.min_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        max_dia_prop = _float_prop.FloatProperty(
            'Maximum Diameter', 'max_dia', self.max_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        group_prop.AppendChild(min_mm2_prop)
        group_prop.AppendChild(max_mm2_prop)
        group_prop.AppendChild(min_awg_prop)
        group_prop.AppendChild(max_awg_prop)
        group_prop.AppendChild(min_dia_prop)
        group_prop.AppendChild(max_dia_prop)

        return group_prop
