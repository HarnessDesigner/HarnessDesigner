from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import PartNumberMixin, DescriptionMixin, ManufacturerMixin, FamilyMixin, SeriesMixin, ColorMixin, MaterialMixin


class AccessoriesTable(TableBase):
    __table_name__ = 'accessories'

    def __iter__(self) -> _Iterable["Accessory"]:
        for db_id in TableBase.__iter__(self):
            yield Accessory(self, db_id)

    def __getitem__(self, item) -> "Accessory":
        if isinstance(item, int):
            if item in self:
                return Accessory(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return Accessory(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, description: str, mfg_id: int, family_id: int,
               series_id: int, material_id: int, color_id: int) -> "Accessory":

        db_id = TableBase.insert(self, part_number=part_number, description=description,
                                 mfg_id=mfg_id, family_id=family_id, series_id=series_id,
                                 material_id=material_id, color_id=color_id)

        return Accessory(self, db_id)

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
        }
        return ret


class Accessory(EntryBase, PartNumberMixin, DescriptionMixin, ManufacturerMixin, FamilyMixin, SeriesMixin, ColorMixin, MaterialMixin):
    _table: AccessoriesTable = None
