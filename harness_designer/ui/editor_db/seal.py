from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import seal as _seal


class SealsPage(_base.EditorList):
    __table_name__ = 'seals'
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
                type.name AS type_name,
                t.hardness,
                t.lubricant,
                t.length,
                t.width,
                t.height,
                t.weight,
                t.o_dia,
                t.i_dia,
                t.wire_size_dia_min,
                t.wire_size_dia_max,
                t.wire_size_cross_min,
                t.wire_size_cross_max,
                t.wire_size_awg_min,
                t.wire_size_awg_max,
                t.compat_housings,
                t.compat_terminals,
                t.model3d_id,
                t.image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN seal_types AS type ON type.id = t.type_id
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
        9: 'Type',
        10: 'Hardness (shore)',
        11: 'Lubricant',
        12: 'Length (mm)',
        13: 'Width (mm)',
        14: 'Height (mm)',
        15: 'Weight (g)',
        16: 'Outside Diameter (mm)',
        17: 'Inside Diameter (mm)',
        18: 'Wire AWG (min)',
        19: 'Wire AWG (max)',
        20: 'Wire Dia (mm)(min)',
        21: 'Wire Dia (mm)(max)',
        22: 'Wire Cross (mm²)(min)',
        23: 'Wire Cross (mm²)(max)',
        24: 'Compat Housings',
        25: 'Compat Terminals'
    }
    table: "_seal.SealsTable" = None
