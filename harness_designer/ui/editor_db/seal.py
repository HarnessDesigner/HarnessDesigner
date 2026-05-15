# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import seal as _seal


class SealsPage(_base.EditorList):
    __table_name__ = 'seals'
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
                type.name AS type_name,
                t.hardness AS hardness,
                t.lubricant AS lubricant,
                t.length AS length,
                t.width AS width,
                t.height AS height,
                t.weight AS weight,
                t.o_dia AS o_dia,
                t.i_dia AS i_dia,
                t.wire_size_dia_min AS wire_size_dia_min,
                t.wire_size_dia_max AS wire_size_dia_max,
                t.wire_size_cross_min AS wire_size_cross_min,
                t.wire_size_cross_max AS wire_size_cross_max,
                t.wire_size_awg_min AS wire_size_awg_min,
                t.wire_size_awg_max AS wire_size_awg_max,
                t.compat_housings AS compat_housings,
                t.compat_terminals AS compat_terminals,
                t.model3d_id AS model3d_id,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN seal_types AS type ON type.id = t.type_id
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
        7: ('Temperature (min)', 'min_temp_name'),
        8: ('Temperature (max)', 'max_temp_name'),
        9: ('Type', 'type_name'),
        10: ('Hardness (shore)', 'hardness'),
        11: ('Lubricant', 'lubricant'),
        12: ('Length (mm)', 'length'),
        13: ('Width (mm)', 'width'),
        14: ('Height (mm)', 'height'),
        15: ('Weight (g)', 'weight'),
        16: ('Outside Diameter (mm)', 'o_dia'),
        17: ('Inside Diameter (mm)', 'i_dia'),
        18: ('Wire AWG (min)', 'wire_size_awg_min'),
        19: ('Wire AWG (max)', 'wire_size_awg_max'),
        20: ('Wire Dia (mm)(min)', 'wire_size_dia_min'),
        21: ('Wire Dia (mm)(max)', 'wire_size_dia_max'),
        22: ('Wire Cross (mm²)(min)', 'wire_size_cross_min'),
        23: ('Wire Cross (mm²)(max)', 'wire_size_cross_max',),
        24: ('Compat Housings', 'compat_housings'),
        25: ('Compat Terminals', 'compat_terminals'),
        26: ('3D Model', 'model3d_id'),
    }
    table: "_seal.SealsTable" = None
