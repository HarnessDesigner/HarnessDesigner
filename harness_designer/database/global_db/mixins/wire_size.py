# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin

from .... import utils as _utils
from ....ui import prop_ctrls as _prop_ctrls


class WireSizeMixin(BaseMixin):

    @property
    def wire_size_dia_min(self) -> float | None:
        return self._table.select('wire_size_dia_min', id=self._db_id)[0][0]

    @wire_size_dia_min.setter
    def wire_size_dia_min(self, value: float):
        self._table.update(self._db_id, wire_size_dia_min=value)
        self._table.update(self._db_id, wire_size_cross_min=_utils.d_mm_to_mm2(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.d_mm_to_awg(value))
        self._populate('wire_size_dia_min')

    @property
    def wire_size_dia_max(self) -> float | None:
        return self._table.select('wire_size_dia_max', id=self._db_id)[0][0]

    @wire_size_dia_max.setter
    def wire_size_dia_max(self, value: float):
        self._table.update(self._db_id, wire_size_dia_max=value)
        self._table.update(self._db_id, wire_size_cross_min=_utils.d_mm_to_mm2(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.d_mm_to_awg(value))
        self._populate('wire_size_dia_max')

    @property
    def wire_size_cross_min(self) -> float | None:
        return self._table.select('wire_size_cross_min', id=self._db_id)[0][0]

    @wire_size_cross_min.setter
    def wire_size_cross_min(self, value: float):
        self._table.update(self._db_id, wire_size_cross_min=value)
        self._table.update(self._db_id, wire_size_dia_min=_utils.mm2_to_d_mm(value))
        self._table.update(self._db_id, wire_size_awg_min=_utils.mm2_to_awg(value))
        self._populate('wire_size_cross_min')

    @property
    def wire_size_cross_max(self) -> float | None:
        return self._table.select('wire_size_cross_max', id=self._db_id)[0][0]

    @wire_size_cross_max.setter
    def wire_size_cross_max(self, value: float):
        self._table.update(self._db_id, wire_size_cross_max=value)
        self._table.update(self._db_id, wire_size_dia_max=_utils.mm2_to_d_mm(value))
        self._table.update(self._db_id, wire_size_awg_max=_utils.mm2_to_awg(value))
        self._populate('wire_size_cross_max')

    @property
    def wire_size_awg_min(self) -> int | None:
        return self._table.select('wire_size_awg_min', id=self._db_id)[0][0]

    @wire_size_awg_min.setter
    def wire_size_awg_min(self, value: int):
        self._table.update(self._db_id, wire_size_awg_min=value)
        self._table.update(self._db_id, wire_size_dia_min=_utils.awg_to_d_mm(value))
        self._table.update(self._db_id, wire_size_cross_min=_utils.awg_to_mm2(value))
        self._populate('wire_size_awg_min')

    @property
    def wire_size_awg_max(self) -> int | None:
        return self._table.select('wire_size_awg_max', id=self._db_id)[0][0]

    @wire_size_awg_max.setter
    def wire_size_awg_max(self, value: int):
        self._table.update(self._db_id, wire_size_awg_max=value)
        self._table.update(self._db_id, wire_size_dia_max=_utils.awg_to_d_mm(value))
        self._table.update(self._db_id, wire_size_cross_max=_utils.awg_to_mm2(value))
        self._populate('wire_size_awg_max')


class WireSizeControl(_prop_ctrls.Category):

    def set_obj(self, db_obj: WireSizeMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.min_dia_ctrl.SetValue(0.254)
            self.max_dia_ctrl.SetValue(0.254)

            self.min_awg_ctrl.SetValue(30)
            self.max_awg_ctrl.SetValue(30)

            self.min_mm2_ctrl.SetValue(0.0507)
            self.max_mm2_ctrl.SetValue(0.0507)

            self.min_dia_ctrl.Enable(False)
            self.max_dia_ctrl.Enable(False)

            self.min_awg_ctrl.Enable(False)
            self.max_awg_ctrl.Enable(False)

            self.min_mm2_ctrl.Enable(False)
            self.max_mm2_ctrl.Enable(False)
        else:
            self.min_dia_ctrl.SetValue(db_obj.wire_size_dia_min)
            self.max_dia_ctrl.SetValue(db_obj.wire_size_dia_max)

            self.min_awg_ctrl.SetValue(db_obj.wire_size_awg_min)
            self.max_awg_ctrl.SetValue(db_obj.wire_size_awg_max)

            self.min_mm2_ctrl.SetValue(db_obj.wire_size_cross_min)
            self.max_mm2_ctrl.SetValue(db_obj.wire_size_cross_max)

            self.min_dia_ctrl.Enable(True)
            self.max_dia_ctrl.Enable(True)

            self.min_awg_ctrl.Enable(True)
            self.max_awg_ctrl.Enable(True)

            self.min_mm2_ctrl.Enable(True)
            self.max_mm2_ctrl.Enable(True)

    def _on_min_mm2(self, evt):
        mm2 = evt.GetValue()

        self.db_obj.wire_size_cross_min = mm2
        self.min_awg_ctrl.SetValue(self.db_obj.wire_size_awg_min)
        self.min_dia_ctrl.SetValue(self.db_obj.wire_size_dia_min)

    def _on_max_mm2(self, evt):
        mm2 = evt.GetValue()

        self.db_obj.wire_size_cross_max = mm2
        self.max_awg_ctrl.SetValue(self.db_obj.wire_size_awg_max)
        self.max_dia_ctrl.SetValue(self.db_obj.wire_size_dia_max)

    def _on_min_awg(self, evt):
        awg = evt.GetValue()

        self.db_obj.wire_size_awg_min = awg
        self.min_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_min)
        self.min_dia_ctrl.SetValue(self.db_obj.wire_size_dia_min)

    def _on_max_awg(self, evt):
        awg = evt.GetValue()
        
        self.db_obj.wire_size_awg_max = awg

        self.max_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_max)
        self.max_dia_ctrl.SetValue(self.db_obj.wire_size_dia_max)       

    def _on_min_dia(self, evt):
        dia = evt.GetValue()

        self.db_obj.wire_size_dia_min = dia
        self.min_awg_ctrl.SetValue(self.db_obj.wire_size_awg_min)
        self.min_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_min)

    def _on_max_dia(self, evt):
        dia = evt.GetValue()

        self.db_obj.wire_size_dia_max = dia
        self.max_awg_ctrl.SetValue(self.db_obj.wire_size_awg_max)
        self.max_mm2_ctrl.SetValue(self.db_obj.wire_size_cross_max)
    
    def __init__(self, parent):
        self.db_obj: WireSizeMixin = None

        super().__init__(parent, 'Wire Sizes')

        self.min_mm2_ctrl = _prop_ctrls.FloatProperty(
            self, 'Minimum Cross', min_value=0.0507, max_value=135.1755, increment=0.0001, units='mm²')

        self.max_mm2_ctrl = _prop_ctrls.FloatProperty(
            self, 'Maximum Cross', min_value=0.0507, max_value=135.1755, increment=0.0001, units='mm²')

        self.min_awg_ctrl = _prop_ctrls.IntProperty(
            self, 'Minimum AWG', min_value=-4, max_value=30, units='awg')

        self.max_awg_ctrl = _prop_ctrls.IntProperty(
            self, 'Maximum AWG', min_value=-4, max_value=30, units='awg')

        self.min_dia_ctrl = _prop_ctrls.FloatProperty(
            self, 'Minimum Diameter', min_value=0.254, max_value=13.1191, increment=0.0001, units='mm')

        self.max_dia_ctrl = _prop_ctrls.FloatProperty(
            self, 'Maximum Diameter', min_value=0.254, max_value=13.1191, increment=0.0001, units='mm')

        self.min_mm2_ctrl.property_changed.connect(self._on_min_mm2)
        self.max_mm2_ctrl.property_changed.connect(self._on_max_mm2)

        self.min_awg_ctrl.property_changed.connect(self._on_min_awg)
        self.max_awg_ctrl.property_changed.connect(self._on_max_awg)

        self.min_dia_ctrl.property_changed.connect(self._on_min_dia)
        self.max_dia_ctrl.property_changed.connect(self._on_max_dia)
