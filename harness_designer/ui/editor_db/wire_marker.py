# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import wire_marker as _wire_marker


class WireMarkersPage(_base.EditorList):
    _has_model_3d = False

    __table_name__ = 'wire_markers'
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
                t.min_diameter AS min_dia,
                t.max_diameter AS max_dia,
                t.wire_size_awg_min AS wire_size_awg_min,
                t.wire_size_awg_max AS wire_size_awg_max,
                t.wire_size_dia_min AS wire_size_dia_min,
                t.wire_size_dia_max AS wire_size_dia_max,
                t.wire_size_cross_min AS wire_size_cross_min,
                t.wire_size_cross_max AS wire_size_cross_max,
                t.length AS length,
                t.weight AS weight,
                t.has_label AS has_label,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
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
        9: ('Diameter (mm)(min)', 'min_dia'),
        10: ('Diameter (mm)(max)', 'max_dia'),
        11: ('Wire AWG (min)', 'wire_size_awg_min'),
        12: ('Wire AWG (max)', 'wire_size_awg_max'),
        13: ('Wire Dia (mm)(min)', 'wire_size_dia_min'),
        14: ('Wire Dia (mm)(max)', 'wire_size_dia_max'),
        15: ('Wire Cross (mm²)(min)', 'wire_size_cross_min'),
        16: ('Wire Cross (mm²)(max)', 'wire_size_cross_max'),
        17: ('Length (mm)', 'length'),
        18: ('Weight (g)', 'weight'),
        19: ('Has Label', 'has_label')
    }
    table: "_wire_marker.WireMarkersTable" = None
