from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import tpa_lock as _tpa_lock


class TPALocksPage(_base.EditorList):
    __table_name__ = 'tpa_locks'
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
                t.lock_type,
                t.length,
                t.width,
                t.height,
                t.weight,
                t.compat_housings,
                t.model3d_id,
                t.image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
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
        10: 'Length (mm)',
        11: 'Width (mm)',
        12: 'Height (mm)',
        13: 'Weight (g)',
        14: 'Compat Housings'
    }
    table: "_tpa_lock.TPALocksTable" = None
