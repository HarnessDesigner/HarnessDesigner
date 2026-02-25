from typing import Iterable as _Iterable


from . import EntryBase, TableBase
from ...wrappers.decimal import Decimal as _decimal

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, ColorMixin,
                     FamilyMixin, SeriesMixin, ResourceMixin, WeightMixin, TemperatureMixin,
                     Model3DMixin)


class BootsTable(TableBase):
    __table_name__ = 'boots'

    def __iter__(self) -> _Iterable["Boot"]:
        for db_id in TableBase.__iter__(self):
            yield Boot(self, db_id)

    def __getitem__(self, item) -> "Boot":
        if isinstance(item, int):
            if item in self:
                return Boot(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Boot(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, min_temp_id: int, max_temp_id: int, image_id: int,
               datasheet_id: int, cad_id: int, color_id: int, weight: _decimal) -> "Boot":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, color_id=color_id, weight=float(weight))

        return Boot(self, db_id)

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
                'label': 'Material',
                'type': [int, str],
                'search_params': ['material_id', 'materials', 'name']
            },
            7: {
                'label': 'Direction',
                'type': [int, str],
                'search_params': ['direction_id', 'directions', 'name']
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
                'label': 'Weight',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class Boot(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
           SeriesMixin, ResourceMixin, WeightMixin, ColorMixin, TemperatureMixin, Model3DMixin):
    _table: BootsTable = None
