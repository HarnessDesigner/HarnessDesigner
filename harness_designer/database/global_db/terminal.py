from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from ...geometry import point as _point

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, GenderMixin,
                     SeriesMixin, FamilyMixin, ResourceMixin, WeightMixin, CavityLockMixin,
                     Model3DMixin, PlatingMixin, CompatHousingsMixin, CompatSealsMixin,
                     TemperatureMixin, ColorMixin, WireSizeMixin)

if TYPE_CHECKING:
    from . import seal as _seal


class TerminalsTable(TableBase):
    __table_name__: str = 'terminals'

    def _load_database(self, splash):
        from ..create_database import terminals

        data_path = self._con.db_data.open(splash)
        terminals.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import terminals

        return terminals.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import terminals

        terminals.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        terminals.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import terminals

        terminals.table.update_fields(self)

    def __iter__(self) -> _Iterable["Terminal"]:
        for db_id in TableBase.__iter__(self):
            yield Terminal(self, db_id)

    def __getitem__(self, item) -> "Terminal":
        if isinstance(item, int):
            if item in self:
                return Terminal(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Terminal(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, gender_id: int,
               series_id: int, family_id: int, sealing: bool, cavity_lock_id: int,
               image_id: int, datasheet_id: int, cad_id: int, material_id: int,
               blade_size: float, resistance: int, mating_cycles: int,
               max_vibration_g: int, max_current_ma: int, wire_size_min_awg: int,
               wire_size_max_awg: int, wire_dia_min: float, wire_dia_max: float,
               min_wire_cross: float, max_wire_cross: float, plating_id: int,
               weight: float, length: float, width, _decimal, height: float) -> "Terminal":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 gender_id=gender_id, series_id=series_id, family_id=family_id, sealing=int(sealing),
                                 cavity_lock_id=cavity_lock_id, image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, material_id=material_id, blade_size=float(blade_size),
                                 resistance=resistance, mating_cycles=mating_cycles,
                                 max_vibration_g=max_vibration_g, max_current_ma=max_current_ma,
                                 wire_size_min_awg=wire_size_min_awg, wire_size_max_awg=wire_size_max_awg,
                                 wire_dia_min=float(wire_dia_min), wire_dia_max=float(wire_dia_max),
                                 min_wire_cross=float(min_wire_cross), max_wire_cross=float(max_wire_cross),
                                 plating_id=plating_id, weight=float(weight), length=float(length), width=float(width),
                                 height=float(height))

        return Terminal(self, db_id)

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
                'label': 'Plating',
                'type': [int, str],
                'search_params': ['plating_id', 'platings', 'symbol']
            },
            6: {
                'label': 'Gender',
                'type': [int, str],
                'search_params': ['gender_id', 'genders', 'name']
            },
            7: {
                'label': 'Current (ma)',
                'type': [int],
                'search_params': ['max_current_ma']
            },
            8: {
                'label': 'Blade Size (mm)',
                'type': [float],
                'search_params': ['blade_size']
            },
            9: {
                'label': 'Wire Size (Min)(AWG)',
                'type': [int],
                'search_params': ['wire_size_min_awg']
            },
            10: {
                'label': 'Wire Size (Max)(AWG)',
                'type': [int],
                'search_params': ['wire_size_max_awg']
            },
            11: {
                'label': 'Wire Size (Min)(mm2)',
                'type': [float],
                'search_params': ['min_wire_cross']
            },
            12: {
                'label': 'Wire Size (Max)(mm2)',
                'type': [float],
                'search_params': ['max_wire_cross']
            },
            13: {
                'label': 'Sealable',
                'type': [bool],
                'search_params': ['sealing']
            },
            14: {
                'label': 'Resistance',
                'type': [float],
                'out_params': 'resistance'
            },
            15: {
                'label': 'Mating Cycles',
                'type': [int],
                'out_params': 'mating_cycles'
            },
            16: {
                'label': 'Cavity Lock',
                'type': [int, str],
                'search_params': ['cavity_lock_id', 'cavity_locks', 'name']
            },
            17: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            18: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            19: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            20: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Terminal(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
               GenderMixin, SeriesMixin, FamilyMixin, ResourceMixin, TemperatureMixin,
               WeightMixin, CavityLockMixin, PlatingMixin, Model3DMixin,
               CompatHousingsMixin, CompatSealsMixin, ColorMixin, WireSizeMixin):

    _table: TerminalsTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer

        packet = {
            'terminals': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'platings': [self.plating_id],
            'datasheets': [self.datasheet_id],
            'cavity_locks': [self.cavity_lock_id],
            'genders': [self.gender_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        if not self.sealing:
            return []

        min_dia = self.min_dia
        max_dia = self.max_dia

        if not min_dia or not max_dia:
            return []

        cmd = (f'SELECT id FROM seals WHERE wire_dia_min <= {min_dia} '
               f'AND wire_dia_max >= {max_dia};')

        self._table.db.seals_table.execute(cmd)
        rows = self._table.db.seals_table.fetchall()

        res = []
        for row in rows:
            seal = self._table.db.seals_table[row[0]]
            if seal.type.lower() not in ('sws', 'single wire seal'):
                continue
            res.append(seal)

        return res

    @property
    def sealing(self) -> bool:
        return bool(self._table.select('sealing', id=self._db_id)[0][0])

    @sealing.setter
    def sealing(self, value: bool):
        self._table.update(self._db_id, size=int(value))

    @property
    def blade_size(self) -> float:
        return self._table.select('blade_size', id=self._db_id)[0][0]

    @blade_size.setter
    def blade_size(self, value: float):
        self._table.update(self._db_id, blade_size=value)

    @property
    def resistance(self) -> float:
        return self._table.select('resistance', id=self._db_id)[0][0]

    @resistance.setter
    def resistance(self, value: float):
        self._table.update(self._db_id, resistance=value)

    @property
    def mating_cycles(self) -> int:
        return self._table.select('mating_cycles', id=self._db_id)[0][0]

    @mating_cycles.setter
    def mating_cycles(self, value: int):
        self._table.update(self._db_id, mating_cycles=value)

    @property
    def max_vibration_g(self) -> int:
        return self._table.select('max_vibration_g', id=self._db_id)[0][0]

    @max_vibration_g.setter
    def max_vibration_g(self, value: int):
        self._table.update(self._db_id, max_vibration_g=value)

    @property
    def max_current_ma(self) -> int:
        return self._table.select('max_current_ma', id=self._db_id)[0][0]

    @max_current_ma.setter
    def max_current_ma(self, value: int):
        self._table.update(self._db_id, max_current_ma=value)

    @property
    def round_terminal(self) -> bool:
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        self._table.update(self._db_id, round_terminal=int(value))

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=round(value, 6))

    @property
    def width(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                width = min(width, height)
                self._table.update(self._db_id, width=width, height=width)
            return width

        else:
            return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, width=round(value, 6))

    @property
    def height(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                height = min(width, height)
                self._table.update(self._db_id, width=height, height=height)

            return height

        else:
            return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, height=round(value, 6))

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            if self.round_terminal:
                if y > 0:
                    x = y

                    self._table.update(self._db_id, width=y)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, width=1.0)
                x = 1.0

        if y <= 0:
            if self.round_terminal:
                if x > 0:
                    y = x

                    self._table.update(self._db_id, height=x)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, height=1.0)
                y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def _dimension_propgrid(self) -> _prop_grid.Property:

        group_prop = _prop_grid.Property('Dimensions', '')

        length_prop = _prop_grid.FloatProperty(
            'Length', 'length', self.length,
            min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        width_prop = _prop_grid.FloatProperty(
            'Width', 'width', self.width,
            min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        height_prop = _prop_grid.FloatProperty(
            'Height', 'height', self.height,
            min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        group_prop.Append(length_prop)
        group_prop.Append(width_prop)
        group_prop.Append(height_prop)

        return group_prop

    @property
    def propgrid(self) -> _prop_grid.Category:
        part_cat = _prop_grid.Category('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        gender_prop = self._gender_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        dimension_prop = self._dimension_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid
        wire_size_prop = self._wire_size_propgrid
        compat_housings_prop = self._compat_housings_propgrid
        compat_seals_prop = self._compat_seals_propgrid
        plating_prop = self._plating_propgrid
        cavity_lock_prop = self._cavity_lock_propgrid

        sealing_prop = _prop_grid.BoolProperty(
            'Sealing', 'sealing', self.sealing)

        blade_size_prop = _prop_grid.FloatProperty(
            'Blade Size', 'blade_size', self.blade_size,
            min_value=0.01, max_value=99.00, increment=0.01, units='mm')

        resistance_prop = _prop_grid.FloatProperty(
            'Resistance', 'resistance', self.resistance,
            min_value=0.1, max_value=10000000.00, increment=0.1, units='Ω')

        mating_cycles_prop = _prop_grid.IntProperty(
            'Mating Cycles', 'mating_cycles', self.mating_cycles,
            min_value=1, max_value=100000)

        max_vibration_g_prop = _prop_grid.IntProperty(
            'Maximum Vibration', 'max_vibration_g', self.max_vibration_g,
            min_value=0, max_value=100000, units='G')

        max_current_ma_prop = _prop_grid.IntProperty(
            'Maximum Current', 'max_current_ma', self.max_current_ma,
            min_value=0, max_value=100000, units='ma')

        part_cat.Append(part_number_prop)
        part_cat.Append(manufacturer_prop)
        part_cat.Append(description_prop)
        part_cat.Append(family_prop)
        part_cat.Append(series_prop)
        part_cat.Append(gender_prop)
        part_cat.Append(color_prop)
        part_cat.Append(plating_prop)
        part_cat.Append(max_current_ma_prop)
        part_cat.Append(resistance_prop)
        part_cat.Append(blade_size_prop)
        part_cat.Append(wire_size_prop)
        part_cat.Append(sealing_prop)
        part_cat.Append(cavity_lock_prop)
        part_cat.Append(temperature_prop)
        part_cat.Append(dimension_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(resource_prop)
        part_cat.Append(model3d_prop)
        part_cat.Append(max_vibration_g_prop)
        part_cat.Append(mating_cycles_prop)
        part_cat.Append(compat_housings_prop)
        part_cat.Append(compat_seals_prop)

        return part_cat
