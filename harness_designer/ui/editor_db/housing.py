# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import housing as _housing


class HousingsPage(_base.EditorList):
    __table_name__ = 'housings'

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
        9: ('Gender', {'alias': 'gender_name', 'field_name': 'gender_id', 'ref_table': 'genders', 'ref_field': 'name'}),
        10: ('Direction', {'alias': 'direction_name', 'field_name': 'direction_id', 'ref_table': 'directions', 'ref_field': 'name'}),
        11: ('Cavity Lock', {'alias': 'cavity_lock_name', 'field_name': 'cavity_lock_id', 'ref_table': 'cavity_locks', 'ref_field': 'name'}),
        12: ('IP Rating', {'alias': 'ip_rating_name', 'field_name': 'ip_rating_id', 'ref_table': 'ip_ratings', 'ref_field': 'name'}),
        13: ('Seal Type', {'alias': 'seal_type_name', 'field_name': 'seal_type_id', 'ref_table': 'seal_types', 'ref_field': 'name'}),
        14: ('CPA Lock Type', {'alias': 'cpa_lock_type_name', 'field_name': 'cpa_lock_type_id', 'ref_table': 'cpa_lock_types', 'ref_field': 'name'}),
        15: ('Sealing', {'alias': 'sealing', 'field_name': 'sealing'}),
        16: ('Rows', {'alias': 'rows', 'field_name': 'rows'}),
        17: ('Pin Count', {'alias': 'num_pins', 'field_name': 'num_pins'}),
        18: ('Terminal Sizes', {'alias': 'terminal_sizes', 'field_name': 'terminal_sizes'}),
        19: ('Terminal Size Counts', {'alias': 'terminal_size_counts', 'field_name': 'terminal_size_counts'}),
        20: ('Pitch (mm)', {'alias': 'centerline', 'field_name': 'centerline'}),
        21: ('Compat CPA Locks', {'alias': 'compat_cpas', 'field_name': 'compat_cpas'}),
        22: ('Compat TPA Locks', {'alias': 'compat_tpas', 'field_name': 'compat_tpas'}),
        23: ('Compat Covers', {'alias': 'compat_covers', 'field_name': 'compat_covers'}),
        24: ('Compat Terminals', {'alias': 'compat_terminals', 'field_name': 'compat_terminals'}),
        25: ('Compat Seals', {'alias': 'compat_seals', 'field_name': 'compat_seals'}),
        26: ('Compat Housings', {'alias': 'compat_housings', 'field_name': 'compat_housings'}),
        27: ('Compat Boots', {'alias': 'compat_boots', 'field_name': 'compat_boots'}),
        28: ('Length (mm)', {'alias': 'length', 'field_name': 'length'}),
        29: ('Width (mm)', {'alias': 'width', 'field_name': 'width'}),
        30: ('Height (mm)', {'alias': 'height', 'field_name': 'height'}),
        31: ('Weight (g)', {'alias': 'weight', 'field_name': 'weight'}),
        32: ('3D Model', {'alias': 'model3d_id', 'field_name': 'model3d_id'}),
    }

    table: "_housing.HousingsTable" = None
