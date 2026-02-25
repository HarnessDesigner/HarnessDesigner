from typing import Iterable as _Iterable

from . import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                     ResourceMixin, ColorMixin)


class WireMarkersTable(TableBase):
    __table_name__: str = 'wire_markers'

    def __iter__(self) -> _Iterable["WireMarker"]:

        for db_id in TableBase.__iter__(self):
            yield WireMarker(self, db_id)

    def __getitem__(self, item) -> "WireMarker":
        if isinstance(item, int):
            if item in self:
                return WireMarker(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return WireMarker(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, image_id: int, datasheet_id: int,
               cad_id: int, color_id: int, min_diameter: float, max_diameter: float, length: float) -> "WireMarker":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 image_id=image_id, datasheet_id=datasheet_id, cad_id=cad_id,
                                 color_id=color_id, min_diameter=min_diameter,
                                 max_diameter=max_diameter, length=length)

        return WireMarker(self, db_id)

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
                'label': 'Color',
                'type': [int, str],
                'search_params': ['color_id', 'colors', 'name']
            },
            4: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['min_awg']
            },
            5: {
                'label': 'Diameter (Min)(AWG)',
                'type': [int],
                'search_params': ['max_awg']
            },
            6: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['min_diameter']
            },
            7: {
                'label': 'Diameter (Min)(mm)',
                'type': [float],
                'search_params': ['max_diameter']
            },
            8: {
                'label': 'Label',
                'type': [bool],
                'search_params': ['has_label']
            },
            9: {
                'label': 'Length (mm)',
                'type': [float],
                'search_params': ['length']
            },
            10: {
                'label': 'Weight (g)',
                'type': [float],
                'search_params': ['weight']
            }
        }

        return ret


class WireMarker(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                 ColorMixin, ResourceMixin):

    _table: WireMarkersTable = None

    @property
    def weight(self) -> float:
        return self._table.select('weight', id=self._db_id)[0][0]

    @weight.setter
    def weight(self, value: float):
        self._table.update(self._db_id, weight=value)

    @property
    def has_label(self) -> bool:
        return bool(self._table.select('has_label', id=self._db_id)[0][0])

    @has_label.setter
    def has_label(self, value: bool):
        self._table.update(self._db_id, has_label=int(value))

    @property
    def min_diameter(self) -> float:
        return self._table.select('min_diameter', id=self._db_id)[0][0]

    @min_diameter.setter
    def min_diameter(self, value: float):
        self._table.update(self._db_id, min_diameter=value)

    @property
    def max_diameter(self) -> float:
        return self._table.select('max_diameter', id=self._db_id)[0][0]

    @max_diameter.setter
    def max_diameter(self, value: float):
        self._table.update(self._db_id, max_diameter=value)

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)
