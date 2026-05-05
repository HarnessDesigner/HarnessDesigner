from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import wire_marker as _wire_marker


class WireMarkersPage(_base.EditorList):
    _has_model_3d = False

    __table_name__ = 'wire_markers'
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
                t.min_diameter,
                t.max_diameter,
                t.wire_size_awg_min,
                t.wire_size_awg_max,
                t.wire_size_dia_min,
                t.wire_size_dia_max,
                t.wire_size_cross_min,
                t.wire_size_cross_max,
                t.length,
                t.weight,
                t.has_label,
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
        9: 'Diameter (mm)(min)',
        10: 'Diameter (mm)(max)',
        11: 'Wire AWG (min)',
        12: 'Wire AWG (max)',
        13: 'Wire Dia (mm)(min)',
        14: 'Wire Dia (mm)(max)',
        15: 'Wire Cross (mm²)(min)',
        16: 'Wire Cross (mm²)(max)',
        17: 'Length (mm)',
        18: 'Weight (g)',
        19: 'Has Label'
    }
    table: "_wire_marker.WireMarkersTable" = None
