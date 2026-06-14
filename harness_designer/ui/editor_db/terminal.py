# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import terminal as _terminal


class TerminalsPage(_base.EditorList):
    __table_name__ = 'terminals'

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
        9: ('Plating', {'alias': 'plating_description', 'field_name': 'plating_id', 'ref_table': 'platings', 'ref_field': 'description'}),
        10: ('Gender', {'alias': 'gender_name', 'field_name': 'gender_id', 'ref_table': 'genders', 'ref_field': 'name'}),
        11: ('Cavity Lock', {'alias': 'cavity_lock_name', 'field_name': 'cavity_lock_id', 'ref_table': 'cavity_locks', 'ref_field': 'name'}),
        12: ('Sealing', {'alias': 'sealing', 'field_name': 'sealing'}),
        13: ('Blade Size (mm)', {'alias': 'blade_size', 'field_name': 'blade_size'}),
        14: ('Resistance (Ω)', {'alias': 'resistance', 'field_name': 'resistance'}),
        15: ('Mating Cycles', {'alias': 'mating_cycles', 'field_name': 'mating_cycles'}),
        16: ('Max Vibration (G)', {'alias': 'max_vibration_g', 'field_name': 'max_vibration_g'}),
        17: ('Max Current (ma)', {'alias': 'max_current_ma', 'field_name': 'max_current_ma'}),
        18: ('Wire AWG (min)', {'alias': 'wire_size_awg_min', 'field_name': 'wire_size_awg_min'}),
        19: ('Wire AWG (max)', {'alias': 'wire_size_awg_max', 'field_name': 'wire_size_awg_max'}),
        20: ('Wire Dia (mm)(min)', {'alias': 'wire_size_dia_min', 'field_name': 'wire_size_dia_min'}),
        21: ('Wire Dia (mm)(max)', {'alias': 'wire_size_dia_max', 'field_name': 'wire_size_dia_max'}),
        22: ('Wire Cross (mm²)(min)', {'alias': 'wire_size_cross_min', 'field_name': 'wire_size_cross_min'}),
        23: ('Wire Cross (mm²)(max)', {'alias': 'wire_size_cross_max', 'field_name': 'wire_size_cross_max'}),
        24: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        25: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        26: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        27: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        28: ('Compat Housings', {'alias': 'compat_housings', 'field_name': 'compat_housings'}),
        29: ('Compat Seals', {'alias': 'compat_seals', 'field_name': 'compat_seals'}),
        30: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_terminal.TerminalsTable" = None
