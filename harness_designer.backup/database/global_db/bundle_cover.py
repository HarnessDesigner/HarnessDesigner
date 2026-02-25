from typing import Iterable as _Iterable, TYPE_CHECKING

from . import EntryBase, TableBase
from ...wrappers.decimal import Decimal as _decimal
from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                     ResourceMixin, TemperatureMixin, ColorMixin, SeriesMixin,
                     MaterialMixin, ProtectionMixin, AdhesiveMixin, WeightMixin)


if TYPE_CHECKING:
    from . import temperature as _temperature


class BundleCoversTable(TableBase):
    __table_name__ = 'bundle_covers'

    def __iter__(self) -> _Iterable["BundleCover"]:
        for db_id in TableBase.__iter__(self):
            yield BundleCover(self, db_id)

    def __getitem__(self, item) -> "BundleCover":
        if isinstance(item, int):
            if item in self:
                return BundleCover(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return BundleCover(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, series_id: int, image_id: int,
               datasheet_id: int, cad_id: int, min_temp_id: int, max_temp_id: int, color_id: int,
               min_size: _decimal, max_size: _decimal, wall: str, shrink_ratio: str, protections: str,
               material_id: int, rigidity: str, shrink_temp_id: int, adhesives: list[str],
               weight: _decimal) -> "BundleCover":
        
        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description, 
                                 series_id=series_id, image_id=image_id, datasheet_id=datasheet_id, 
                                 cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 color_id=color_id, min_size=float(min_size), max_size=float(max_size), wall=wall,
                                 shrink_ratio=shrink_ratio, protections=protections,
                                 material_id=material_id, rigidity=rigidity, shrink_temp_id=shrink_temp_id,
                                 adhesives=f"[{', '.join(adhesives)}]", weight=float(weight))

        return BundleCover(self, db_id)

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
                'label': 'Diameter (Min)',
                'type': [float],
                'search_params': ['min_dia']
            },
            8: {
                'label': 'Diameter (Max)',
                'type': [float],
                'search_params': ['max_dia']
            },
            9: {
                'label': 'Temperature (Min)',
                'type': [int, str],
                'search_params': ['min_temp_id', 'temperatures', 'name']
            },
            10: {
                'label': 'Temperature (Max)',
                'type': [int, str],
                'search_params': ['max_temp_id', 'temperatures', 'name']
            },
            11: {
                'label': 'Temperature (Shrink)',
                'type': [int, str],
                'search_params': ['shrink_temp_id', 'temperatures', 'name']
            },
            12: {
                'label': 'Weight',
                'type': [float],
                'search_params': ['weight']
            },
            13: {
                'label': 'Rigidity',
                'type': [str],
                'search_params': ['rigidity']
            },
            14: {
                'label': 'Wall',
                'type': [str],
                'search_params': ['wall']
            },
            15: {
                'label': 'Shrink Ratio',
                'type': [str],
                'search_params': ['shrink_ratio']
            },
            16: {
                'label': 'Protection',
                'type': [int, str],
                'search_params': ['protection_id', 'protections', 'name']
            },
        }

        return ret


class BundleCover(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, 
                  ResourceMixin, TemperatureMixin, ColorMixin, SeriesMixin,
                  MaterialMixin, ProtectionMixin, AdhesiveMixin, WeightMixin):
    
    _table: BundleCoversTable = None

    @property
    def rigidity(self) -> str:
        return self._table.select('rigidity', id=self._db_id)[0][0]

    @rigidity.setter
    def rigidity(self, value: str):
        self._table.update(self._db_id, rigidity=value)

    @property
    def shrink_temp(self) -> "_temperature.Temperature":
        shrink_temp_id = self.shrink_temp_id
        from .temperature import Temperature

        return Temperature(self._table.db.temperatures_table, shrink_temp_id)

    @shrink_temp.setter
    def shrink_temp(self, value: "_temperature.Temperature"):
        self._table.update(self._db_id, shrink_temp_id=value.db_id)

    @property
    def shrink_temp_id(self) -> int:
        return self._table.select('shrink_temp_id', id=self._db_id)[0][0]

    @shrink_temp_id.setter
    def shrink_temp_id(self, value: int):
        self._table.update(self._db_id, shrink_temp_id=value)

    @property
    def shrink_ratio(self) -> str:
        return self._table.select('shrink_ratio', id=self._db_id)[0][0]

    @shrink_ratio.setter
    def shrink_ratio(self, value: str):
        self._table.update(self._db_id, shrink_ratio=value)

    @property
    def wall(self) -> str:
        return self._table.select('wall', id=self._db_id)[0][0]

    @wall.setter
    def wall(self, value: str):
        self._table.update(self._db_id, wall=value)
    
    @property
    def min_size(self) -> float:
        return self._table.select('min_size', id=self._db_id)[0][0]

    @min_size.setter
    def min_size(self, value: float):
        self._table.update(self._db_id, min_size=value)
        
    @property
    def max_size(self) -> float:
        return self._table.select('max_size', id=self._db_id)[0][0]

    @max_size.setter
    def max_size(self, value: float):
        self._table.update(self._db_id, max_size=value)
