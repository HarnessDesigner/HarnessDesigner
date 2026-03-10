import os
import json
import math


from ... import db_connectors as _con

from . import families as _families
from . import manufacturers as _manufacturers
from . import series as _series
from . import colors as _colors
from . import materials as _materials
from . import resources as _resources
from . import temperatures as _temperatures
from . import platings as _platings


def add_wires(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_wire(con, cur, **line)


def wires(con, cur, splash):
    res = cur.execute('SELECT id FROM wires WHERE id=0;')

    if res.fetchall():
        return

    splash.SetText(f'Adding core wire to db [1 | 1]...')

    cur.execute('INSERT INTO wires (id, part_number, mfg_id, description, size_mm2, '
                'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                'color_id, stripe_color_id, family_id, series_id) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 0, 'Internal Use DO NOT DELETE', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 999999, 999999, 0, 0))
    con.commit()

    splash.SetText(f'Building wires...')

    data = _build_wires(con, cur)

    data_len = len(data)

    splash.SetText(f'Adding wires to db [0 | {data_len}]...')

    cur.executemany('INSERT INTO wires (part_number, mfg_id, description, size_mm2, '
                    'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                    'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                    'color_id, stripe_color_id, family_id, series_id) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    data)

    splash.SetText(f'Adding wires to db [{data_len} | {data_len}]...')
    con.commit()

    # os.path.join(DATA_PATH, 'wires.json')

    json_paths = []

    for json_path in json_paths:
        if os.path.exists(json_path):

            splash.SetText(f'Loading Wire file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding wire to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding wire to db [{i} | {data_len}]...')
                add_wire(con, cur, **item)

            con.commit()


def add_wire(con, cur, part_number, mfg, description, size_mm2, size_awg, od_mm,
             conductor_dia_mm, weight_1km, resistance_1km, core_material, min_temp,
             max_temp, volts, material, color, stripe_color, family, series,
             datasheet=None, image=None, cad=None):

    mfg_id = _manufacturers.get_mfg_id(con, cur, mfg)
    core_material_id = _platings.get_plating_id(con, cur, core_material)
    series_id = _series.get_series_id(con, cur, series, mfg_id)
    family_id = _families.get_family_id(con, cur, family, mfg_id)
    color_id = _colors.get_color_id(con, cur, color)
    stripe_color_id = _colors.get_color_id(con, cur, stripe_color if stripe_color else 'None')
    material_id = _materials.get_material_id(con, cur, material)
    min_temp_id = _temperatures.get_temperature_id(con, cur, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, cur, max_temp)

    datasheet_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    image_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_CAD, cad)

    cur.execute('INSERT INTO wires (part_number, mfg_id, description, size_mm2, '
                'size_awg, od_mm, conductor_dia_mm, weight_1km, resistance_1km, '
                'core_material_id, min_temp_id, max_temp_id, volts, material_id, '
                'color_id, stripe_color_id, family_id, series_id, image_id, datasheet_id, cad_id) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, mfg_id, description, size_mm2, size_awg, od_mm,
                 conductor_dia_mm, weight_1km, resistance_1km, core_material_id,
                 min_temp_id, max_temp_id, volts, material_id, color_id,
                 stripe_color_id, family_id, series_id, image_id, datasheet_id, cad_id))
    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'wires',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_families.table,
                                                    _families.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.table,
                                                    _series.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datasheet_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stripe_color_id', default='999999', no_null=True,
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('num_conductors', default='1', no_null=True),
    _con.IntField('shielded', default='0', no_null=True),
    _con.FloatField('tpi', default='"0.0"', no_null=True),
    _con.FloatField('conductor_dia_mm', default='NULL'),
    _con.FloatField('size_mm2', default='NULL'),
    _con.IntField('size_awg', default='NULL'),
    _con.FloatField('od_mm', no_null=True),
    _con.FloatField('weight_1km', default='"0.0"', no_null=True),
    _con.IntField('core_material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('resistance_ikm', default='"0.0"', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True)
)


# def wires(con, cur):
#     cur.execute('CREATE TABLE wires('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'stripe_color_id INTEGER DEFAULT 999999 NOT NULL, '
#                 'num_conductors INTEGER DEFAULT 1 NOT NULL, '
#                 'shielded INTEGER DEFAULT 0 NOT NULL, '
#                 'tpi REAL DEFAULT "0.0" NOT NULL, '
#                 'conductor_dia_mm REAL DEFAULT NULL, '
#                 'size_mm2 REAL DEFAULT NULL, '
#                 'size_awg INTEGER DEFAULT NULL, '
#                 'od_mm REAL NOT NULL, '
#                 'weight_1km REAL DEFAULT "0.0" NOT NULL, '
#                 'core_material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'resistance_1km REAL DEFAULT "0.0" NOT NULL, '
#                 'volts REAL DEFAULT "0.0" NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (stripe_color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (core_material_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()


def _build_wires(con, cur):
    mapping = {
        'M22759/5': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 6.48,
                    'weight': 115.0,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 4.73,
                    'weight': 63.3,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 4.24,
                    'weight': 46.0,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 3.81,
                    'weight': 33.5,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 3.30,
                    'weight': 24.7,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.92,
                    'weight': 19.2,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.54,
                    'weight': 13.6,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 2.29,
                    'weight': 10.1,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 2.03,
                    'weight': 7.60,
                    'resistance': 79.7
                }

            }
        },
        'M22759/6': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.14,
                    'od': 6.48,
                    'weight': 118.0,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.77,
                    'od': 4.73,
                    'weight': 64.8,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 4.24,
                    'weight': 47.5,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 3.81,
                    'weight': 34.7,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 3.30,
                    'weight': 25.2,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 2.92,
                    'weight': 19.5,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.54,
                    'weight': 13.9,
                    'resistance': 32.1
                },
                22: {
                    'dia': 0.76,
                    'od': 2.29,
                    'weight': 10.4,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 2.03,
                    'weight': 7.70,
                    'resistance': 85.0
                }

            }
        },
        'M22759/7': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.72,
                    'weight': 101.0,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 4.11,
                    'weight': 55.7,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 3.48,
                    'weight': 38.3,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 3.00,
                    'weight': 25.8,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.67,
                    'weight': 18.9,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.39,
                    'weight': 15.2,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.13,
                    'weight': 10.9,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.91,
                    'weight': 7.44,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.63,
                    'weight': 5.51,
                    'resistance': 79.7
                }

            }
        },
        'M22759/8': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with abrasion-resistant mineral fillers',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.14,
                    'od': 5.72,
                    'weight': 104.0,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.77,
                    'od': 4.11,
                    'weight': 57.2,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 3.48,
                    'weight': 42.8,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 3.00,
                    'weight': 27.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.67,
                    'weight': 19.4,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 2.39,
                    'weight': 15.5,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 2.13,
                    'weight': 11.2,
                    'resistance': 32.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.91,
                    'weight': 7.66,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.63,
                    'weight': 5.66,
                    'resistance': 85.0
                }

            }
        },
        'M22759/9': {
            'start': 8,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.38,
                    'weight': 97.3,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 3.68,
                    'weight': 52.5,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 3.15,
                    'weight': 34.7,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 2.62,
                    'weight': 24.0,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.21,
                    'weight': 15.8,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 2.03,
                    'weight': 12.9,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 209.0
                }
            }
        },
        'M22759/10': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.13,
                    'weight': 98.8,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.74,
                    'od': 3.48,
                    'weight': 53.4,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 2.95,
                    'weight': 34.8,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 2.46,
                    'weight': 24.1,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.11,
                    'weight': 16.1,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.93,
                    'weight': 12.9,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.68,
                    'weight': 9.06,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.47,
                    'weight': 6.40,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.30,
                    'weight': 4.66,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.17,
                    'weight': 3.54,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 223.0
                }
            }
        },
        'M22759/11': {
            'start': 8,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.23,
                    'weight': 86.1,
                    'resistance': 2.16
                },
                10: {
                    'dia': 2.74,
                    'od': 3.63,
                    'weight': 52.0,
                    'resistance': 3.90
                },
                12: {
                    'dia': 2.18,
                    'od': 2.90,
                    'weight': 35.0,
                    'resistance': 5.94
                },
                14: {
                    'dia': 1.70,
                    'od': 2.34,
                    'weight': 21.9,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 1.96,
                    'weight': 14.3,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.78,
                    'weight': 11.3,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.66,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.12,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.59,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.59,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.82,
                    'resistance': 209.0
                }
            }
        },
        'M22759/12': {
            'start': 8,
            'stop': 25,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                8: {
                    'dia': 4.11,
                    'od': 5.28,
                    'weight': 87.5,
                    'resistance': 2.28
                },
                10: {
                    'dia': 2.74,
                    'od': 3.63,
                    'weight': 52.8,
                    'resistance': 4.07
                },
                12: {
                    'dia': 2.18,
                    'od': 2.90,
                    'weight': 35.7,
                    'resistance': 6.20
                },
                14: {
                    'dia': 1.70,
                    'od': 2.34,
                    'weight': 22.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 1.96,
                    'weight': 14.5,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.78,
                    'weight': 11.4,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.72,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.15,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.60,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.60,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.83,
                    'resistance': 223.0
                }
            }
        },
        'M22759/16': {
            'start': -2,
            'stop': 25,
            'step': 1,
            'con_plate': 'Sn/Cu',
            'material': 'Extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                -2: {
                    'dia': 11.7,
                    'od': 14.0,
                    'weight': 722.0,
                    'resistance': 0.299
                },
                -1: {
                    'dia': 10.5,
                    'od': 12.3,
                    'weight': 566.0,
                    'resistance': 0.380
                },
                1: {
                    'dia': 9.40,
                    'od': 11.1,
                    'weight': 437.0,
                    'resistance': 0.489
                },
                2: {
                    'dia': 8.38,
                    'od': 9.96,
                    'weight': 344.0,
                    'resistance': 0.600
                },
                4: {
                    'dia': 6.60,
                    'od': 8.03,
                    'weight': 227.0,
                    'resistance': 0.916
                },
                6: {
                    'dia': 5.13,
                    'od': 6.43,
                    'weight': 144.0,
                    'resistance': 1.46
                },
                8: {
                    'dia': 4.11,
                    'od': 5.13,
                    'weight': 91.5,
                    'resistance': 2.30
                },
                10: {
                    'dia': 2.79,
                    'od': 3.61,
                    'weight': 50.6,
                    'resistance': 4.13
                },
                12: {
                    'dia': 2.18,
                    'od': 2.97,
                    'weight': 32.4,
                    'resistance': 6.63
                },
                14: {
                    'dia': 1.70,
                    'od': 2.41,
                    'weight': 21.6,
                    'resistance': 10.0
                },
                16: {
                    'dia': 1.35,
                    'od': 2.06,
                    'weight': 14.4,
                    'resistance': 15.8
                },
                18: {
                    'dia': 1.22,
                    'od': 1.85,
                    'weight': 11.4,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.97,
                    'od': 1.57,
                    'weight': 7.71,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.37,
                    'weight': 5.24,
                    'resistance': 53.1
                },
                24: {
                    'dia': 0.61,
                    'od': 1.19,
                    'weight': 3.65,
                    'resistance': 85.9
                }
            }
        },
        'M22759/17': {
            'start': 20,
            'stop': 27,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.57,
                    'weight': 7.38,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.37,
                    'weight': 5.06,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.19,
                    'weight': 3.45,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.07,
                    'weight': 2.49,
                    'resistance': 147.0
                }
            }
        },
        'M22759/18': {
            'start': 10,
            'stop': 27,
            'step': 2,
            'con_plate': 'Sn/Cu',
            'material': 'Thin-wall extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                10: {
                    'dia': 2.79,
                    'od': 3.48,
                    'weight': 49.3,
                    'resistance': 4.13
                },
                12: {
                    'dia': 2.18,
                    'od': 2.80,
                    'weight': 31.3,
                    'resistance': 6.63
                },
                14: {
                    'dia': 1.70,
                    'od': 2.21,
                    'weight': 20.4,
                    'resistance': 10.0
                },
                16: {
                    'dia': 1.35,
                    'od': 1.83,
                    'weight': 13.3,
                    'resistance': 15.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.60,
                    'weight': 10.3,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.97,
                    'od': 1.35,
                    'weight': 6.85,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.14,
                    'weight': 4.52,
                    'resistance': 53.1
                },
                24: {
                    'dia': 0.61,
                    'od': 0.97,
                    'weight': 3.01,
                    'resistance': 85.9
                },
                26: {
                    'dia': 0.48,
                    'od': 0.86,
                    'weight': 2.26,
                    'resistance': 135.0
                }
            }
        },
        'M22759/19': {
            'start': 20,
            'stop': 27,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Thin-wall extruded ETFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.35,
                    'weight': 6.62,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.14,
                    'weight': 4.27,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 0.97,
                    'weight': 2.86,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 0.86,
                    'weight': 2.02,
                    'resistance': 147.0
                }
            }
        },
        'M22759/20': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 244.0
                }
            }
        },
        'M22759/21': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE',
            'volts': 1000,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.78,
                    'weight': 9.06,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.57,
                    'weight': 6.40,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.40,
                    'weight': 4.66,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.27,
                    'weight': 3.54,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 1.14,
                    'weight': 2.65,
                    'resistance': 259.0
                }
            }
        },
        'M22759/22': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Thin-wall extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.72,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.28,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.74,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.74,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.89,
                    'resistance': 244.0
                }
            }
        },
        'M22759/23': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Thin-wall extruded PTFE',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.52,
                    'weight': 7.84,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.30,
                    'weight': 5.39,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.14,
                    'weight': 3.79,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.02,
                    'weight': 2.77,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.89,
                    'weight': 1.92,
                    'resistance': 259.0
                }
            }
        },
        'M22759/28': {
            'start': 14,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                14: {
                    'dia': 1.70,
                    'od': 2.39,
                    'weight': 22.0,
                    'resistance': 9.45
                },
                16: {
                    'dia': 1.35,
                    'od': 2.01,
                    'weight': 14.5,
                    'resistance': 14.8
                },
                18: {
                    'dia': 1.19,
                    'od': 1.80,
                    'weight': 11.4,
                    'resistance': 19.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 30.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 49.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 79.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 126.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 209.0
                }
            }
        },
        'M22759/29': {
            'start': 14,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                14: {
                    'dia': 1.70,
                    'od': 2.39,
                    'weight': 22.0,
                    'resistance': 9.84
                },
                16: {
                    'dia': 1.35,
                    'od': 2.01,
                    'weight': 14.5,
                    'resistance': 15.6
                },
                18: {
                    'dia': 1.19,
                    'od': 1.80,
                    'weight': 11.4,
                    'resistance': 20.0
                },
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 32.0
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 52.5
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 85.0
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 138.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 223.0
                }
            }
        },
        'M22759/30': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ag/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 200,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.80,
                    'resistance': 35.1
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.22,
                    'resistance': 57.4
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.68,
                    'resistance': 93.2
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.68,
                    'resistance': 147.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.89,
                    'resistance': 244.0
                }
            }
        },
        'M22759/31': {
            'start': 20,
            'stop': 29,
            'step': 2,
            'con_plate': 'Ni/Cu',
            'material': 'Extruded PTFE with polyimide hard coat.',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 260,
            'data': {
                20: {
                    'dia': 0.97,
                    'od': 1.55,
                    'weight': 7.86,
                    'resistance': 37.4
                },
                22: {
                    'dia': 0.76,
                    'od': 1.32,
                    'weight': 5.24,
                    'resistance': 61.0
                },
                24: {
                    'dia': 0.61,
                    'od': 1.17,
                    'weight': 3.69,
                    'resistance': 98.7
                },
                26: {
                    'dia': 0.48,
                    'od': 1.04,
                    'weight': 2.69,
                    'resistance': 162.0
                },
                28: {
                    'dia': 0.38,
                    'od': 0.91,
                    'weight': 1.90,
                    'resistance': 259.0
                }
            }
        },
        'M22759/32': {
            'start': 12,
            'stop': 31,
            'step': 2,
            'con_plate': 'Sn/Cu',
            'material': 'Fluoropolymer Cross-linked Modified (ETFE)',
            'volts': 600,
            'min_temp': -55,
            'max_temp': 150,
            'data': {
                12: {
                    'dia': 0.0,
                    'od': 2.62,
                    'weight': 29.0,
                    'resistance': 6.63
                },
                14: {
                    'dia': 0.0,
                    'od': 2.16,
                    'weight': 19.0,
                    'resistance': 10.0
                },
                16: {
                    'dia': 0.0,
                    'od': 1.73,
                    'weight': 12.3,
                    'resistance': 15.8
                },
                18: {
                    'dia': 0.0,
                    'od': 1.52,
                    'weight': 9.67,
                    'resistance': 20.4
                },
                20: {
                    'dia': 0.0,
                    'od': 1.27,
                    'weight': 6.40,
                    'resistance': 32.4
                },
                22: {
                    'dia': 0.0,
                    'od': 1.09,
                    'weight': 4.17,
                    'resistance': 53.2
                },
                24: {
                    'dia': 0.0,
                    'od': 0.94,
                    'weight': 2.98,
                    'resistance': 86.0
                },
                26: {
                    'dia': 0.0,
                    'od': 0.81,
                    'weight': 2.08,
                    'resistance': 136.0
                },
                28: {
                    'dia': 0.0,
                    'od': 0.68,
                    'weight': 1.35,
                    'resistance': 225.0
                },
                30: {
                    'dia': 0.0,
                    'od': 0.61,
                    'weight': 0.98,
                    'resistance': 330.0
                }
            }
        },
        # 'M22759/80': {},
        # 'M22759/81': {},
        # 'M22759/82': {},
        # 'M22759/83': {},
        # 'M22759/84': {},
        # 'M22759/85': {},
        # 'M22759/86': {},
        # 'M22759/87': {},
        # 'M22759/88': {},
        # 'M22759/89': {},
        # 'M22759/90': {},
        # 'M22759/91': {},
        # 'M22759/92': {}
    }

    color_mapping = {
        0: 'Black',
        1: 'Brown',
        2: 'Red',
        3: 'Orange',
        4: 'Yellow',
        5: 'Green',
        6: 'Blue',
        7: 'Violet',
        8: 'Gray',
        9: 'White'
    }

    def __awg_to_mm2(a: int) -> float:
        d_in = 0.005 * (92 ** ((36 - a) / 39))
        d_mm = d_in * 25.4
        area_mm2 = (math.pi / 4) * (d_mm ** 2)
        return round(area_mm2, 4)

    pn_template = '{series}-{awg}-{primary}{secondary}'

    values = []
    mfg_id = _manufacturers.get_mfg_id(con, cur, 'TE')

    family_id = _families.get_family_id(con, cur, 'Tefzel', mfg_id)

    for series, wire_data in mapping.items():
        series_id = _series.get_series_id(con, cur, series, 2)
        plating_id = _platings.get_plating_id(con, cur, wire_data['con_plate'])
        min_temp = str(wire_data['min_temp']) + '°C'
        max_temp = '+' + str(wire_data['max_temp']) + '°C'
        min_temp_id = _temperatures.get_temperature_id(con, cur, min_temp)
        max_temp_id = _temperatures.get_temperature_id(con, cur, max_temp)
        volts = wire_data['volts']
        material_id = _materials.get_material_id(con, cur, wire_data['material'])

        for awg in range(wire_data['start'], wire_data['stop'], wire_data['step']):
            if awg not in wire_data['data']:
                continue

            dia = wire_data['data'][awg]['dia']
            od_mm = wire_data['data'][awg]['od']
            weight = wire_data['data'][awg]['weight'] * 1000.0
            resistance = wire_data['data'][awg]['resistance']

            mm_2 = __awg_to_mm2(awg)

            for p_id in range(10):
                part_number = pn_template.format(series=series, awg=awg, primary=p_id, secondary='')
                description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]} Tefzel milspec single conductor wire'

                values.append((part_number, mfg_id, description, str(mm_2), awg, od_mm, dia, weight, resistance, plating_id, min_temp_id, max_temp_id, volts, material_id, p_id, 999999, family_id, series_id))
                for s_id in range(10):
                    if p_id == s_id:
                        continue
                    description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]}/{color_mapping[s_id]} Tefzel milspec single conductor wire'

                    values.append((part_number + str(s_id), mfg_id, description, mm_2, awg, od_mm, dia, weight, resistance, plating_id, min_temp_id, max_temp_id, volts, material_id, p_id, s_id, family_id, series_id))

    return values
