# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import housing as _housing


class HousingsPage(_base.EditorList):
    __table_name__ = 'housings'
    __query__ = f'''\
        SELECT * FROM (
        SELECT Row_Number() OVER (ORDER BY {{sort_clause}}) AS RowNum, *
        FROM (
            SELECT
                t.id AS id,
                t.part_number AS part_number,
                t.description AS description,
                mfg.name AS mfg_name,
                family.name AS family_name,
                series.name AS series_name,
                color.name AS color_name,
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                gender.name AS gender_name,
                direction.name AS direction_name,
                cavity_lock.name AS cavity_lock_name,
                ip_rating.name AS ip_rating_name,
                seal_type.name AS seal_type_name,
                cpa_lock_type.name AS cpa_lock_type_name,
                t.sealing AS sealing,
                t.rows AS rows,
                t.num_pins AS num_pins,
                t.terminal_sizes AS terminal_sizes,
                t.terminal_size_counts AS terminal_size_counts,
                t.centerline AS centerline,
                t.compat_cpas AS compat_cpas,
                t.compat_tpas AS compat_tpas,
                t.compat_covers AS compat_covers,
                t.compat_terminals AS compat_terminals,
                t.compat_seals AS compat_seals,
                t.compat_housings AS compat_housings,
                t.compat_boots AS compat_boots,
                t.length AS length,
                t.width AS width,
                t.height AS height,
                t.weight AS weight,
                t.model3d_id AS model3d_id,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN genders AS gender ON gender.id = t.gender_id
            LEFT JOIN directions AS direction ON direction.id = t.direction_id
            LEFT JOIN cavity_locks AS cavity_lock ON cavity_lock.id = t.cavity_lock_id
            LEFT JOIN ip_ratings AS ip_rating ON ip_rating.id = t.ip_rating_id
            LEFT JOIN seal_types AS seal_type ON seal_type.id = t.seal_type_id
            LEFT JOIN cpa_lock_types AS cpa_lock_type ON cpa_lock_type.id = t.cpa_lock_type_id
            )
        ) WHERE RowNum BETWEEN {{start_row}} AND {{end_row}};
        '''

    column_mapping = {
        0: ('DB ID', 'id'),
        1: ('Part Number', 'part_number'),
        2: ('Description', 'description'),
        3: ('Manufacturer', 'mfg_name'),
        4: ('Family', 'family_name'),
        5: ('Series', 'series_name'),
        6: ('Color', 'color_name'),
        7: ('Temperature (min)', 'min_temp_name'),
        8: ('Temperature (max)', 'max_temp_name'),
        9: ('Gender', 'gender_name'),
        10: ('Direction', 'direction_name'),
        11: ('Cavity Lock', 'cavity_lock_name'),
        12: ('IP Rating', 'ip_rating_name'),
        13: ('Seal Type', 'seal_type_name'),
        14: ('CPA Lock Type', 'cpa_lock_type_name'),
        15: ('Sealing', 'sealing'),
        16: ('Rows', 'rows'),
        17: ('Pin Count', 'num_pins'),
        18: ('Terminal Sizes', 'terminal_sizes'),
        19: ('Terminal Size Counts', 'terminal_size_counts'),
        20: ('Pitch (mm)', 'centerline'),
        21: ('Compat CPA Locks', 'compat_cpas'),
        22: ('Compat TPA Locks', 'compat_tpas'),
        23: ('Compat Covers', 'compat_covers'),
        24: ('Compat Terminals', 'compat_terminals'),
        25: ('Compat Seals', 'compat_seals'),
        26: ('Compat Housings', 'compat_housings'),
        27: ('Compat Boots', 'compat_boots'),
        28: ('Length (mm)', 'length'),
        29: ('Width (mm)', 'width'),
        30: ('Height (mm)', 'height'),
        31: ('Weight (g)', 'weight'),
        32: ('3D Model', 'model3d_id')
    }
    table: "_housing.HousingsTable" = None
