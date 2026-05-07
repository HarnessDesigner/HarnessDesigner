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
                material.name AS material_name,
                shape.name AS shape_name,
                protection.name AS protection_name,
                t.branch_count AS branch_count,
                t.adhesive_ids AS adhesive_ids,
                t.weight AS weight,
                t.image_id AS image_id
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
        7: ('Material', 'material_name'),
        8: ('Shape', 'shape_name'),
        9: ('Protections', 'protection_name'),
        10: ('Branch Count', 'branch_count'),
        11: ('Adhesive Codes', 'adhesive_ids'),
        12: ('Weight (g)', 'weight')
    }

    table: "_transition.TransitionsTable" = None
