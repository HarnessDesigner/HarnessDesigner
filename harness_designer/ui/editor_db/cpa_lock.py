# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import cpa_lock as _cpa_lock


class CPALocksPage(_base.EditorList):
    __table_name__ = 'cpa_locks'

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
        9: ('Type', {'alias': 'type_name', 'field_name': 'type_id', 'ref_table': 'cpa_lock_types', 'ref_field': 'name'}),
        10: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        11: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        12: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        13: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        14: ('Compat Housings', {'alias': 'compat_housings', 'field_name': 'compat_housings'}),
        15: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_cpa_lock.CPALocksTable" = None
