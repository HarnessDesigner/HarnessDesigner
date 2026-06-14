# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import wire_marker as _wire_marker


class WireMarkersPage(_base.EditorList):
    _has_model_3d = False

    __table_name__ = 'wire_markers'

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
        9: ('Diameter (mm)(min)', {'alias': 'min_dia', 'field_name': 'min_diameter'}),
        10: ('Diameter (mm)(max)', {'alias': 'max_dia', 'field_name': 'max_diameter'}),
        11: ('Wire AWG (min)', {'alias': 'wire_size_awg_min', 'field_name': 'wire_size_awg_min'}),
        12: ('Wire AWG (max)', {'alias': 'wire_size_awg_max', 'field_name': 'wire_size_awg_max'}),
        13: ('Wire Dia (mm)(min)', {'alias': 'wire_size_dia_min', 'field_name': 'wire_size_dia_min'}),
        14: ('Wire Dia (mm)(max)', {'alias': 'wire_size_dia_max', 'field_name': 'wire_size_dia_max'}),
        15: ('Wire Cross (mm²)(min)', {'alias': 'wire_size_cross_min', 'field_name': 'wire_size_cross_min'}),
        16: ('Wire Cross (mm²)(max)', {'alias': 'wire_size_cross_max', 'field_name': 'wire_size_cross_max'}),
        17: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        18: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        19: ('Has Label', {'alias': 'has_label', 'field_name': 'has_label'}),
    }

    table: "_wire_marker.WireMarkersTable" = None
