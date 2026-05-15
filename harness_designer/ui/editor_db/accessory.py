# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import accessory as _accessory


class AccessoriesPage(_base.EditorList):
    _has_model_3d = False

    __table_name__ = 'accessories'
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
            material.name AS material_name,
            t.length AS length,
            t.width AS width,
            t.height AS height,
            t.weight AS weight,
            t.image_id AS image_id
        FROM {__table_name__} AS t
        LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
        LEFT JOIN families AS family ON family.id = t.family_id
        LEFT JOIN series AS series ON series.id = t.series_id
        LEFT JOIN colors AS color ON color.id = t.color_id
        LEFT JOIN materials AS material ON material.id = t.material_id
        )
    ) WHERE RowNum BETWEEN {{start_row}} AND {{end_row}};
    '''

    column_mapping = {
        0: ('DB ID', 'id', True),
        1: ('Part Number', 'part_number', True),
        2: ('Description', 'description'),
        3: ('Manufacturer', 'mfg_name'),
        4: ('Family', 'family_name'),
        5: ('Series', 'series_name'),
        6: ('Color', 'color_name'),
        7: ('Material', 'material_name'),
        8: ('Length (mm)', 'length'),
        9: ('Width (mm)', 'width'),
        10: ('Height (mm)', 'height'),
        11: ('Weight (g)', 'weight'),
    }

    table: "_accessory.AccessoriesTable" = None
