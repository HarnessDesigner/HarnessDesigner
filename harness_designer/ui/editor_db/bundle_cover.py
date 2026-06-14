# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import bundle_cover as _bundle_cover


class BundleCoversPage(_base.EditorList):
    _has_model_3d = False
    _has_image = False

    __table_name__ = 'bundle_covers'

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
        9: ('Shrink Temperature', {'alias': 'shrink_temp_name', 'field_name': 'shrink_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        10: ('Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        11: ('Protections', {'alias': 'protection_name', 'field_name': 'protection_id', 'ref_table': 'protections', 'ref_field': 'name'}),
        12: ('Rigidity', {'alias': 'rigidity', 'field_name': 'rigidity'}),
        13: ('Shrink Ratio', {'alias': 'shrink_ratio', 'field_name': 'shrink_ratio'}),
        14: ('Wall', {'alias': 'wall', 'field_name': 'wall'}),
        15: ('Diameter (mm)(min)', {'alias': 'min_dia', 'field_name': 'min_dia'}),
        16: ('Diameter (mm)(max)', {'alias': 'max_dia', 'field_name': 'max_dia'}),
        17: ('Adhesive Codes', {'alias': 'adhesive_ids', 'field_name': 'adhesive_ids'}),
        18: ('Weight (g/m)', {'alias': 'weight', 'field_name': 'weight'}),
    }

    table: "_bundle_cover.BundleCoversTable" = None
