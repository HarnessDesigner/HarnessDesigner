from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import transition as _transition


class TransitionsPage(_base.EditorList):
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'transitions'
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
                material.name AS material_name,
                shape.name AS shape_name,
                protection.name AS protection_name,
                t.branch_count,
                t.adhesive_ids,
                t.weight,
                t.image_id,
                (SELECT json_group_array(json_object(
                    'id', tb.id,
                    'idx', tb.idx,
                    'bulb_offset', tb.bulb_offset,
                    'bulb_length', tb.bulb_length,
                    'min_dia', tb.min_dia,
                    'max_dia', tb.max_dia,
                    'length', tb.length,
                    'offset', tb.offset,
                    'angle', tb.angle,
                    'flange_height', tb.flange_height,
                    'flange_width', tb.flange_width
                ))
                FROM transition_branches AS tb
                WHERE tb.transition_id = t.id) AS branches
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN materials AS material ON material.id = t.material_id
            LEFT JOIN shapes AS shape ON shape.id = t.shape_id
            LEFT JOIN protections AS protection ON protection.id = t.protection_id
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
        9: 'Material',
        10: 'Shape',
        11: 'Protections',
        12: 'Branch Count',
        13: 'Adhesive Codes',
        14: 'Weight (g)'
    }
    table: "_transition.TransitionsTable" = None
