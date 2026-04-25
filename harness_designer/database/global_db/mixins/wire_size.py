from .base import BaseMixin

from .... import utils as _utils
from ....ui.editor_obj import prop_grid as _prop_grid


class WireSizeMixin(BaseMixin):

    @property
    def min_dia(self) -> float | None:
        return self._table.select('min_dia', id=self._db_id)[0][0]

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)
        self._populate('min_dia')

    @property
    def max_dia(self) -> float | None:
        return self._table.select('max_dia', id=self._db_id)[0][0]

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, max_dia=value)
        self._populate('max_dia')

    @property
    def min_size_mm2(self) -> float | None:
        return self._table.select('min_size_mm2', id=self._db_id)[0][0]

    @min_size_mm2.setter
    def min_size_mm2(self, value: float):
        self._table.update(self._db_id, min_size_mm2=value)
        self._populate('min_size_mm2')

    @property
    def max_size_mm2(self) -> float | None:
        return self._table.select('max_size_mm2', id=self._db_id)[0][0]

    @max_size_mm2.setter
    def max_size_mm2(self, value: float):
        self._table.update(self._db_id, max_size_mm2=value)
        self._populate('max_size_mm2')

    @property
    def min_size_awg(self) -> int | None:
        return self._table.select('min_size_awg', id=self._db_id)[0][0]

    @min_size_awg.setter
    def min_size_awg(self, value: int):
        self._table.update(self._db_id, min_size_awg=value)
        self._populate('min_size_awg')

    @property
    def max_size_awg(self) -> int | None:
        return self._table.select('max_size_awg', id=self._db_id)[0][0]

    @max_size_awg.setter
    def max_size_awg(self, value: int):
        self._table.update(self._db_id, max_size_awg=value)
        self._populate('max_size_awg')


class WireSizeControl(_prop_grid.Category):

    def set_obj(self, db_obj: WireSizeMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.min_dia_ctrl.SetValue(0.26)
            self.max_dia_ctrl.SetValue(0.26)

            self.min_awg_ctrl.SetValue(30)
            self.max_awg_ctrl.SetValue(30)

            self.min_mm2_ctrl.SetValue(0.05)
            self.max_mm2_ctrl.SetValue(0.05)

            self.min_dia_ctrl.Enable(False)
            self.max_dia_ctrl.Enable(False)

            self.min_awg_ctrl.Enable(False)
            self.max_awg_ctrl.Enable(False)

            self.min_mm2_ctrl.Enable(False)
            self.max_mm2_ctrl.Enable(False)
        else:
            self.min_dia_ctrl.SetValue(db_obj.min_dia)
            self.max_dia_ctrl.SetValue(db_obj.max_dia)

            self.min_awg_ctrl.SetValue(db_obj.min_size_awg)
            self.max_awg_ctrl.SetValue(db_obj.max_size_awg)

            self.min_mm2_ctrl.SetValue(db_obj.min_size_mm2)
            self.max_mm2_ctrl.SetValue(db_obj.max_size_mm2)

            self.min_dia_ctrl.Enable(True)
            self.max_dia_ctrl.Enable(True)

            self.min_awg_ctrl.Enable(True)
            self.max_awg_ctrl.Enable(True)

            self.min_mm2_ctrl.Enable(True)
            self.max_mm2_ctrl.Enable(True)

    def _on_min_mm2(self, evt):
        mm2 = evt.GetValue()
        awg = _utils.mm2_to_awg(mm2)
        dia = _utils.mm2_to_d_mm(mm2)

        self.db_obj.min_size_mm2 = mm2
        self.db_obj.min_size_awg = awg
        self.db_obj.min_dia = dia

    def _on_max_mm2(self, evt):
        mm2 = evt.GetValue()
        awg = _utils.mm2_to_awg(mm2)
        dia = _utils.mm2_to_d_mm(mm2)

        self.db_obj.max_size_mm2 = mm2
        self.db_obj.max_size_awg = awg
        self.db_obj.max_dia = dia

    def _on_min_awg(self, evt):
        awg = evt.GetValue()
        mm2 = _utils.awg_to_mm2(awg)
        dia = _utils.awg_to_d_mm(awg)

        self.db_obj.min_size_awg = awg
        self.db_obj.min_size_mm2 = mm2
        self.db_obj.min_dia = dia

    def _on_max_awg(self, evt):
        awg = evt.GetValue()
        mm2 = _utils.awg_to_mm2(awg)
        dia = _utils.awg_to_d_mm(awg)

        self.db_obj.max_size_awg = awg
        self.db_obj.max_size_mm2 = mm2
        self.db_obj.max_dia = dia

    def _on_min_dia(self, evt):
        dia = evt.GetValue()
        mm2 = _utils.d_mm_to_mm2(dia)
        awg = _utils.d_mm_to_awg(dia)

        self.db_obj.min_dia = dia
        self.db_obj.min_size_mm2 = mm2
        self.db_obj.min_size_awg = awg

    def _on_max_dia(self, evt):
        dia = evt.GetValue()
        mm2 = _utils.d_mm_to_mm2(dia)
        awg = _utils.d_mm_to_awg(dia)

        self.db_obj.max_dia = dia
        self.db_obj.max_size_mm2 = mm2
        self.db_obj.max_size_awg = awg

    def __init__(self, parent):
        self.db_obj: WireSizeMixin = None

        super().__init__(parent, 'Wire Sizes')

        self.min_mm2_ctrl = _prop_grid.FloatProperty(
            self, 'Minimum Cross', min_value=0.05, max_value=55.0, increment=0.01, units='mm²')

        self.max_mm2_ctrl = _prop_grid.FloatProperty(
            self, 'Maximum Cross', min_value=0.05, max_value=55.0, increment=0.01, units='mm²')

        self.min_awg_ctrl = _prop_grid.IntProperty(
            self, 'Minimum AWG', min_value=0, max_value=30, units='awg')

        self.max_awg_ctrl = _prop_grid.IntProperty(
            self, 'Maximum AWG', min_value=0, max_value=30, units='awg')

        self.min_dia_ctrl = _prop_grid.FloatProperty(
            self, 'Minimum Diameter', min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        self.max_dia_ctrl = _prop_grid.FloatProperty(
            self, 'Maximum Diameter', min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        self.min_mm2_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_mm2)
        self.max_mm2_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_mm2)

        self.min_awg_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_awg)
        self.max_awg_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_awg)

        self.min_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_dia)
        self.max_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_dia)
