from typing import TYPE_CHECKING, Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import (PartNumberMixin, DescriptionMixin, ManufacturerMixin, FamilyMixin,
                     SeriesMixin, MaterialMixin, ColorMixin, PlatingMixin, ResourceMixin,
                     Model3DMixin, WeightMixin, TemperatureMixin)


if TYPE_CHECKING:
    from . import splice_types as _splice_types


class SplicesTable(TableBase):
    __table_name__ = 'splices'

    def _load_database(self, splash):
        from ..create_database import splices

        data_path = self._con.db_data.open(splash)
        splices.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import splices

        return splices.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import splices

        splices.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        splices.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import splices

        splices.table.update_fields(self)

    def __iter__(self) -> _Iterable["Splice"]:
        for db_id in TableBase.__iter__(self):
            yield Splice(self, db_id)

    def __getitem__(self, item) -> "Splice":
        if isinstance(item, int):
            if item in self:
                return Splice(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Splice(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, description: str, mfg_id: int, family_id: int,
               series_id: int, material_id: int, color_id: int, plating_id: int,
               type_id: int, min_dia: float, max_dia: float, resistance: float,
               length: float, weight: float) -> "Splice":

        db_id = TableBase.insert(self, part_number=part_number, description=description,
                                 mfg_id=mfg_id, family_id=family_id, series_id=series_id,
                                 material_id=material_id, color_id=color_id, plating_id=plating_id,
                                 type_id=type_id, min_dia=min_dia, max_dia=max_dia,
                                 resistance=resistance, length=length, weight=weight)

        return Splice(self, db_id)

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
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            6: {
                'label': 'Plating',
                'type': [int, str],
                'search_params': ['plating_id', 'platings', 'symbol']
            },
            7: {
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            8: {
                'label': 'Type',
                'type': [int, str],
                'search_params': ['type_id', 'splice_types', 'name']
            },
            9: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['min_dia']
            },
            10: {
                'label': 'Diameter (Max)(mm)',
                'type': [float],
                'search_params': ['max_dia']
            },
            11: {
                'label': 'Resistance (ohms)',
                'type': [float],
                'search_params': ['resistance']
            },
            12: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            13: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Splice(EntryBase, PartNumberMixin, DescriptionMixin, ManufacturerMixin,
             FamilyMixin, SeriesMixin, MaterialMixin, ColorMixin, PlatingMixin,
             ResourceMixin, Model3DMixin, WeightMixin, TemperatureMixin):

    _table: SplicesTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'tpa_locks': [self.db_id],
            'families': [self.family_id],
            'splice_types': [self.type_id],
            'series': [self.series_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

    @property
    def type(self) -> "_splice_types.SpliceType":
        db_id = self.type_id
        return self._table.db.splice_types_table[db_id]

    @type.setter
    def type(self, value: "_splice_types.SpliceType"):
        self.type_id = value.db_id

    @property
    def type_id(self) -> int:
        return self._table.select('type_id', id=self._db_id)[0][0]

    @type_id.setter
    def type_id(self, value: int):
        self._table.update(self._db_id, type_id=value)

    @property
    def resistance(self) -> float:
        return self._table.select('resistance', id=self._db_id)[0][0]

    @resistance.setter
    def resistance(self, value: float):
        self._table.update(self._db_id, resistance=value)

    @property
    def min_dia(self) -> float:
        return self._table.select('min_dia', id=self._db_id)[0][0]

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)

    @property
    def max_dia(self) -> float:
        return self._table.select('max_dia', id=self._db_id)[0][0]

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)

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
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid
        material_prop = self._material_propgrid
        plating_prop = self._plating_propgrid
        type_prop = self.type.propgrid

        min_dia_prop = _prop_grid.FloatProperty(
            'Minimum Diameter', 'min_dia', self.min_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        max_dia_prop = _prop_grid.FloatProperty(
            'Maximum Diameter', 'max_dia', self.max_dia,
            min_value=0.26, max_value=8.25, increment=0.01, units='mm')

        resistance_prop = _prop_grid.FloatProperty(
            'Resistance', 'resistance', self.resistance,
            min_value=0.1, max_value=10000000.00, increment=0.1, units='Ω')

        length_prop = _prop_grid.FloatProperty(
            'Length', 'length', self.length,
            min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        part_cat.Append(part_number_prop)
        part_cat.Append(manufacturer_prop)
        part_cat.Append(description_prop)
        part_cat.Append(family_prop)
        part_cat.Append(series_prop)
        part_cat.Append(length_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(material_prop)
        part_cat.Append(color_prop)
        part_cat.Append(plating_prop)
        part_cat.Append(resistance_prop)
        part_cat.Append(temperature_prop)
        part_cat.Append(min_dia_prop)
        part_cat.Append(max_dia_prop)
        part_cat.Append(type_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(resource_prop)
        part_cat.Append(model3d_prop)

        return part_cat
