# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import bundle_cover as _bundle_cover


class BundleCoversPage(_base.EditorList):
    """Represent a bundle covers page in :mod:`harness_designer.ui.editor_db.bundle_cover`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _has_model_3d = False
    _has_image = False

    __table_name__ = 'bundle_covers'
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
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                shrink_temp.name AS shrink_temp_name,
                material.name AS material_name,
                protection.name AS protection_name,
                t.rigidity AS rigidity,
                t.shrink_ratio AS shrink_ratio,
                t.wall AS wall,
                t.min_dia AS min_dia,
                t.max_dia AS max_dia,
                t.adhesive_ids AS adhesive_ids,
                t.weight AS weight
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN materials AS material ON material.id = t.material_id
            LEFT JOIN temperatures AS shrink_temp ON shrink_temp.id = t.shrink_temp_id
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
        7: ('Temperature (min)', 'min_temp_name'),
        8: ('Temperature (max)', 'max_temp_name'),
        9: ('Shrink Temperature', 'shrink_temp_name'),
        10: ('Material', 'material_name'),
        11: ('Protections', 'protection_name'),
        12: ('Rigidity', 'rigidity'),
        13: ('Shrink Ratio', 'shrink_ratio'),
        14: ('Wall', 'wall'),
        15: ('Diameter (mm)(min)', 'min_dia'),
        16: ('Diameter (mm)(max)', 'max_dia'),
        17: ('Adhesive Codes', 'adhesive_ids'),
        18: ('Weight (g/m)', 'weight'),
    }
    table: "_bundle_cover.BundleCoversTable" = None
