# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import transition as _transition


class TransitionsPage(_base.EditorList):
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'transitions'

    column_mapping = {
        0: ('DB ID', {'alias': 'id', 'field_name': 'id'}, True),
        1: ('Part Number', {'alias': 'part_number', 'field_name': 'part_number'}, True),
        2: ('Description', {'alias': 'description', 'field_name': 'description'}),
        3: ('Manufacturer', {'alias': 'mfg_name', 'field_name': 'mfg_id', 'ref_table': 'manufacturers', 'ref_field': 'name'}),
        4: ('Family', {'alias': 'family_name', 'field_name': 'family_id', 'ref_table': 'families', 'ref_field': 'name'}),
        5: ('Series', {'alias': 'series_name', 'field_name': 'series_id', 'ref_table': 'series', 'ref_field': 'name'}),
        6: ('Color', {'alias': 'color_name', 'field_name': 'color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        7: ('Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        8: ('Shape', {'alias': 'shape_name', 'field_name': 'shape_id', 'ref_table': 'shapes', 'ref_field': 'name'}),
        9: ('Protections', {'alias': 'protection_name', 'field_name': 'protection_id', 'ref_table': 'protections', 'ref_field': 'name'}),
        10: ('Branch Count', {'alias': 'branch_count', 'field_name': 'branch_count'}),
        11: ('Adhesive Codes', {'alias': 'adhesive_ids', 'field_name': 'adhesive_ids'}),
        12: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
    }

    table: "_transition.TransitionsTable" = None
