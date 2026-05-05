from typing import TYPE_CHECKING

import wx
from . import base as _base

if TYPE_CHECKING:
    from ...database.global_db import wire as _wire


class WiresPage(_base.EditorList):
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'wires'
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
                min_temp.name AS min_temp_name,
                max_temp.name AS max_temp_name,
                material.name AS material_name,
                stripe_color.name AS stripe_color_name,
                core_material.description AS core_material_description,
                t.num_conductors,
                t.shielded,
                t.tpi,
                t.wire_size_dia,
                t.wire_size_cross,
                t.wire_size_awg,
                t.od_mm,
                t.weight_1km,
                t.resistance_1km,
                t.volts,
                t.strands
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
        9: 'Jacket Material',
        10: 'Stripe Color',
        11: 'Core Material',
        12: 'Conductor Count',
        13: 'Shielded',
        14: 'TPI',
        15: 'Wire Dia (mm)',
        16: 'Wire Cross (mm²)',
        17: 'Wire AWG',
        18: 'Outside Dia (mm)',
        19: 'Weight (g/km)',
        20: 'Resistance (Ω/km)',
        21: 'Volts (V)',
        22: 'Strands'
    }

    table: "_wire.WiresTable" = None
