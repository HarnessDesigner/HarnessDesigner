from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from ...wrappers.decimal import Decimal as _decimal
from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, DirectionMixin,
                     FamilyMixin, SeriesMixin, ResourceMixin, WeightMixin,
                     TemperatureMixin, ColorMixin, DimensionMixin, Model3DMixin)


class CoversTable(TableBase):
    __table_name__ = 'covers'

    def __iter__(self) -> _Iterable["Cover"]:
        for db_id in TableBase.__iter__(self):
            yield Cover(self, db_id)

    def __getitem__(self, item) -> "Cover":
        if isinstance(item, int):
            if item in self:
                return Cover(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Cover(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, image_id: int, datasheet_id: int, cad_id: int,
               direction_id: int, min_temp_id: int, max_temp_id: int, color_id: int,
               length: _decimal, width: _decimal, height: _decimal, pins: str, weight: _decimal) -> "Cover":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, direction_id=direction_id,
                                 min_temp_id=min_temp_id, max_temp_id=max_temp_id, color_id=color_id,
                                 length=float(length), width=float(width), height=float(height),
                                 pins=pins, weight=float(weight))

        return Cover(self, db_id)

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
                'label': 'Direction',
                'type': [int, str],
                'search_params': ['direction_id', 'directions', 'name']
            },
            7: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            8: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Width (mm)',
                'type': [float],
                'search_params': ['width']
            },
            11: {
                'label': 'Height (mm)',
                'type': [float],
                'search_params': ['height']
            },
            12: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Cover(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, DirectionMixin,
            FamilyMixin, SeriesMixin, ResourceMixin, TemperatureMixin,
            ColorMixin, DimensionMixin, WeightMixin, Model3DMixin):

    _table: CoversTable = None

    @property
    def pins(self) -> str:
        return self._table.select('pins', id=self._db_id)[0][0]

    @pins.setter
    def pins(self, value: str):
        self._table.update(self._db_id, pins=value)
