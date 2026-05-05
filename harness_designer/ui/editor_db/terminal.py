
from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import terminal as _terminal


class TerminalsPage(_base.EditorList):
    __table_name__ = 'terminals'

    __query__ = f'''\
        SELECT * FROM (
            SELECT
                Row_Number() OVER (ORDER BY {{sort_column}} {{sort_direction}}) AS RowNum,
                t.id,
                t.part_number,
                t.description,
                mfg.name AS mfg_name,
                family.name AS family_name,
                series.name AS series_name,
                color.name AS color_name,
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                plating.description AS plating_description,
                gender.name AS gender_name,
                cavity_lock.name AS cavity_lock_name,
                t.sealing,
                t.blade_size,
                t.resistance,
                t.mating_cycles,
                t.max_vibration_g,
                t.max_current_ma,
                t.wire_size_awg_min,
                t.wire_size_awg_max,
                t.wire_size_dia_min,
                t.wire_size_dia_max,
                t.wire_size_cross_min,
                t.wire_size_cross_max,
                t.length,
                t.width,
                t.height,
                t.weight,
                t.compat_housings,
                t.compat_seals,
                t.model3d_id,
                t.image_id
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
        ) t2 WHERE RowNum = {{row}};
        '''

    column_mapping = {
        0: 'DB ID',
        1: 'Part Number',
        2: 'Description',
        3: 'Manufacturer',
        4: 'Family',
        5: 'Series',
        6: 'Color',
        7: 'Temperature (min)',
        8: 'Temperature (max)',
        9: 'Plating',
        10: 'Gender',
        11: 'Cavity Lock',
        12: 'Sealing',
        13: 'Blade Size (mm)',
        14: 'Resistance (Ω)',
        15: 'Mating Cycles',
        16: 'Max Vibration (G)',
        17: 'Max Current (ma)',
        18: 'Wire AWG (min)',
        19: 'Wire AWG (max)',
        20: 'Wire Dia (mm)(min)',
        21: 'Wire Dia (mm)(max)',
        22: 'Wire Cross (mm²)(min)',
        23: 'Wire Cross (mm²)(max)',
        24: 'Length (mm)',
        25: 'Width (mm)',
        26: 'Height (mm)',
        27: 'Weight (g)',
        28: 'Compat Housings',
        29: 'Compat Seals'
    }
    table: "_terminal.TerminalsTable" = None
