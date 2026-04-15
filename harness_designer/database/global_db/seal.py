from typing import TYPE_CHECKING, Iterable as _Iterable

import uuid
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase
from ...geometry import point as _point

from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    ColorMixin, ColorControl,
    FamilyMixin, FamilyControl,
    SeriesMixin, SeriesControl,
    ResourceMixin, ResourcesControl,
    WeightMixin, WeightControl,
    TemperatureMixin, TemperatureControl,
    Model3DMixin,
    WireSizeMixin,
    DimensionMixin, DimensionControl,
    CompatHousingsMixin, CompatHousingsControl,
    CompatTerminalsMixin, CompatTerminalsControl

)

if TYPE_CHECKING:
    from . import seal_type as _seal_type


class SealsTable(TableBase):
    __table_name__ = 'seals'

    def _load_database(self, splash):
        from ..create_database import seals

        data_path = self._con.db_data.open(splash)
        seals.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import seals

        return seals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import seals

        seals.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        seals.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import seals

        seals.table.update_fields(self)

    def __iter__(self) -> _Iterable["Seal"]:
        for db_id in TableBase.__iter__(self):
            yield Seal(self, db_id)

    def __getitem__(self, item) -> "Seal":
        if isinstance(item, int):
            if item in self:
                return Seal(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Seal(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, series_id: int, type: str, hardness: int,  # NOQA
               color_id: int, lubricant: str, min_temp_id: int, max_temp_id: int, length: float, o_dia: float,
               i_dia: float, wire_dia_min: float, wire_dia_max: float, image_id: int, datasheet_id: int,
               cad_id: int, weight: float) -> "Seal":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 series_id=series_id, type=type, hardness=hardness, color_id=color_id,
                                 lubricant=lubricant, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 length=length, o_dia=o_dia, i_dia=i_dia, wire_dia_min=wire_dia_min,
                                 wire_dia_max=wire_dia_max, image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, weight=weight)
        return Seal(self, db_id)

    @property
    def search_items(self) -> dict:
        ret = {
            0: {
                'label': 'Part Number',
                'type': [str],
                'out_params': 'part_number'
            },
            1: {
                'label': 'Description',
                'type': [str],
                'out_params': 'description'
            },
            2: {
                'label': 'Manufacturer',
                'type': [int, str],
                'search_params': ['mfg_id', 'manufacturers', 'name']
            },
            3: {
                'label': 'Series',
                'type': [int, str],
                'search_params': ['series_id', 'series', 'name']
            },
            4: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            5: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            6: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            7: {
                'label': 'Type',
                'type': [int, str],
                'search_params': ['type_id', 'seal_types', 'name']
            },
            8: {
                'label': 'Hardness (shore)',
                'type': [int],
                'search_params': ['hardness']
            },
            9: {
                'label': 'Lubricant',
                'type': [str],
                'out_params': 'lubricant'
            },
            10: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            11: {
                'label': 'Diameter (OD)(mm)',
                'type': [float],
                'search_params': ['o_dia']
            },
            12: {
                'label': 'Diameter (ID)(mm)',
                'type': [float],
                'search_params': ['i_dia']
            },
            13: {
                'label': 'Wire Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['wire_dia_min']
            },
            14: {
                'label': 'Wire Diameter (Max)(mm)',
                'type': [float],
                'search_params': ['wire_dia_max']
            },
            15: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Seal(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
           SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin,
           Model3DMixin, DimensionMixin, FamilyMixin, WireSizeMixin, CompatHousingsMixin,
           CompatTerminalsMixin):

    _table: SealsTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'seals': [self.db_id],
            'series': [self.series_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        o_dia1, o_dia2, length = scale.as_float

        o_dia = max(o_dia1, o_dia2)
        self._table.update(self._db_id, o_dia=o_dia, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        is_sws = self.type.name.lower() in ('sws', 'single wire seal')
        if is_sws:
            x = y = self.o_dia
        else:
            x = self.width
            y = self.height

        z = self.length

        if x <= 0:
            if is_sws:
                self._table.update(self._db_id, o_dia=1.0)
                x = y = 1.0
            else:
                self._table.update(self._db_id, width=1.0)
                x = 1.0

        if y <= 0:
            if is_sws:
                self._table.update(self._db_id, o_dia=1.0)
                x = y = 1.0
            else:
                self._table.update(self._db_id, height=1.0)
                x = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def o_dia(self) -> float:
        return self._table.select('o_dia', id=self._db_id)[0][0]

    @o_dia.setter
    def o_dia(self, value: float):
        self._table.update(self._db_id, o_dia=round(value, 6))

    @property
    def i_dia(self) -> float:
        return self._table.select('i_dia', id=self._db_id)[0][0]

    @i_dia.setter
    def i_dia(self, value: float):
        self._table.update(self._db_id, i_dia=round(value, 6))

    @property
    def type(self) -> "_seal_type.SealType":
        type_id = self.type_id
        return self.table.db.seal_types_table[type_id]

    @property
    def type_id(self) -> int:
        return self._table.select('type_id', id=self._db_id)[0][0]

    @type_id.setter
    def type_id(self, value: int):
        self._table.update(self._db_id, type_id=value)

    @property
    def hardness(self) -> int:
        return self._table.select('hardness', id=self._db_id)[0][0]

    @hardness.setter
    def hardness(self, value: int):
        self._table.update(self.hardness, i_dia=value)

    @property
    def lubricant(self) -> str:
        return self._table.select('lubricant', id=self._db_id)[0][0]

    @lubricant.setter
    def lubricant(self, value: str):
        self._table.update(self._db_id, lubricant=value)

    @property
    def wire_dia_min(self) -> float:
        return self._table.select('wire_dia_min', id=self._db_id)[0][0]

    @wire_dia_min.setter
    def wire_dia_min(self, value: float):
        self._table.update(self._db_id, wire_dia_min=round(value, 6))

    @property
    def wire_dia_max(self) -> float:
        return self._table.select('wire_dia_max', id=self._db_id)[0][0]

    @wire_dia_max.setter
    def wire_dia_max(self, value: float):
        self._table.update(self._db_id, wire_dia_max=round(value, 6))


class SealControl(wx.Notebook):

    # TODO: Add seal type and wire sizes

    def set_obj(self, db_obj: Seal):
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.dimension_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)

        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.weight_ctrl.set_obj(db_obj)
        self.compat_housing_ctrl.set_obj(db_obj)
        self.compat_terminals_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.hardness_ctrl.SetValue(0)
            self.lubricant_ctrl.SetValue('')
            self.o_dia_ctrl.SetValue(0.0)
            self.i_dia_ctrl.SetValue(0.0)

            self.hardness_ctrl.Enable(False)
            self.lubricant_ctrl.Enable(False)
            self.o_dia_ctrl.Enable(False)
            self.i_dia_ctrl.Enable(False)
        else:
            self.hardness_ctrl.SetValue(db_obj.hardness)
            self.lubricant_ctrl.SetValue(db_obj.lubricant)
            self.o_dia_ctrl.SetValue(db_obj.o_dia)
            self.i_dia_ctrl.SetValue(db_obj.i_dia)

            self.hardness_ctrl.Enable(True)
            self.lubricant_ctrl.Enable(True)
            self.o_dia_ctrl.Enable(True)
            self.i_dia_ctrl.Enable(True)

    def _on_hardness(self, evt):
        value = evt.GetValue()
        self.db_obj.hardness = value

    def _on_lubricant(self, evt):
        value = evt.GetValue()
        self.db_obj.lubricant = value

    def _on_o_dia(self, evt):
        value = evt.GetValue()
        self.db_obj.o_dia = value

    def _on_i_dia(self, evt):
        value = evt.GetValue()
        self.db_obj.i_dia = value

    def __init__(self, parent):
        self.db_obj: Seal = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)
        self.color_ctrl = ColorControl(general_page)

        self.hardness_ctrl = _prop_grid.IntProperty(
            general_page, 'Hardness', -1, min_value=-1, max_value=999, units='shore')

        self.lubricant_ctrl = _prop_grid.StringProperty(general_page, 'Lubricant', '')

        self.o_dia_ctrl = _prop_grid.FloatProperty(
            general_page, 'Outside Diameter', 0.0, min_value=0.0,
            max_value=99.9, increment=0.01, units='mm')

        self.i_dia_ctrl = _prop_grid.FloatProperty(
            general_page, 'Inside Diameter', 0.0, min_value=0.00,
            max_value=99.9, increment=0.01, units='mm')

        self.hardness_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_hardness)
        self.lubricant_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_lubricant)
        self.o_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_o_dia)
        self.i_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_i_dia)

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.dimension_page = DimensionControl(self)
        self.weight_ctrl = WeightControl(self.dimension_page)

        self.resources_page = ResourcesControl(self)

        compat_parts_page = _prop_grid.Category(self, 'Compatible Parts')
        self.compat_housing_ctrl = CompatHousingsControl(compat_parts_page)
        self.compat_terminals_ctrl = CompatTerminalsControl(compat_parts_page)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.dimension_page,
            self.resources_page,
            compat_parts_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
