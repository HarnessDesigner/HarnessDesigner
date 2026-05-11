# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import cover as _cover


class CoversPage(_base.EditorList):
    __table_name__ = 'covers'
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
                direction.name AS direction_name,
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                t.length AS length,
                t.width AS width,
                t.height AS height,
                t.weight AS weight,
                t.compat_housings AS compat_housings, 
                t.model3d_id AS model3d_id,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN directions AS direction ON direction.id = t.direction_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
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
        7: ('Direction', 'direction_name'),
        8: ('Temperature (min)', 'min_temp_name'),
        9: ('Temperature (max)', 'max_temp_name'),
        10: ('Length (mm)', 'length'),
        11: ('Width (mm)', 'width'),
        12: ('Height (mm)', 'height'),
        13: ('Weight (g)', 'weight'),
        14: ('Compat Housings', 'compat_housings'),
        15: ('3D Model', 'model3d_id'),
    }
    table: "_cover.CoversTable" = None
