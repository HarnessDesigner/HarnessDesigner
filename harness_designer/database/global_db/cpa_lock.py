from typing import TYPE_CHECKING, Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
                     SeriesMixin, ResourceMixin, TemperatureMixin, WeightMixin,
                     ColorMixin, DimensionMixin, Model3DMixin, CompatHousingsMixin)

if TYPE_CHECKING:
    from . import cpa_lock_type as _cpa_lock_type


class CPALocksTable(TableBase):
    __table_name__ = 'cpa_locks'

    def _load_database(self, splash):
        from ..create_database import cpa_locks

        data_path = self._con.db_data.open(splash)
        cpa_locks.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import cpa_locks

        return cpa_locks.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import cpa_locks

        cpa_locks.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        cpa_locks.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import cpa_locks

        cpa_locks.table.update_fields(self)

    def __iter__(self) -> _Iterable["CPALock"]:

        for db_id in TableBase.__iter__(self):
            yield CPALock(self, db_id)

    def __getitem__(self, item) -> "CPALock":
        if isinstance(item, int):
            if item in self:
                return CPALock(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', part_number=item)
        if db_id:
            return CPALock(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, part_number: str, mfg_id: int, description: str, family_id: int,
               series_id: int, image_id: int, datasheet_id: int, cad_id: int, min_temp_id: int,
               max_temp_id: int, pins: str, color_id: int, length: float, width: float,
               height: float, terminal_size: float, weight: float) -> "CPALock":

        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description,
                                 family_id=family_id, series_id=series_id, image_id=image_id,
                                 datasheet_id=datasheet_id, cad_id=cad_id, min_temp_id=min_temp_id,
                                 max_temp_id=max_temp_id, pins=pins, color_id=color_id, length=float(length),
                                 width=float(width), height=float(height), terminal_size=float(terminal_size), weight=float(weight))

        return CPALock(self, db_id)

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


class CPALock(EntryBase, PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
              SeriesMixin, ResourceMixin, TemperatureMixin, WeightMixin,
              ColorMixin, DimensionMixin, Model3DMixin, CompatHousingsMixin):

    _table: CPALocksTable = None

    def build_monitor_packet(self):
        color = self.color

        packet = {
            'cpa_locks': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'temperatures': [self.min_temp_id, self.max_temp],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id],
            'models3d': [self.model3d_id]
        }
        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)

        return packet

    @property
    def type(self) -> "_cpa_lock_type.CPALockType":
        type_id = self.type_id
        return self._table.db.cpa_locks_table[type_id]

    @property
    def type_id(self) -> int:
        return self._table.select('type_id', id=self._db_id)[0][0]

    @type_id.setter
    def type_id(self, value: int):
        self._table.update(self._db_id, type_id=value)

    @property
    def pins(self) -> str:
        return self._table.select('pins', id=self._db_id)[0][0]

    @pins.setter
    def pins(self, value: str):
        self._table.update(self._db_id, pins=value)

    @property
    def terminal_size(self) -> float:
        return self._table.select('terminal_size', id=self._db_id)[0][0]

    @terminal_size.setter
    def terminal_size(self, value: float):
        self._table.update(self._db_id, terminal_size=value)

    @property
    def propgrid(self):       
        part_cat = wxpg.PropertyCategory('Part Attributes')
        
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
        
        compat_housings_prop = self._compat_housings_propgrid

        type_prop = self.type.propgrid

        pins_prop = wxpg.StringProperty('Pins', 'pins', self.pins)       

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(type_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(dimension_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(pins_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(model3d_prop)
        part_cat.AppendChild(compat_housings_prop)

        return part_cat