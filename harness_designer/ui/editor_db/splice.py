# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import splice as _splice


class SplicesPage(_base.EditorList):
    __table_name__ = 'splices'
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
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                material.name AS material_name,
                plating.description AS plating_description,
                type.name AS type_name,
                t.min_dia AS min_dia,
                t.max_dia AS max_dia,
                t.resistance AS resistance,
                t.length AS length,
                t.weight AS weight,
                t.wire_size_dia_min AS wire_size_dia_min,
                t.wire_size_dia_max AS wire_size_dia_max,
                t.wire_size_cross_min AS wire_size_cross_min,
                t.wire_size_cross_max AS wire_size_cross_max,
                t.wire_size_awg_min AS wire_size_awg_min,
                t.wire_size_awg_max AS wire_size_awg_max,
                t.num_wires AS num_wires,
                t.model3d_id AS model3d_id,
                t.image_id AS image_id
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN materials AS material ON material.id = t.material_id
            LEFT JOIN platings AS plating ON plating.id = t.plating_id
            LEFT JOIN splice_types AS type ON type.id = t.type_id
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
        9: ('Material', 'material_name'),
        10: ('Plating', 'plating_description'),
        11: ('Type', 'type_name'),
        12: ('Diameter (mm)(min)', 'min_dia'),
        13: ('Diameter (mm)(max)', 'max_dia'),
        14: ('Resistance (Ω)', 'resistance'),
        15: ('Length (mm)', 'length'),
        16: ('Weight (g)', 'weight'),
        17: ('Wire AWG (min)', 'wire_size_awg_min'),
        18: ('Wire AWG (max)', 'wire_size_awg_max'),
        19: ('Wire Dia (mm)(min)', 'wire_size_dia_min'),
        20: ('Wire Dia (mm)(max)', 'wire_size_dia_max'),
        21: ('Wire Cross (mm²)(min)', 'wire_size_cross_min'),
        22: ('Wire Cross (mm²)(max)', 'wire_size_cross_max'),
        23: ('Wire Count', 'num_wires'),
        24: ('3D Model', 'model3d_id'),
    }
    table: "_splice.SplicesTable" = None
