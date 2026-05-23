# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base as _base


if TYPE_CHECKING:
    from ...database.global_db import wire as _wire


class WiresPage(_base.EditorList):
    """Represent a wires page in :mod:`harness_designer.ui.editor_db.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'wires'
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
                material.name AS material_name,
                stripe_color.name AS stripe_color_name,
                core_material.description AS core_material_description,
                t.num_conductors AS num_conductors,
                t.shielded AS shielded,
                t.tpi AS tpi,
                t.wire_size_dia AS wire_size_dia,
                t.wire_size_cross AS wire_size_cross,
                t.wire_size_awg AS wire_size_awg,
                t.od_mm AS od_mm,
                t.weight_1km AS weight_1km,
                t.resistance_1km AS resistance_1km,
                t.volts AS volts,
                t.strands AS strands
            FROM {__table_name__} AS t
            LEFT JOIN manufacturers AS mfg ON mfg.id = t.mfg_id
            LEFT JOIN families AS family ON family.id = t.family_id
            LEFT JOIN series AS series ON series.id = t.series_id
            LEFT JOIN colors AS color ON color.id = t.color_id
            LEFT JOIN temperatures AS min_temp ON min_temp.id = t.min_temp_id
            LEFT JOIN temperatures AS max_temp ON max_temp.id = t.max_temp_id
            LEFT JOIN materials AS material ON material.id = t.material_id
            LEFT JOIN colors AS stripe_color ON stripe_color.id = t.stripe_color_id
            LEFT JOIN platings AS core_material ON core_material.id = t.core_material_id
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
        9: ('Jacket Material', 'material_name'),
        10: ('Stripe Color', 'stripe_color_name'),
        11: ('Core Material', 'core_material_description'),
        12: ('Conductor Count', 'num_conductors'),
        13: ('Shielded', 'shielded'),
        14: ('TPI', 'tpi'),
        15: ('Wire Dia (mm)', 'wire_size_dia'),
        16: ('Wire Cross (mm²)', 'wire_size_cross'),
        17: ('Wire AWG', 'wire_size_awg'),
        18: ('Outside Dia (mm)', 'od_mm'),
        19: ('Weight (g/km)', 'weight_1km'),
        20: ('Resistance (Ω/km)', 'resistance_1km'),
        21: ('Volts (V)', 'volts'),
        22: ('Strands', 'strands')
    }

    table: "_wire.WiresTable" = None
