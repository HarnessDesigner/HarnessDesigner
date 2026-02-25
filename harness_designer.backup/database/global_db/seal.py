from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from ...wrappers.decimal import Decimal as _decimal
from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, SeriesMixin,
                     ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin, Model3DMixin)


class SealsTable(TableBase):
    __table_name__ = 'seals'

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
               color_id: int, lubricant: str, min_temp_id: int, max_temp_id: int, length: _decimal, o_dia: _decimal,
               i_dia: _decimal, wire_dia_min: _decimal, wire_dia_max: _decimal, image_id: int, datasheet_id: int,
               cad_id: int, weight: _decimal) -> "Seal":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 series_id=series_id, type=type, hardness=hardness, color_id=color_id,
                                 lubricant=lubricant, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 length=float(length), o_dia=float(o_dia), i_dia=float(i_dia), wire_dia_min=float(wire_dia_min),
                                 wire_dia_max=float(wire_dia_max), image_id=image_id, datasheet_id=datasheet_id,
                                 cad_id=cad_id, weight=float(weight))
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


class Seal(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, SeriesMixin,
           ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin, Model3DMixin):

    _table: SealsTable = None

    @property
    def o_dia(self) -> _decimal:
        return _decimal(self._table.select('o_dia', id=self._db_id)[0][0])

    @o_dia.setter
    def o_dia(self, value: _decimal):
        self._table.update(self._db_id, o_dia=float(value))

    @property
    def i_dia(self) -> _decimal:
        return _decimal(self._table.select('i_dia', id=self._db_id)[0][0])

    @i_dia.setter
    def i_dia(self, value: _decimal):
        self._table.update(self._db_id, i_dia=float(value))

    @property
    def type(self) -> str:
        return self._table.select('type', id=self._db_id)[0][0]

    @type.setter
    def type(self, value: str):
        self._table.update(self._db_id, type=value)

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
    def length(self) -> _decimal:
        return _decimal(self._table.select('length', id=self._db_id)[0][0])

    @length.setter
    def length(self, value: _decimal):
        self._table.update(self._db_id, length=float(value))

    @property
    def wire_dia_min(self) -> _decimal:
        return _decimal(self._table.select('wire_dia_min', id=self._db_id)[0][0])

    @wire_dia_min.setter
    def wire_dia_min(self, value: _decimal):
        self._table.update(self._db_id, wire_dia_min=float(value))

    @property
    def wire_dia_max(self) -> _decimal:
        return _decimal(self._table.select('wire_dia_max', id=self._db_id)[0][0])

    @wire_dia_max.setter
    def wire_dia_max(self, value: _decimal):
        self._table.update(self._db_id, wire_dia_max=float(value))
