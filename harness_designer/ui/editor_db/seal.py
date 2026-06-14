# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import seal as _seal


class SealsPage(_base.EditorList):
    __table_name__ = 'seals'

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
        9: ('Type', {'alias': 'type_name', 'field_name': 'type_id', 'ref_table': 'seal_types', 'ref_field': 'name'}),
        10: ('Hardness (shore)', {'alias': 'hardness', 'field_name': 'hardness'}),
        11: ('Lubricant', {'alias': 'lubricant', 'field_name': 'lubricant'}),
        12: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        13: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        14: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        15: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        16: ('Outside Diameter (mm)', {'alias': 'o_dia', 'field_name': 'o_dia'}),
        17: ('Inside Diameter (mm)', {'alias': 'i_dia', 'field_name': 'i_dia'}),
        18: ('Wire AWG (min)', {'alias': 'wire_size_awg_min', 'field_name': 'wire_size_awg_min'}),
        19: ('Wire AWG (max)', {'alias': 'wire_size_awg_max', 'field_name': 'wire_size_awg_max'}),
        20: ('Wire Dia (mm)(min)', {'alias': 'wire_size_dia_min', 'field_name': 'wire_size_dia_min'}),
        21: ('Wire Dia (mm)(max)', {'alias': 'wire_size_dia_max', 'field_name': 'wire_size_dia_max'}),
        22: ('Wire Cross (mm²)(min)', {'alias': 'wire_size_cross_min', 'field_name': 'wire_size_cross_min'}),
        23: ('Wire Cross (mm²)(max)', {'alias': 'wire_size_cross_max', 'field_name': 'wire_size_cross_max'}),
        24: ('Compat Housings', {'alias': 'compat_housings', 'field_name': 'compat_housings'}),
        25: ('Compat Terminals', {'alias': 'compat_terminals', 'field_name': 'compat_terminals'}),
        26: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_seal.SealsTable" = None
