from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, DirectionMixin,
                     FamilyMixin, SeriesMixin, ResourceMixin, WeightMixin,
                     TemperatureMixin, ColorMixin, DimensionMixin, Model3DMixin,
                     CompatHousingsMixin)


class CoversTable(TableBase):
    __table_name__ = 'covers'

    def _load_database(self, splash):
        from ..create_database import covers
        covers.add_records(self._con, splash)

    def _table_needs_update(self) -> bool:
        from ..create_database import covers

        return covers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import covers

        covers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        covers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import covers

        covers.table.update_fields(self)

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
               length: float, width: float, height: float, pins: str, weight: float) -> "Cover":

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
            ColorMixin, DimensionMixin, WeightMixin, Model3DMixin, CompatHousingsMixin):

    _table: CoversTable = None

    def build_monitor_packet(self):
        color = self.color

        packet = {
            'covers': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'directions': [self.direction_id],
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
    def pins(self) -> str:
        return self._table.select('pins', id=self._db_id)[0][0]

    @pins.setter
    def pins(self, value: str):
        self._table.update(self._db_id, pins=value)

    @property
    def propgrid(self):       
        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        direction_prop = self._direction_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        dimension_prop = self._dimension_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid
        
        compat_housings_prop = self._compat_housings_propgrid

        pins_prop = wxpg.StringProperty('Pins', 'pins', self.pins)

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(direction_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(dimension_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(pins_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(model3d_prop)
        part_cat.AppendChild(compat_housings_prop)

        return part_cat
