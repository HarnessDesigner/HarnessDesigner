from typing import Iterable as _Iterable, TYPE_CHECKING
import math

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, SeriesMixin,
                     ResourceMixin, ColorMixin, FamilyMixin, MaterialMixin, TemperatureMixin)


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

    @property
    def od_mm(self) -> float:
        return self._table.select('od_mm', id=self._db_id)[0][0]

    @od_mm.setter
    def od_mm(self, value: float):
        self._table.update(self._db_id, od_mm=value)

    @property
    def shielded(self) -> bool:
        return bool(self._table.select('shielded', id=self._db_id)[0][0])

    @shielded.setter
    def shielded(self, value: bool):
        self._table.update(self._db_id, shielded=int(value))

    @property
    def tpi(self) -> int:
        return self._table.select('tpi', id=self._db_id)[0][0]

    @tpi.setter
    def tpi(self, value: int):
        self._table.update(self._db_id, tpi=value)

    @property
    def num_conductors(self) -> int:
        return self._table.select('num_conductors', id=self._db_id)[0][0]

    @num_conductors.setter
    def num_conductors(self, value: int):
        self._table.update(self._db_id, num_conductors=value)

    @property
    def core_material(self) -> "_plating.Plating":
        db_id = self.core_material_id
        return self._table.db.platings_table[db_id]

    @core_material.setter
    def core_material(self, value: "_plating.Plating"):
        self.core_material_id = value.db_id

    @property
    def core_material_id(self) -> int:
        return self._table.select('core_material_id', id=self._db_id)[0][0]

    @core_material_id.setter
    def core_material_id(self, value: int):
        self._table.update(self._db_id, core_material_id=value)

    @property
    def conductor_dia_mm(self) -> float:
        d_mm = self._table.select('conductor_dia_mm', id=self._db_id)[0][0]

        if d_mm is None:
            d_mm = round(self.conductor_dia_in * 25.4, 4)

        return d_mm

    @conductor_dia_mm.setter
    def conductor_dia_mm(self, value: float):
        self._table.update(self._db_id, conductor_dia_mm=value)

    @property
    def conductor_dia_in(self) -> float:
        d_in = 0.005 * (92 ** ((36 - self.size_awg) / 39))
        return round(float(d_in), 4)

    @conductor_dia_in.setter
    def conductor_dia_in(self, value: float):
        self.conductor_dia_mm = value * 25.4

    @property
    def size_mm2(self) -> float:
        mm2 = self._table.select('size_mm2', id=self._db_id)[0][0]

        if mm2 is None:
            awg = self.size_awg

            if awg is None:
                d_mm = self.conductor_dia_mm

                if d_mm is None:
                    raise RuntimeError('sanity check')

                return self.__mm_to_mm2(d_mm)

            return self.__awg_to_mm2(awg)

        return mm2

    @size_mm2.setter
    def size_mm2(self, value: float):
        self._table.update(self._db_id, size_mm2=value)

    @property
    def size_awg(self) -> int:
        awg = self._table.select('size_awg', id=self._db_id)[0][0]

        if awg is None:
            mm2 = self.size_mm2

            if mm2 is None:
                dia_mm = self.conductor_dia_mm

                if dia_mm is None:
                    raise RuntimeError('sanity check')

                return self.__mm_to_awg(dia_mm)

            return self.__mm2_to_awg(mm2)

        return awg

    @size_awg.setter
    def size_awg(self, value: int):
        self._table.update(self._db_id, size_awg=value)

    @staticmethod
    def __awg_to_mm2(awg: int) -> float:
        d_in = 0.005 * (92 ** ((36 - awg) / 39))
        d_mm = d_in * 25.4
        area_mm2 = (math.pi / 4) * (d_mm ** 2)
        return round(area_mm2, 4)

    @staticmethod
    def __mm_to_mm2(d_mm: float) -> float:
        area_mm2 = (math.pi / 4) * (d_mm ** 2)
        return float(round(area_mm2, 4))

    @classmethod
    def __mm_to_awg(cls, d_mm: float) -> int:
        area_mm2 = (math.pi / 4) * (d_mm ** 2)
        return cls.__mm2_to_awg(area_mm2)

    @staticmethod
    def __mm2_to_awg(mm2: float) -> int:
        d_mm = 2 * math.sqrt(mm2 / math.pi)
        d_in = d_mm / 25.4
        awg = 36 - 39 * math.log(d_in / 0.005, 92)
        return int(round(awg))

    @property
    def size_in2(self) -> float:
        area_mm2 = self.size_mm2
        area_in2 = area_mm2 / 25.4 / 25.4
        return round(float(area_in2), 4)

    @size_in2.setter
    def size_in2(self, value: float):
        self.size_mm2 = value * 25.4 * 25.4

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

    @stripe_color.setter
    def stripe_color(self, value: "_color.Color"):
        self._table.update(self._db_id, stripe_color_id=value.db_id)

    @property
    def stripe_color_id(self) -> int | None:
        return self._table.select('stripe_color_id', id=self._db_id)[0][0]

    @stripe_color_id.setter
    def stripe_color_id(self, value: int | None):
        self._table.update(self._db_id, stripe_color_id=value)

    @property
    def propgrid(self):
        from ...ui.editor_obj.prop_grid import float_prop as _float_prop
        from ...ui.editor_obj.prop_grid import bool_prop as _bool_prop
        from ...ui.editor_obj.prop_grid import int_prop as _int_prop

        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        resource_prop = self._resource_propgrid
        material_prop = self._material_propgrid
        stripe_color_prop = self.stripe_color.propgrid
        core_material_prop = self.core_material.propgrid

        stripe_color_prop.SetLabel('Stripe Color')
        material_prop.SetLabel('Jacket Material')
        core_material_prop.SetLabel('Core Material')

        tpi_prop = _float_prop.FloatProperty(
            'Twists per Inch', 'tpi', self.od_mm,
            min_value=0.05, max_value=60.0, increment=0.01, units='tpi')
            
        conductor_dia_mm_prop = _float_prop.FloatProperty(
            'Conductor Diameter', 'conductor_dia_mm', self.conductor_dia_mm,
            min_value=0.05, max_value=60.0, increment=0.01, units='mm')
            
        weight_1km_prop = _float_prop.FloatProperty(
            'Weight', 'weight_1km', self.weight_1km,
            min_value=0.05, max_value=99999.99, increment=0.01, units='g/km')

        volts_prop = _float_prop.FloatProperty(
            'Volts', 'volts', self.volts,
            min_value=0.05, max_value=100000.00, increment=0.01, units='V')
            
        resistance_1km_prop = _float_prop.FloatProperty(
            'Resistance', 'resistance_1km', self.resistance_1km,
            min_value=0.05, max_value=99999.99, increment=0.01, units='Ω/km')
            
        od_mm_prop = _float_prop.FloatProperty(
            'Outside Diameter', 'od_mm', self.od_mm,
            min_value=0.05, max_value=60.0, increment=0.01, units='mm')
            
        size_mm2_prop = _float_prop.FloatProperty(
            'Size', 'size_mm2', self.size_mm2,
            min_value=0.05, max_value=60.0, increment=0.01, units='mm²')

        num_conductors_prop = _int_prop.IntProperty(
            'Conductor Count', 'num_conductors', self.num_conductors, min_value=0, 
            max_value=10)
            
        size_awg_prop = _int_prop.IntProperty(
            'Size', 'size_awg', self.size_awg, min_value=30, 
            max_value=0, units='awg')

        shielded_prop = _bool_prop.BoolProperty(
            'Shielded', 'shielded', self.shielded)

        wire_size_prop = wxpg.PGProperty('Wire Size')
        wire_size_prop.AppendChild(conductor_dia_mm_prop)
        wire_size_prop.AppendChild(od_mm_prop)
        wire_size_prop.AppendChild(size_mm2_prop)
        wire_size_prop.AppendChild(size_awg_prop)

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(material_prop)
        part_cat.AppendChild(core_material_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(stripe_color_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(tpi_prop)
        part_cat.AppendChild(wire_size_prop)
        part_cat.AppendChild(weight_1km_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(volts_prop)
        part_cat.AppendChild(resistance_1km_prop)
        part_cat.AppendChild(num_conductors_prop)
        part_cat.AppendChild(shielded_prop)

        return part_cat
