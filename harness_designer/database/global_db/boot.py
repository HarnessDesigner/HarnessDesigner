from typing import Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, ColorMixin,
                     FamilyMixin, SeriesMixin, ResourceMixin, WeightMixin, TemperatureMixin,
                     Model3DMixin, DimensionMixin, CompatHousingsMixin, DirectionMixin)


class BootsTable(TableBase):
    __table_name__ = 'boots'

    def _load_database(self, splash):
        from ..create_database import boots

        data_path = self._con.db_data.open(splash)
        boots.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import boots

        return boots.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import boots

        boots.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        boots.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import boots

        boots.table.update_fields(self)

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
               datasheet_id: int, cad_id: int, color_id: int, weight: float) -> "Boot":

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
           SeriesMixin, ResourceMixin, WeightMixin, ColorMixin, TemperatureMixin,
           Model3DMixin, DimensionMixin, CompatHousingsMixin, DirectionMixin):
    _table: BootsTable = None

    def build_monitor_packet(self):
        color = self.color

        packet = {
            'covers': [self.db_id],
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
    def propgrid(self) -> _prop_grid.Category:       
        part_cat = _prop_grid.Category('Part Attributes')
        
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

        part_cat.Append(part_number_prop)
        part_cat.Append(manufacturer_prop)
        part_cat.Append(description_prop)
        part_cat.Append(family_prop)
        part_cat.Append(series_prop)
        part_cat.Append(color_prop)
        part_cat.Append(direction_prop)
        part_cat.Append(temperature_prop)
        part_cat.Append(dimension_prop)
        part_cat.Append(weight_prop)
        part_cat.Append(resource_prop)
        part_cat.Append(model3d_prop)
        part_cat.Append(compat_housings_prop)

        return part_cat
