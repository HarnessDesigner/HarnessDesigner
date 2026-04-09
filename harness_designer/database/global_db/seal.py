from typing import TYPE_CHECKING, Iterable as _Iterable

import uuid
from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from ...geometry import point as _point

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, SeriesMixin,
                     ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin, Model3DMixin,
                     DimensionMixin, FamilyMixin, WireSizeMixin, CompatHousingsMixin, CompatTerminalsMixin)

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

    @property
    def propgrid(self) -> _prop_grid.Category:
        part_cat = _prop_grid.Category('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        dimension_prop = self._dimension_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid
        wire_size_prop = self._wire_size_propgrid
        compat_housings_prop = self._compat_housings_propgrid
        compat_terminals_prop = self._compat_terminals_propgrid
        seal_type_prop = self.type.propgrid

        hardness_prop = _prop_grid.IntProperty(
            'Hardness', 'hardness', self.hardness, min_value=1, max_value=999, units='shore')

        lubricant_prop = _prop_grid.StringProperty('Lubricant', 'lubricant', self.lubricant)

        o_dia_prop = _prop_grid.FloatProperty(
            'Outside Diameter', 'o_dia', self.o_dia, min_value=0.01,
            max_value=99.9, increment=0.01, units='mm')

        i_dia_prop = _prop_grid.FloatProperty(
            'Inside Diameter', 'i_dia', self.i_dia, min_value=0.01,
            max_value=99.9, increment=0.01, units='mm')

        part_cat.Append(part_number_prop)
        part_cat.Append(manufacturer_prop)
        part_cat.Append(description_prop)
        part_cat.Append(family_prop)
        part_cat.Append(series_prop)
        part_cat.Append(color_prop)
        part_cat.Append(temperature_prop)
        part_cat.Append(dimension_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(resource_prop)
        part_cat.Append(model3d_prop)
        part_cat.Append(i_dia_prop)
        part_cat.Append(o_dia_prop)
        part_cat.Append(wire_size_prop)
        part_cat.Append(seal_type_prop)
        part_cat.Append(hardness_prop)
        part_cat.Append(lubricant_prop)
        part_cat.Append(compat_housings_prop)
        part_cat.Append(compat_terminals_prop)

        return part_cat
