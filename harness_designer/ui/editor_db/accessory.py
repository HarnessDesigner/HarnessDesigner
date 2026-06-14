# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import accessory as _accessory


class AccessoriesPage(_base.EditorList):
    _has_model_3d = False

    __table_name__ = 'accessories'

    column_mapping = {
        0: ('DB ID', {'alias': 'id', 'field_name': 'id'}, True),
        1: ('Part Number', {'alias': 'part_number', 'field_name': 'part_number'}, True),
        2: ('Description', {'alias': 'description', 'field_name': 'description'}),
        3: ('Manufacturer', {'alias': 'mfg_name', 'field_name': 'mfg_id', 'ref_table': 'manufacturers', 'ref_field': 'name'}),
        4: ('Family', {'alias': 'family_name', 'field_name': 'family_id', 'ref_table': 'families', 'ref_field': 'name'}),
        5: ('Series', {'alias': 'series_name', 'field_name': 'series_id', 'ref_table': 'series', 'ref_field': 'name'}),
        6: ('Color', {'alias': 'color_name', 'field_name': 'color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        7: ('Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        8: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        9: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        10: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        11: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
    }

    table: "_accessory.AccessoriesTable" = None
