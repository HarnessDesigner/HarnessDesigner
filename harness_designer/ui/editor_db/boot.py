# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import boot as _boot


class BootsPage(_base.EditorList):
    __table_name__ = 'boots'

    column_mapping = {
        0: ('DB ID', {'alias': 'id', 'field_name': 'id'}, True),
        1: ('Part Number', {'alias': 'part_number', 'field_name': 'part_number'}, True),
        2: ('Description', {'alias': 'description', 'field_name': 'description'}),
        3: ('Manufacturer', {'alias': 'mfg_name', 'field_name': 'mfg_id', 'ref_table': 'manufacturers', 'ref_field': 'name'}),
        4: ('Family', {'alias': 'family_name', 'field_name': 'family_id', 'ref_table': 'families', 'ref_field': 'name'}),
        5: ('Series', {'alias': 'series_name', 'field_name': 'series_id', 'ref_table': 'series', 'ref_field': 'name'}),
        6: ('Color', {'alias': 'color_name', 'field_name': 'color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        7: ('Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        8: ('Direction', {'alias': 'direction_name', 'field_name': 'direction_id', 'ref_table': 'directions', 'ref_field': 'name'}),
        9: ('Temperature (min)', {'alias': 'min_temp_name', 'field_name': 'min_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        10: ('Temperature (max)', {'alias': 'max_temp_name', 'field_name': 'max_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        11: ('Protections', {'alias': 'protection_name', 'field_name': 'protection_id', 'ref_table': 'protections', 'ref_field': 'name'}),
        12: ('Diameter (mm)(min)', {'alias': 'min_dia', 'field_name': 'min_dia'}),
        13: ('Diameter (mm)(max)', {'alias': 'max_dia', 'field_name': 'max_dia'}),
        14: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        15: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        16: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        17: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        18: ('Compat Housings', {'alias': 'compat_housings', 'field_name': 'compat_housings'}),
        19: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_boot.BootsTable" = None
