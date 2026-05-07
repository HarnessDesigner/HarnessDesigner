
from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import terminal as _terminal


class TerminalsPage(_base.EditorList):
    __table_name__ = 'terminals'

    __query__ = f'''\
        SELECT * FROM (
        SELECT Row_Number() OVER (ORDER BY {{sort_column}} {{sort_direction}}) AS RowNum, *
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
                plating.description AS plating_description,
                gender.name AS gender_name,
                cavity_lock.name AS cavity_lock_name,
                t.sealing AS sealing,
                t.blade_size AS blade_size,
                t.resistance AS resistance,
                t.mating_cycles AS mating_cycles,
                t.max_vibration_g AS max_vibration_g,
                t.max_current_ma AS max_current_ma,
                t.wire_size_awg_min AS wire_size_awg_min,
                t.wire_size_awg_max AS wire_size_awg_max,
                t.wire_size_dia_min AS wire_size_dia_min,
                t.wire_size_dia_max AS wire_size_dia_max,
                t.wire_size_cross_min AS wire_size_cross_min,
                t.wire_size_cross_max AS wire_size_cross_max,
                t.length AS length,
                t.width AS width,
                t.height AS height,
                t.weight AS weight,
                t.compat_housings AS compat_housings,
                t.compat_seals AS compat_seals,
                t.model3d_id AS model3d_id,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN platings AS plating ON plating.id = t.plating_id
            LEFT JOIN genders AS gender ON gender.id = t.gender_id
            LEFT JOIN cavity_locks AS cavity_lock ON cavity_lock.id = t.cavity_lock_id
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
        9: ('Plating', 'plating_description'),
        10: ('Gender', 'gender_name'),
        11: ('Cavity Lock', 'cavity_lock_name'),
        12: ('Sealing', 'sealing'),
        13: ('Blade Size (mm)', 'blade_size'),
        14: ('Resistance (Ω)', 'resistance'),
        15: ('Mating Cycles', 'mating_cycles'),
        16: ('Max Vibration (G)', 'max_vibration_g'),
        17: ('Max Current (ma)', 'max_current_ma'),
        18: ('Wire AWG (min)', 'wire_size_awg_min'),
        19: ('Wire AWG (max)', 'wire_size_awg_max'),
        20: ('Wire Dia (mm)(min)', 'wire_size_dia_min'),
        21: ('Wire Dia (mm)(max)', 'wire_size_dia_max'),
        22: ('Wire Cross (mm²)(min)', 'wire_size_cross_min'),
        23: ('Wire Cross (mm²)(max)', 'wire_size_cross_max'),
        24: ('Length (mm)', 'length'),
        25: ('Width (mm)', 'width'),
        26: ('Height (mm)', 'height'),
        27: ('Weight (g)', 'weight'),
        28: ('Compat Housings', 'compat_housings'),
        29: ('Compat Seals', 'compat_seals'),
        30: ('3D Model', 'model3d_id'),
    }
    table: "_terminal.TerminalsTable" = None
