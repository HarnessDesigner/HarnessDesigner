from typing import Iterable as _Iterable

import json

from .bases import EntryBase, TableBase
from .mixins import PartNumberMixin, DescriptionMixin, ManufacturerMixin, FamilyMixin, SeriesMixin, ColorMixin, MaterialMixin


class AccessoriesTable(TableBase):
    __table_name__ = 'accessories'

    def _table_needs_update(self) -> bool:
        from ..create_database import accessories

        return accessories.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import accessories

        accessories.table.add_to_db(self)

        data_path = self._con.db_data.open(splash)
        accessories.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import accessories

        accessories.table.update_fields(self)

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


class Accessory(EntryBase, PartNumberMixin, DescriptionMixin, ManufacturerMixin,
                FamilyMixin, SeriesMixin, ColorMixin, MaterialMixin):

    _table: AccessoriesTable = None

    def build_monitor_packet(self):
        color = self.color

        packet = {
            'accessories': [self.db_id],
            'families': [self.family_id],
            'series': [self.series_id],
            'materials': [self.material_id],
            'colors': [color.db_id],
        }

        self.merge_packet_data(self.manufacturer.build_monitor_packet(), packet)

        return packet

'''
 @property
    def propgrid(self):
        from ...ui.editor_obj.prop_grid import array_string_prop as _array_string_prop

        part_cat = wxpg.PropertyCategory('Part Attributes')
        
        part_number_prop = self._part_number_propgrid
        manufacturer_prop = self._manufacturer_propgrid
        description_prop = self._description_propgrid
        family_prop = self._family_propgrid
        series_prop = self._series_propgrid
        gender_prop = self._gender_propgrid
        ip_rating_prop = self.ip_rating.propgrid
        color_prop = self._color_propgrid
        direction_prop = self._direction_propgrid
        temperature_prop = self._temperature_propgrid
        dimension_prop = self._dimension_propgrid
        weight_prop = self._weight_propgrid
        resource_prop = self._resource_propgrid
        model3d_prop = self._model3d_propgrid

        accessory_parts_prop = wxpg.PGProperty('Accessory Parts')
        
        compat_housings_prop = self._compat_housings_propgrid
        compat_terminals_prop = self._compat_terminals_propgrid
        compat_seals_prop = self._compat_seals_propgrid

        compat_tpas_prop = _array_string_prop.ArrayStringProperty(
            'Compatible TPA Locks', 'compat_tpas_array', self.compat_tpas_array)
        compat_cpas_prop = _array_string_prop.ArrayStringProperty(
            'Compatible CPA Locks', 'compat_cpas_array', self.compat_cpas_array)
        compat_boots_prop = _array_string_prop.ArrayStringProperty(
            'Compatible Boots', 'compat_boots_array', self.compat_boots_array)
        compat_covers_prop = _array_string_prop.ArrayStringProperty(
            'Compatible Covers', 'compat_covers_array', self.compat_covers_array)
    
        from ...ui.editor_obj.prop_grid import position_prop as _position_prop

        cover_position3d_prop = _position_prop.Position3DProperty(
            'Cover Position', 'cover_position3d', self.cover_position3d)
        
        seal_position3d_prop = _position_prop.Position3DProperty(
            'Seal Position', 'seal_position3d', self.seal_position3d)
        
        boot_position3d_prop = _position_prop.Position3DProperty(
            'Boot Position', 'boot_position3d', self.boot_position3d)
        
        tpa_lock_1_position3d_prop = _position_prop.Position3DProperty(
            'TPA Lock 1 Position', 'tpa_lock_1_position3d', self.tpa_lock_1_position3d)
        
        tpa_lock_2_position3d_prop = _position_prop.Position3DProperty(
            'TPA Lock 2 Position', 'tpa_lock_2_position3d', self.tpa_lock_2_position3d)
        
        cpa_lock_position3d_prop = _position_prop.Position3DProperty(
            'CPA Lock Position', 'cpa_lock_position3d', self.cpa_lock_position3d)
        
        from ...ui.editor_obj.prop_grid import array_float_prop as _array_float_prop
        from ...ui.editor_obj.prop_grid import array_int_prop as _array_int_prop
        from ...ui.editor_obj.prop_grid import bool_prop as _bool_prop
        from ...ui.editor_obj.prop_grid import float_prop as _float_prop
        from ...ui.editor_obj.prop_grid import int_prop as _int_prop

        terminal_sizes_prop = _array_float_prop.ArrayFloatProperty(
            'Terminal Sizes', 'terminal_sizes', self.terminal_sizes)
        
        terminal_size_counts_prop = _array_int_prop.ArrayIntProperty(
            'Terminal Size Counts', 'terminal_size_counts', self.terminal_size_counts)
        
        centerline_prop = _float_prop.FloatProperty(
            'Pitch', 'centerline', self.centerline, min_value=0.01, 
            max_value=999.9, increment=0.01, units='mm')
        
        rows_prop = _int_prop.IntProperty(
            'Rows', 'rows', self.rows, min_value=1, max_value=999)
        
        num_pins_prop = _int_prop.IntProperty(
            'Pin Count', 'num_pins', self.num_pins, min_value=1, max_value=999)
                
        cavity_lock_prop = self._cavity_lock_propgrid
        
        terminal_prop = wxpg.PGProperty('Terminals')
        terminal_prop.AppendChild(compat_terminals_prop)
        terminal_prop.AppendChild(cavity_lock_prop)
        terminal_prop.AppendChild(terminal_sizes_prop)
        terminal_prop.AppendChild(terminal_size_counts_prop)
        terminal_prop.AppendChild(centerline_prop)
        terminal_prop.AppendChild(rows_prop)
        terminal_prop.AppendChild(num_pins_prop)

        housings_prop = wxpg.PGProperty('Housings')
        housings_prop.AppendChild(compat_housings_prop)
        accessory_parts_prop.AppendChild(housings_prop)
        
        sealing_prop = _bool_prop.BoolProperty(
            'Sealing', 'sealing', self.sealing)
        seal_type_prop = self.seal_type.propgrid
        
        seals_prop = wxpg.PGProperty('Seals')
        seals_prop.AppendChild(compat_seals_prop)
        seals_prop.AppendChild(sealing_prop)
        seals_prop.AppendChild(seal_type_prop)
        seals_prop.AppendChild(seal_position3d_prop)
        accessory_parts_prop.AppendChild(seals_prop)

        tpas_prop = wxpg.PGProperty('TPA Locks')
        tpas_prop.AppendChild(compat_tpas_prop)
        tpas_prop.AppendChild(tpa_lock_1_position3d_prop)
        tpas_prop.AppendChild(tpa_lock_2_position3d_prop)
        accessory_parts_prop.AppendChild(tpas_prop)

        cpa_lock_type_prop = self.cpa_lock_type.propgrid
        
        cpas_prop = wxpg.PGProperty('CPA Locks')
        cpas_prop.AppendChild(compat_cpas_prop)
        cpas_prop.AppendChild(cpa_lock_type_prop)
        cpas_prop.AppendChild(cpa_lock_position3d_prop)
        accessory_parts_prop.AppendChild(cpas_prop)

        boots_prop = wxpg.PGProperty('Boots')
        boots_prop.AppendChild(compat_boots_prop)
        boots_prop.AppendChild(boot_position3d_prop)
        accessory_parts_prop.AppendChild(boots_prop)

        covers_prop = wxpg.PGProperty('Covers')
        covers_prop.AppendChild(compat_covers_prop)
        covers_prop.AppendChild(cover_position3d_prop)
        accessory_parts_prop.AppendChild(covers_prop)

        from ...ui.editor_obj.prop_grid import angle_prop as _angle_prop

        angle3d_prop = _angle_prop.Angle3DProperty(
            'Housing Angle', 'angle3d', self.angle3d)
        
        part_cat.AppendChild(part_number_prop)
        part_cat.AppendChild(manufacturer_prop)
        part_cat.AppendChild(description_prop)
        part_cat.AppendChild(family_prop)
        part_cat.AppendChild(series_prop)
        part_cat.AppendChild(ip_rating_prop)
        part_cat.AppendChild(gender_prop)
        part_cat.AppendChild(color_prop)
        part_cat.AppendChild(direction_prop)
        part_cat.AppendChild(temperature_prop)
        part_cat.AppendChild(dimension_prop)
        part_cat.AppendChild(weight_prop)
        part_cat.AppendChild(resource_prop)
        part_cat.AppendChild(model3d_prop)
        part_cat.AppendChild(accessory_parts_prop)
        part_cat.AppendChild(angle3d_prop)

        return part_cat
'''