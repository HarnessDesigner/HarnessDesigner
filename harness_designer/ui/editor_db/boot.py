# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import boot as _boot


class BootsPage(_base.EditorList):
    """Represent a boots page in :mod:`harness_designer.ui.editor_db.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'boots'
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
                direction.name AS direction_name,
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                protection.name AS protection_name,
                t.min_dia AS min_dia,
                t.max_dia AS max_dia,
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
            LEFT JOIN materials AS material ON material.id = t.material_id
            LEFT JOIN directions AS direction ON direction.id = t.direction_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN protections AS protection ON protection.id = t.protection_id
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
        8: ('Direction', 'direction_name'),
        9: ('Temperature (min)', 'min_temp_name'),
        10: ('Temperature (max)', 'max_temp_name'),
        11: ('Protections', 'protection_name'),
        12: ('Diameter (mm)(min)', 'min_dia'),
        13: ('Diameter (mm)(max)', 'max_dia'),
        14: ('Length (mm)', 'length'),
        15: ('Width (mm)', 'width'),
        16: ('Height (mm)', 'height'),
        17: ('Weight (g)', 'weight'),
        18: ('Compat Housings', 'compat_housings'),
        19: ('3D Model', 'model3d_id'),
    }

    table: "_boot.BootsTable" = None
