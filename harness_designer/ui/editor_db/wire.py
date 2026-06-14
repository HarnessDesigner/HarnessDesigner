# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import wire as _wire


class WiresPage(_base.EditorList):
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'wires'

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
        9: ('Jacket Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        10: ('Stripe Color', {'alias': 'stripe_color_name', 'field_name': 'stripe_color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        11: ('Core Material', {'alias': 'core_material_description', 'field_name': 'core_material_id', 'ref_table': 'platings', 'ref_field': 'description'}),
        12: ('Conductor Count', {'alias': 'num_conductors', 'field_name': 'num_conductors'}),
        13: ('Shielded', {'alias': 'shielded', 'field_name': 'shielded'}),
        14: ('TPI', {'alias': 'tpi', 'field_name': 'tpi'}),
        15: ('Wire Dia (mm)', {'alias': 'wire_size_dia', 'field_name': 'wire_size_dia'}),
        16: ('Wire Cross (mm²)', {'alias': 'wire_size_cross', 'field_name': 'wire_size_cross'}),
        17: ('Wire AWG', {'alias': 'wire_size_awg', 'field_name': 'wire_size_awg'}),
        18: ('Outside Dia (mm)', {'alias': 'od_mm', 'field_name': 'od_mm'}),
        19: ('Weight (g/km)', {'alias': 'weight_1km', 'field_name': 'weight_1km'}),
        20: ('Resistance (Ω/km)', {'alias': 'resistance_1km', 'field_name': 'resistance_1km'}),
        21: ('Volts (V)', {'alias': 'volts', 'field_name': 'volts'}),
        22: ('Strands', {'alias': 'strands', 'field_name': 'strands'}),
    }

    table: "_wire.WiresTable" = None
