# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import splice as _splice


class SplicesPage(_base.EditorList):
    __table_name__ = 'splices'

    column_mapping = {
        0: ('DB ID', {'alias': 'id', 'field_name': 'id'}, True),
        1: ('Part Number', {'alias': 'part_number', 'field_name': 'part_number'}, True),
        2: ('Description', {'alias': 'description', 'field_name': 'description'}),
        3: ('Manufacturer', {'alias': 'mfg_name', 'field_name': 'mfg_id', 'ref_table': 'manufacturers', 'ref_field': 'name'}),
        4: ('Family', {'alias': 'family_name', 'field_name': 'family_id', 'ref_table': 'families', 'ref_field': 'name'}),
        5: ('Series', {'alias': 'series_name', 'field_name': 'series_id', 'ref_table': 'series', 'ref_field': 'name'}),
        6: ('Color', {'alias': 'color_name', 'field_name': 'color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        7: ('Temperature (min)', {'alias': 'min_temp_name', 'field_name': 'min_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        8: ('Temperature (max)', {'alias': 'max_temp_name', 'field_name': 'max_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        9: ('Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        10: ('Plating', {'alias': 'plating_description', 'field_name': 'plating_id', 'ref_table': 'platings', 'ref_field': 'description'}),
        11: ('Type', {'alias': 'type_name', 'field_name': 'type_id', 'ref_table': 'splice_types', 'ref_field': 'name'}),
        12: ('Diameter (mm)(min)', {'alias': 'min_dia', 'field_name': 'min_dia'}),
        13: ('Diameter (mm)(max)', {'alias': 'max_dia', 'field_name': 'max_dia'}),
        14: ('Resistance (Ω)', {'alias': 'resistance', 'field_name': 'resistance'}),
        15: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        16: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        17: ('Wire AWG (min)', {'alias': 'wire_size_awg_min', 'field_name': 'wire_size_awg_min'}),
        18: ('Wire AWG (max)', {'alias': 'wire_size_awg_max', 'field_name': 'wire_size_awg_max'}),
        19: ('Wire Dia (mm)(min)', {'alias': 'wire_size_dia_min', 'field_name': 'wire_size_dia_min'}),
        20: ('Wire Dia (mm)(max)', {'alias': 'wire_size_dia_max', 'field_name': 'wire_size_dia_max'}),
        21: ('Wire Cross (mm²)(min)', {'alias': 'wire_size_cross_min', 'field_name': 'wire_size_cross_min'}),
        22: ('Wire Cross (mm²)(max)', {'alias': 'wire_size_cross_max', 'field_name': 'wire_size_cross_max'}),
        23: ('Wire Count', {'alias': 'num_wires', 'field_name': 'num_wires'}),
        24: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_splice.SplicesTable" = None
