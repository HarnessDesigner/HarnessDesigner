from typing import Iterable as _Iterable, TYPE_CHECKING

import wx

from ... import utils as _utils
from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase

from .mixins import (
    PartNumberMixin, PartNumberControl,
    ManufacturerMixin, ManufacturerControl,
    DescriptionMixin, DescriptionControl,
    SeriesMixin, SeriesControl,
    ResourceMixin, ResourcesControl,
    ColorMixin, ColorControl,
    FamilyMixin, FamilyControl,
    MaterialMixin, MaterialControl,
    TemperatureMixin, TemperatureControl,
    PlatingControl
)


if TYPE_CHECKING:
    from . import color as _color
    from . import plating as _plating


class WiresTable(TableBase):
    __table_name__: str = 'wires'

    def _load_database(self, splash):
        from ..create_database import wires

        data_path = self._con.db_data.open(splash)
        wires.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import wires

        return wires.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import wires

        wires.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        wires.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import wires

        wires.table.update_fields(self)

    def __iter__(self) -> _Iterable["Wire"]:

        for db_id in TableBase.__iter__(self):
            yield Wire(self, db_id)

    def __getitem__(self, item) -> "Wire":
        if isinstance(item, int):
            if item in self:
                return Wire(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Wire(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int, series_id: int,
               image_id: int, datasheet_id: int, cad_id: int, color_id: int, addl_color_ids: list,
               material_id: int, num_conductors: int, shielded: bool, tpi: int, conductor_dia_mm: float,
               size_mm2: float, size_awg: int, od_mm: float, max_temp_id: int, weight: float) -> "Wire":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, color_id=color_id,
                                 addl_color_ids=str(addl_color_ids), material_id=material_id,
                                 num_conductors=num_conductors, shielded=int(shielded), tpi=tpi,
                                 conductor_dia_mm=conductor_dia_mm, size_mm2=size_mm2, size_awg=size_awg,
                                 od_mm=od_mm, max_temp_id=max_temp_id, weight=weight)

        return Wire(self, db_id)

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
                'label': 'Family',
                'type': [int, str],
                'search_params': ['family_id', 'families', 'name']
            },
            4: {
                'label': 'Series',
                'type': [int, str],
                'search_params': ['series_id', 'series', 'name']
            },
            5: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            6: {
                'label': 'Stripe Color',
                'type': [int, str],
                'search_params': ['stripe_color_id', 'colors', 'name']
            },
            7: {
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            8: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            9: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            10: {
                'label': 'Conductors',
                'type': [int],
                'search_params': ['num_conductors']
            },
            11: {
                'label': 'Shielded',
                'type': [bool],
                'search_params': ['shielded']
            },
            12: {
                'label': 'TPI',
                'type': [float],
                'search_params': ['tpi']
            },
            13: {
                'label': 'Conductor Diameter (mm)',
                'type': [float],
                'out_params': 'conductor_dia_mm'
            },
            14: {
                'label': 'Size (AWG)',
                'type': [int],
                'search_params': ['size_awg']
            },
            15: {
                'label': 'Size (mm2)',
                'type': [float],
                'search_params': ['size_mm2']
            },
            16: {
                'label': 'Diameter (OD)(mm)',
                'type': [float],
                'search_params': ['od_mm']
            },
            17: {
                'label': 'Core Material',
                'type': [int, str],
                'search_params': ['core_material_id', 'platings', 'symbol']
            },
            18: {
                'label': 'Volts',
                'type': [float],
                'search_params': ['volts']
            },
            19: {
                'label': 'Weight (1km)(g)',
                'type': [float],
                'search_params': ['weight_1km']
            }
        }

        return ret


class Wire(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
           FamilyMixin, SeriesMixin, ResourceMixin, ColorMixin, MaterialMixin,
           TemperatureMixin):

    _table: WiresTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'wires': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'materials': [self.material_id],
            'platings': [self.core_material_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id]
        }

        stripe_color_id = self.stripe_color_id
        if stripe_color_id is not None:
            packet['colors'].append(stripe_color_id)

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def resistance_1km(self) -> float:
        resistance = self._table.select('resistance_1km', id=self._db_id)[0][0]
        return resistance

    @resistance_1km.setter
    def resistance_1km(self, value: float):
        self._table.update(self._db_id, resistance_1km=value)
        self._populate('resistance_1km')

    @property
    def resistance_1kft(self) -> float:
        return self.resistance_ft * 1000

    @resistance_1kft.setter
    def resistance_1kft(self, value: float):
        self.resistance_ft = value / 1000

    @property
    def resistance_m(self) -> float:
        resistance = self.resistance_1km
        return resistance / 1000

    @resistance_m.setter
    def resistance_m(self, value: float):
        value *= 1000
        self.resistance_1km = value

    @property
    def resistance_ft(self) -> float:
        resistance = self.resistance_m
        return resistance * 3.28084

    @resistance_ft.setter
    def resistance_ft(self, value: float):
        value /= 3.28084
        self.resistance_m = value

    @property
    def weight_1km(self) -> float:
        weight = self._table.select('weight_1km', id=self._db_id)[0][0]
        return weight

    @weight_1km.setter
    def weight_1km(self, value: float):
        self._table.update(self._db_id, weight_1km=value)
        self._populate('weight_1km')

    @property
    def weight_1kft(self) -> float:
        return self.weight_lb_ft * 1000

    @weight_1kft.setter
    def weight_1kft(self, value: float):
        self.weight_lb_ft = value / 1000

    @property
    def weight_g_m(self) -> float:
        weight = self.weight_1km
        return weight / 1000

    @weight_g_m.setter
    def weight_g_m(self, value: float):
        value *= 1000
        self.weight_1km = value

    @property
    def weight_g_ft(self) -> float:
        weight = self.weight_g_m
        return weight * 3.28084

    @weight_g_ft.setter
    def weight_g_ft(self, value: float):
        value /= 3.28084
        self.weight_g_m = value

    @property
    def weight_lb_ft(self) -> float:
        weight = self.weight_g_ft
        return weight / 453.592

    @weight_lb_ft.setter
    def weight_lb_ft(self, value: float):
        value *= 453.592
        self.weight_g_ft = value

    @property
    def volts(self) -> float:
        return self._table.select('volts', id=self._db_id)[0][0]

    @volts.setter
    def volts(self, value: float):
        self._table.update(self._db_id, volts=value)
        self._populate('volts')

    @property
    def od_mm(self) -> float:
        return self._table.select('od_mm', id=self._db_id)[0][0]

    @od_mm.setter
    def od_mm(self, value: float):
        self._table.update(self._db_id, od_mm=value)
        self._populate('od_mm')

    @property
    def shielded(self) -> bool:
        return bool(self._table.select('shielded', id=self._db_id)[0][0])

    @shielded.setter
    def shielded(self, value: bool):
        self._table.update(self._db_id, shielded=int(value))
        self._populate('shielded')

    @property
    def tpi(self) -> int:
        return self._table.select('tpi', id=self._db_id)[0][0]

    @tpi.setter
    def tpi(self, value: int):
        self._table.update(self._db_id, tpi=value)
        self._populate('tpi')

    @property
    def num_conductors(self) -> int:
        return self._table.select('num_conductors', id=self._db_id)[0][0]

    @num_conductors.setter
    def num_conductors(self, value: int):
        self._table.update(self._db_id, num_conductors=value)
        self._populate('num_conductors')

    @property
    def core_material(self) -> "_plating.Plating":
        db_id = self.core_material_id
        return self._table.db.platings_table[db_id]

    @property
    def core_material_id(self) -> int:
        return self._table.select('core_material_id', id=self._db_id)[0][0]

    @core_material_id.setter
    def core_material_id(self, value: int):
        self._table.update(self._db_id, core_material_id=value)
        self._populate('core_material_id')

    @property
    def conductor_dia_mm(self) -> float:
        mm = self._table.select('conductor_dia_mm', id=self._db_id)[0][0]

        if mm is None:
            _utils.d_in_to_d_mm(self.conductor_dia_in)

        return mm

    @conductor_dia_mm.setter
    def conductor_dia_mm(self, value: float):
        self._table.update(self._db_id, conductor_dia_mm=value)
        self._populate('conductor_dia_mm')

    @property
    def conductor_dia_in(self) -> float:
        return _utils.awg_to_d_in(self.size_awg)

    @conductor_dia_in.setter
    def conductor_dia_in(self, value: float):
        self.conductor_dia_mm = value * 25.4

    @property
    def size_mm2(self) -> float:
        mm2 = self._table.select('size_mm2', id=self._db_id)[0][0]

        if mm2 is None:
            awg = self.size_awg

            if awg is None:
                mm = self.conductor_dia_mm

                if mm is None:
                    raise RuntimeError('sanity check')

                return _utils.d_mm_to_mm2(mm)

            return _utils.awg_to_mm2(awg)

        return mm2

    @size_mm2.setter
    def size_mm2(self, value: float):
        self._table.update(self._db_id, size_mm2=value)
        self._populate('size_mm2')

    @property
    def size_awg(self) -> int:
        awg = self._table.select('size_awg', id=self._db_id)[0][0]

        if awg is None:
            mm2 = self.size_mm2

            if mm2 is None:
                mm = self.conductor_dia_mm

                if mm is None:
                    raise RuntimeError('sanity check')

                return _utils.d_mm_to_awg(mm)

            return _utils.mm2_to_awg(mm2)

        return awg

    @size_awg.setter
    def size_awg(self, value: int):
        self._table.update(self._db_id, size_awg=value)
        self._populate('size_awg')

    @property
    def size_in2(self) -> float:
        return _utils.mm2_to_in2(self.size_mm2)

    @size_in2.setter
    def size_in2(self, value: float):
        self.size_mm2 = _utils.in2_to_mm2(value)

    @property
    def in2_symbol(self) -> str:
        return 'in²'

    @property
    def mm2_symbol(self) -> str:
        return 'mm²'

    @property
    def stripe_color(self) -> "_color.Color":
        db_id = self.stripe_color_id
        return self._table.db.colors_table[db_id]

    @property
    def stripe_color_id(self) -> int | None:
        return self._table.select('stripe_color_id', id=self._db_id)[0][0]

    @stripe_color_id.setter
    def stripe_color_id(self, value: int | None):
        self._table.update(self._db_id, stripe_color_id=value)
        self._populate('stripe_color_id')


class WireControl(wx.Notebook):

    def set_obj(self, db_obj: Wire):
        self.db_obj = db_obj

        self.mfg_page.set_obj(db_obj)
        self.family_page.set_obj(db_obj)
        self.series_page.set_obj(db_obj)
        self.temperature_page.set_obj(db_obj)
        self.resources_page.set_obj(db_obj)
        self.part_number_ctrl.set_obj(db_obj)
        self.description_ctrl.set_obj(db_obj)
        self.color_ctrl.set_obj(db_obj)
        self.stripe_color_ctrl.set_obj(db_obj)
        self.material_ctrl.set_obj(db_obj)
        self.core_material_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.tpi_ctrl.SetValue(0.0)
            self.weight_1km_ctrl.SetValue(0.0)
            self.volts_ctrl.SetValue(0.0)
            self.resistance_1km_ctrl.SetValue(0.0)
            self.num_conductors_ctrl.SetValue(1)
            self.shielded_ctrl.SetValue(False)
            self.conductor_dia_mm_ctrl.SetValue(0.05)
            self.size_mm2_ctrl.SetValue(0.05)
            self.size_awg_ctrl.SetValue(30.0)
            self.od_mm_ctrl.SetValue(0.05)

            self.tpi_ctrl.Enable(False)
            self.weight_1km_ctrl.Enable(False)
            self.volts_ctrl.Enable(False)
            self.resistance_1km_ctrl.Enable(False)
            self.num_conductors_ctrl.Enable(False)
            self.shielded_ctrl.Enable(False)
            self.conductor_dia_mm_ctrl.Enable(False)
            self.size_mm2_ctrl.Enable(False)
            self.size_awg_ctrl.Enable(False)
            self.od_mm_ctrl.Enable(False)

        else:
            self.tpi_ctrl.SetValue(db_obj.tpi)
            self.weight_1km_ctrl.SetValue(db_obj.weight_1km)
            self.volts_ctrl.SetValue(db_obj.volts)
            self.resistance_1km_ctrl.SetValue(db_obj.resistance_1km)
            self.num_conductors_ctrl.SetValue(db_obj.num_conductors)
            self.shielded_ctrl.SetValue(db_obj.shielded)
            self.conductor_dia_mm_ctrl.SetValue(db_obj.conductor_dia_mm)
            self.size_mm2_ctrl.SetValue(db_obj.size_mm2)
            self.size_awg_ctrl.SetValue(db_obj.size_awg)
            self.od_mm_ctrl.SetValue(db_obj.od_mm)

            self.tpi_ctrl.Enable(True)
            self.weight_1km_ctrl.Enable(True)
            self.volts_ctrl.Enable(True)
            self.resistance_1km_ctrl.Enable(True)
            self.num_conductors_ctrl.Enable(True)
            self.shielded_ctrl.Enable(True)
            self.conductor_dia_mm_ctrl.Enable(True)
            self.size_mm2_ctrl.Enable(True)
            self.size_awg_ctrl.Enable(True)
            self.od_mm_ctrl.Enable(True)

    def _on_tpi(self, evt):
        value = evt.GetValue()
        self.db_obj.tpi = value

    def _on_weight_1km(self, evt):
        value = evt.GetValue()
        self.db_obj.weight_1km = value

    def _on_volts(self, evt):
        value = evt.GetValue()
        self.db_obj.volts = value

    def _on_resistance_1km(self, evt):
        value = evt.GetValue()
        self.db_obj.resistance_1km = value

    def _on_num_conductors(self, evt):
        value = evt.GetValue()
        self.db_obj.num_conductors = value

    def _on_shielded(self, evt):
        value = evt.GetValue()
        self.db_obj.shielded = value

    def _on_conductor_dia_mm(self, evt):
        value = evt.GetValue()
        self.db_obj.conductor_dia_mm = value

    def _on_size_mm2(self, evt):
        value = evt.GetValue()
        self.db_obj.size_mm2 = value

    def _on_size_awg(self, evt):
        value = evt.GetValue()
        self.db_obj.size_awg = value

    def _on_od_mm(self, evt):
        value = evt.GetValue()
        self.db_obj.od_mm = value

    def __init__(self, parent):
        self.db_obj: Wire = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.part_number_ctrl = PartNumberControl(general_page)
        self.description_ctrl = DescriptionControl(general_page)

        self.tpi_ctrl = _prop_grid.FloatProperty(
            general_page, 'Twists per Inch',
            min_value=0.00, max_value=5.0, increment=0.5, units='tpi')

        self.weight_1km_ctrl = _prop_grid.FloatProperty(
            general_page, 'Weight',
            min_value=0.0, max_value=500.0, increment=0.01, units='g/km')

        self.volts_ctrl = _prop_grid.FloatProperty(
            general_page, 'Volts',
            min_value=0.00, max_value=44000.00, increment=0.1, units='V')

        self.resistance_1km_ctrl = _prop_grid.FloatProperty(
            general_page, 'Resistance',
            min_value=0.0, max_value=99999.99, increment=0.01, units='Ω/km')

        self.num_conductors_ctrl = _prop_grid.IntProperty(
            general_page, 'Conductor Count', min_value=1, max_value=10)

        self.shielded_ctrl = _prop_grid.BoolProperty(
            general_page, 'Shielded')

        color_page = _prop_grid.Category(self, 'Color')
        self.color_ctrl = ColorControl(color_page)
        self.color_ctrl.SetLabel('Primary')

        self.stripe_color_ctrl = ColorControl(color_page)
        self.stripe_color_ctrl.SetLabel('Stripe')
        self.stripe_color_ctrl.SetAttributeName('stripe_color')

        self.mfg_page = ManufacturerControl(self)
        self.family_page = FamilyControl(self)
        self.series_page = SeriesControl(self)
        self.temperature_page = TemperatureControl(self)

        self.resources_page = ResourcesControl(self)

        materials_page = _prop_grid.Category(self, 'Materials')
        self.material_ctrl = MaterialControl(materials_page)
        self.material_ctrl.SetLabel('Jacket')

        self.core_material_ctrl = PlatingControl(materials_page)
        self.core_material_ctrl.SetLabel('Core')
        self.core_material_ctrl.SetAttributeName('core_material')

        size_page = _prop_grid.Category(self, 'Size')

        self.conductor_dia_mm_ctrl = _prop_grid.FloatProperty(
            general_page, 'Conductor Diameter',
            min_value=0.05, max_value=60.0, increment=0.01, units='mm')

        self.size_mm2_ctrl = _prop_grid.FloatProperty(
            size_page, 'Cross Section',
            min_value=0.00, max_value=99.9999, increment=0.0001, units='mm²')

        self.size_awg_ctrl = _prop_grid.IntProperty(
            size_page, 'Size', min_value=0,
            max_value=30, units='awg')

        self.od_mm_ctrl = _prop_grid.FloatProperty(
            size_page, 'Outside Diameter',
            min_value=0.0, max_value=99.9999, increment=0.0001, units='mm')

        self.tpi_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_tpi)
        self.weight_1km_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_weight_1km)
        self.volts_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_volts)
        self.resistance_1km_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_resistance_1km)
        self.num_conductors_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_num_conductors)
        self.shielded_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_shielded)
        self.conductor_dia_mm_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_conductor_dia_mm)
        self.size_mm2_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_size_mm2)
        self.size_awg_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_size_awg)
        self.od_mm_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_od_mm)

        for page in (
            general_page,
            self.mfg_page,
            self.family_page,
            self.series_page,
            self.temperature_page,
            self.resources_page,
            size_page,
            color_page,
            materials_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
