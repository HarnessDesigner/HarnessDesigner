from typing import Iterable as _Iterable, TYPE_CHECKING

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin,
                     ResourceMixin, TemperatureMixin, ColorMixin, SeriesMixin,
                     MaterialMixin, ProtectionMixin, AdhesiveMixin, WeightMixin,
                     FamilyMixin)


if TYPE_CHECKING:
    from . import temperature as _temperature


class BundleCoversTable(TableBase):
    __table_name__ = 'bundle_covers'

    def _load_database(self, splash):
        from ..create_database import bundle_covers

        data_path = self._con.db_data.open(splash)
        bundle_covers.add_records(self._con, splash, data_path)

    def _table_needs_update(self) -> bool:
        from ..create_database import bundle_covers

        return bundle_covers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import bundle_covers

        bundle_covers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        bundle_covers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import bundle_covers

        bundle_covers.table.update_fields(self)

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
               min_size: float, max_size: float, wall: str, shrink_ratio: str, protections: str,
               material_id: int, rigidity: str, shrink_temp_id: int, adhesives: list[str],
               weight: float) -> "BundleCover":
        
        db_id = TableBase.insert(self, part_number=part_number, mfg_id=mfg_id, description=description, 
                                 series_id=series_id, image_id=image_id, datasheet_id=datasheet_id, 
                                 cad_id=cad_id, min_temp_id=min_temp_id, max_temp_id=max_temp_id,
                                 color_id=color_id, min_size=min_size, max_size=max_size, wall=wall,
                                 shrink_ratio=shrink_ratio, protections=protections,
                                 material_id=material_id, rigidity=rigidity, shrink_temp_id=shrink_temp_id,
                                 adhesives=f"[{', '.join(adhesives)}]", weight=weight)

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
                  MaterialMixin, ProtectionMixin, AdhesiveMixin, WeightMixin,
                  FamilyMixin):
    
    _table: BundleCoversTable = None

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
        }

        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)

        return packet

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
    def min_dia(self) -> float:
        return self._table.select('min_dia', id=self._db_id)[0][0]

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=round(value, 6))
        
    @property
    def max_dia(self) -> float:
        return self._table.select('max_dia', id=self._db_id)[0][0]

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, max_dia=round(value, 6))

    @property
    def propgrid(self):
        from ...ui.editor_obj.prop_grid import float_prop as _float_prop

        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        material_prop = self._material_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        adhesives_prop = self._adhesives_propgrid
        shrink_temp_prop = self.shrink_temp.propgrid

        shrink_temp_prop.SetLabel('Shrink Temperature')

        rigidity_prop = wxpg.StringProperty('Rigidity', 'rigidity', self.rigidity)
        shrink_ratio_prop = wxpg.StringProperty('Shrink Ratio', 'shrink_ratio', self.shrink_ratio)
        wall_prop = wxpg.StringProperty('Wall', 'wall', self.wall)

        diameter_prop = wxpg.PGProperty('Diameter')

        min_dia_prop = _float_prop.FloatProperty(
            'Minimum', 'min_dia', self.min_dia, min_value=0.01,
            max_value=999.9, increment=0.01, units='mm')

        max_dia_prop = _float_prop.FloatProperty(
            'Maximum', 'max_dia', self.max_dia, min_value=0.01,
            max_value=999.9, increment=0.01, units='mm')

        diameter_prop.AppendChild(min_dia_prop)
        diameter_prop.AppendChild(max_dia_prop)

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(diameter_prop)
        part_cat.AppendChild(shrink_ratio_prop)
        part_cat.AppendChild(shrink_temp_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(wall_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(rigidity_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(material_prop)
        part_cat.AppendChild(adhesives_prop)

        return part_cat
