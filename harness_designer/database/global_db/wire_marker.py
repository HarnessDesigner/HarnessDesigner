from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase

from .mixins import (PartNumberMixin, ManufacturerMixin, DescriptionMixin, FamilyMixin,
                     SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin, WeightMixin)


class WireMarkersTable(TableBase):
    __table_name__: str = 'wire_markers'

    def _table_needs_update(self) -> bool:
        from ..create_database import wire_markers

        return wire_markers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import wire_markers

        wire_markers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        wire_markers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import wire_markers

        wire_markers.table.update_fields(self)

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
                 FamilyMixin, SeriesMixin, ColorMixin, TemperatureMixin, ResourceMixin,
                 WeightMixin):

    _table: WireMarkersTable = None

    def build_monitor_packet(self):
        mfg = self.manufacturer
        color = self.color

        packet = {
            'wire_markers': [self.db_id],
            'colors': [color.db_id],
            'datasheets': [self.datasheet_id],
            'cads': [self.cad_id],
            'images': [self.image_id]
        }

        self.merge_packet_data(mfg.build_monitor_packet(), packet)

        return packet

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
    def min_awg(self) -> int:
        return self._table.select('min_awg', id=self._db_id)[0][0]

    @min_awg.setter
    def min_awg(self, value: int):
        self._table.update(self._db_id, min_awg=value)

    @property
    def max_awg(self) -> int:
        return self._table.select('max_awg', id=self._db_id)[0][0]

    @max_awg.setter
    def max_awg(self, value: int):
        self._table.update(self._db_id, max_awg=value)

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)

    @property
    def propgrid(self):
        from ...ui.editor_obj.prop_grid import float_prop as _float_prop
        from ...ui.editor_obj.prop_grid import int_prop as _int_prop
        from ...ui.editor_obj.prop_grid import bool_prop as _bool_prop

        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid

        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        color_prop = self._color_propgrid
        temperature_prop = self._temperature_propgrid

        diameter_prop = wxpg.PGProperty('Diameter')

        min_diameter_prop = _float_prop.FloatProperty(
            'Minimum', 'min_diameter', self.min_diameter, min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')
            
        max_diameter_prop = _float_prop.FloatProperty(
            'Maximum', 'max_diameter', self.max_diameter, min_value=0.05,
            max_value=60.0, increment=0.01, units='mm')

        diameter_prop.AppendChild(min_diameter_prop)
        diameter_prop.AppendChild(max_diameter_prop)

        wire_size_prop = wxpg.PGProperty('Wire Size')

        min_awg_prop = _int_prop.IntProperty(
            'Minimum', 'min_awg', self.min_awg, min_value=30,
            max_value=0, units='awg')
            
        max_awg_prop = _int_prop.IntProperty(
            'Maximum', 'max_awg', self.max_awg, min_value=30,
            max_value=0, units='awg')

        wire_size_prop.AppendChild(min_awg_prop)
        wire_size_prop.AppendChild(max_awg_prop)

        length_prop = _float_prop.FloatProperty(
            'Length', 'length', self.length, min_value=0.01,
            max_value=99.99, increment=0.01, units='mm')

        label_prop = _bool_prop.BoolProperty(
            'Has Label', 'has_label', self.has_label)

        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid

        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(label_prop)
        part_cat.AppendChild(length_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(wire_size_prop)
        part_cat.AppendChild(diameter_prop)

        return part_cat
