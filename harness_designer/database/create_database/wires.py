import os
import json
import math

from . import families as _families
from . import manufacturers as _manufacturers
from . import series as _series
from . import colors as _colors
from . import materials as _materials
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import temperatures as _temperatures
from . import platings as _platings

from . import projects as _projects
from . import points2d as _points2d
from . import points3d as _points3d
from . import circuits as _circuits
from . import bundle_covers as _bundle_covers
from . import transitions as _transitions


from harness_designer.database import db_connectors as _con
from ... import logger as _logger


def add_wires(con, data: tuple[dict] | list[dict]):
    for line in data:
        add_wire(con, **line)


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM wires WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding wire to db [1 | 1]...')
    splash.flush()

    con.execute('INSERT INTO wires (id, part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, material_id, stripe_color_id, core_material_id, num_conductors, '
                'shielded, tpi, conductor_dia_mm, size_mm2, size_awg, od_mm, weight_1km, '
                'resistance_1km, volts) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 'Internal Use DO NOT DELETE', 0, 0, 0, 999999, 0, 0, 0,
                 0, 0, 0, 999999, 0, 0, 0, 0, 0.0, 0.0, -1, 0.0, 0.0, 0.0, 0.0))
    con.commit()

    splash.SetText(f'Building wires...')
    splash.flush()

    data = _build_wires(con)

    data_len = len(data)

    splash.SetText(f'Adding wires to db [{data_len} | {data_len}]...')
    splash.flush()

    try:
        con.executemany('INSERT INTO wires (part_number, description, mfg_id, family_id, '
                        'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                        'max_temp_id, material_id, stripe_color_id, core_material_id, '
                        'num_conductors, shielded, tpi, conductor_dia_mm, size_mm2, '
                        'size_awg, od_mm, weight_1km, resistance_1km, volts) '
                        'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                        data)

        con.commit()
    except:  # NOQA
        pass

    dirs = []
    for file in os.listdir(data_path):
        file = os.path.join(data_path, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'wires.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading Wire file...')
            splash.flush()

            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding wire to db [0 | {data_len}]...')
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding wire to db [{i + 1} | {data_len}]...')

                pn = item['part_number']
                con.execute(f'SELECT id FROM wires WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    add_wire(con, **item)

        con.commit()

    os.chdir(cwd)


def add_wire(con, part_number, description, mfg=None, family=None, series=None,
             color=None, image=None, datasheet=None, cad=None, min_temp=None,
             max_temp=None, material=None, stripe_color=None, core_material=None,
             num_conductors=1, shielded=0, tpi=0.0, conductor_dia_mm=0.0, size_mm2=0.0,
             size_awg=-1, od_mm=0.0, weight_1km=0.0, resistance_1km=0.0, volts=0.0):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    core_material_id = _platings.get_plating_id(con, core_material)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    stripe_color_id = _colors.get_color_id(con, stripe_color if stripe_color else 'None')
    material_id = _materials.get_material_id(con, material)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)

    con.execute('INSERT INTO wires (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, material_id, stripe_color_id, core_material_id, '
                'num_conductors, shielded, tpi, conductor_dia_mm, size_mm2, size_awg, '
                'od_mm, weight_1km, resistance_1km, volts) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, material_id,
                 stripe_color_id, core_material_id, num_conductors, shielded, tpi,
                 conductor_dia_mm, size_mm2, size_awg, od_mm, weight_1km, resistance_1km,
                 volts))
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
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_images.table,
                                                    _images.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datasheet_id', default='NULL',
                  references=_con.SQLFieldReference(_datasheets.table,
                                                    _datasheets.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_cads.table,
                                                    _cads.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stripe_color_id', default='999999', no_null=True,
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('core_material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('num_conductors', default='1', no_null=True),
    _con.IntField('shielded', default='0', no_null=True),
    _con.FloatField('tpi', default='"0.0"', no_null=True),
    _con.FloatField('conductor_dia_mm', default='NULL'),
    _con.FloatField('size_mm2', default='NULL'),
    _con.IntField('size_awg', default='NULL'),
    _con.FloatField('od_mm', no_null=True),
    _con.FloatField('weight_1km', default='"0.0"', no_null=True),
    _con.FloatField('resistance_1km', default='"0.0"', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True)
)

pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_wires',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('part_id', no_null=True,
                  references=_con.SQLFieldReference(table,
                                                    id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', default='NULL',
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('bundle_id', default='NULL',
                  references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                    _bundle_covers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('transition_id', default='NULL',
                  references=_con.SQLFieldReference(_transitions.pjt_table,
                                                    _transitions.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('start_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('start_point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

def _build_wires(con):
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
                8: {'dia': 4.11, 'od': 6.48, 'weight': 115.00, 'resistance': 2.16},
                10: {'dia': 2.74, 'od': 4.73, 'weight': 63.30, 'resistance': 3.90},
                12: {'dia': 2.18, 'od': 4.24, 'weight': 46.00, 'resistance': 5.94},
                14: {'dia': 1.70, 'od': 3.81, 'weight': 33.50, 'resistance': 9.45},
                16: {'dia': 1.35, 'od': 3.30, 'weight': 24.70, 'resistance': 14.80},
                18: {'dia': 1.19, 'od': 2.92, 'weight': 19.20, 'resistance': 19.00},
                20: {'dia': 0.97, 'od': 2.54, 'weight': 13.60, 'resistance': 30.10},
                22: {'dia': 0.76, 'od': 2.29, 'weight': 10.10, 'resistance': 49.50},
                24: {'dia': 0.61, 'od': 2.03, 'weight': 7.60, 'resistance': 79.70}
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
                8: {'dia': 4.14, 'od': 6.48, 'weight': 118.00, 'resistance': 2.28},
                10: {'dia': 2.77, 'od': 4.73, 'weight': 64.80, 'resistance': 4.07},
                12: {'dia': 2.18, 'od': 4.24, 'weight': 47.50, 'resistance': 6.20},
                14: {'dia': 1.70, 'od': 3.81, 'weight': 34.70, 'resistance': 9.84},
                16: {'dia': 1.35, 'od': 3.30, 'weight': 25.20, 'resistance': 15.60},
                18: {'dia': 1.19, 'od': 2.92, 'weight': 19.50, 'resistance': 20.00},
                20: {'dia': 0.97, 'od': 2.54, 'weight': 13.90, 'resistance': 32.10},
                22: {'dia': 0.76, 'od': 2.29, 'weight': 10.40, 'resistance': 52.50},
                24: {'dia': 0.61, 'od': 2.03, 'weight': 7.70, 'resistance': 85.00}
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
                8: {'dia': 4.11, 'od': 5.72, 'weight': 101.00, 'resistance': 2.16},
                10: {'dia': 2.74, 'od': 4.11, 'weight': 55.70, 'resistance': 3.90},
                12: {'dia': 2.18, 'od': 3.48, 'weight': 38.30, 'resistance': 5.94},
                14: {'dia': 1.70, 'od': 3.00, 'weight': 25.80, 'resistance': 9.45},
                16: {'dia': 1.35, 'od': 2.67, 'weight': 18.90, 'resistance': 14.80},
                18: {'dia': 1.19, 'od': 2.39, 'weight': 15.20, 'resistance': 19.00},
                20: {'dia': 0.97, 'od': 2.13, 'weight': 10.90, 'resistance': 30.10},
                22: {'dia': 0.76, 'od': 1.91, 'weight': 7.44, 'resistance': 49.50},
                24: {'dia': 0.61, 'od': 1.63, 'weight': 5.51, 'resistance': 79.70}
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
                8: {'dia': 4.14, 'od': 5.72, 'weight': 104.00, 'resistance': 2.28},
                10: {'dia': 2.77, 'od': 4.11, 'weight': 57.20, 'resistance': 4.07},
                12: {'dia': 2.18, 'od': 3.48, 'weight': 42.80, 'resistance': 6.20},
                14: {'dia': 1.70, 'od': 3.00, 'weight': 27.00, 'resistance': 9.84},
                16: {'dia': 1.35, 'od': 2.67, 'weight': 19.40, 'resistance': 15.60},
                18: {'dia': 1.19, 'od': 2.39, 'weight': 15.50, 'resistance': 20.00},
                20: {'dia': 0.97, 'od': 2.13, 'weight': 11.20, 'resistance': 32.10},
                22: {'dia': 0.76, 'od': 1.91, 'weight': 7.66, 'resistance': 52.50},
                24: {'dia': 0.61, 'od': 1.63, 'weight': 5.66, 'resistance': 85.00}
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
                8: {'dia': 4.11, 'od': 5.38, 'weight': 97.30, 'resistance': 2.16},
                10: {'dia': 2.74, 'od': 3.68, 'weight': 52.50, 'resistance': 3.90},
                12: {'dia': 2.18, 'od': 3.15, 'weight': 34.70, 'resistance': 5.94},
                14: {'dia': 1.70, 'od': 2.62, 'weight': 24.00, 'resistance': 9.45},
                16: {'dia': 1.35, 'od': 2.21, 'weight': 15.80, 'resistance': 14.80},
                18: {'dia': 1.19, 'od': 2.03, 'weight': 12.90, 'resistance': 19.00},
                20: {'dia': 0.97, 'od': 1.78, 'weight': 9.06, 'resistance': 30.10},
                22: {'dia': 0.76, 'od': 1.57, 'weight': 6.40, 'resistance': 49.50},
                24: {'dia': 0.61, 'od': 1.40, 'weight': 4.66, 'resistance': 79.70},
                26: {'dia': 0.48, 'od': 1.27, 'weight': 3.54, 'resistance': 126.00},
                28: {'dia': 0.38, 'od': 1.14, 'weight': 2.65, 'resistance': 209.00}
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
                8: {'dia': 4.11, 'od': 5.13, 'weight': 98.80, 'resistance': 2.28},
                10: {'dia': 2.74, 'od': 3.48, 'weight': 53.40, 'resistance': 4.07},
                12: {'dia': 2.18, 'od': 2.95, 'weight': 34.80, 'resistance': 6.20},
                14: {'dia': 1.70, 'od': 2.46, 'weight': 24.10, 'resistance': 9.84},
                16: {'dia': 1.35, 'od': 2.11, 'weight': 16.10, 'resistance': 15.60},
                18: {'dia': 1.19, 'od': 1.93, 'weight': 12.90, 'resistance': 20.00},
                20: {'dia': 0.97, 'od': 1.68, 'weight': 9.06, 'resistance': 32.00},
                22: {'dia': 0.76, 'od': 1.47, 'weight': 6.40, 'resistance': 52.50},
                24: {'dia': 0.61, 'od': 1.30, 'weight': 4.66, 'resistance': 85.00},
                26: {'dia': 0.48, 'od': 1.17, 'weight': 3.54, 'resistance': 138.00},
                28: {'dia': 0.38, 'od': 1.14, 'weight': 2.65, 'resistance': 223.00}
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
                8: {'dia': 4.11, 'od': 5.23, 'weight': 86.10, 'resistance': 2.16},
                10: {'dia': 2.74, 'od': 3.63, 'weight': 52.00, 'resistance': 3.90},
                12: {'dia': 2.18, 'od': 2.90, 'weight': 35.00, 'resistance': 5.94},
                14: {'dia': 1.70, 'od': 2.34, 'weight': 21.90, 'resistance': 9.45},
                16: {'dia': 1.35, 'od': 1.96, 'weight': 14.30, 'resistance': 14.80},
                18: {'dia': 1.19, 'od': 1.78, 'weight': 11.30, 'resistance': 19.00},
                20: {'dia': 0.97, 'od': 1.52, 'weight': 7.66, 'resistance': 30.10},
                22: {'dia': 0.76, 'od': 1.30, 'weight': 5.12, 'resistance': 49.50},
                24: {'dia': 0.61, 'od': 1.14, 'weight': 3.59, 'resistance': 79.70},
                26: {'dia': 0.48, 'od': 1.02, 'weight': 2.59, 'resistance': 126.00},
                28: {'dia': 0.38, 'od': 0.89, 'weight': 1.82, 'resistance': 209.00}
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
                8: {'dia': 4.11, 'od': 5.28, 'weight': 87.50, 'resistance': 2.28},
                10: {'dia': 2.74, 'od': 3.63, 'weight': 52.80, 'resistance': 4.07},
                12: {'dia': 2.18, 'od': 2.90, 'weight': 35.70, 'resistance': 6.20},
                14: {'dia': 1.70, 'od': 2.34, 'weight': 22.00, 'resistance': 9.84},
                16: {'dia': 1.35, 'od': 1.96, 'weight': 14.50, 'resistance': 15.60},
                18: {'dia': 1.19, 'od': 1.78, 'weight': 11.40, 'resistance': 20.00},
                20: {'dia': 0.97, 'od': 1.52, 'weight': 7.72, 'resistance': 32.00},
                22: {'dia': 0.76, 'od': 1.30, 'weight': 5.15, 'resistance': 52.50},
                24: {'dia': 0.61, 'od': 1.14, 'weight': 3.60, 'resistance': 85.00},
                26: {'dia': 0.48, 'od': 1.02, 'weight': 2.60, 'resistance': 138.00},
                28: {'dia': 0.38, 'od': 0.89, 'weight': 1.83, 'resistance': 223.00}
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
                -2: {'dia': 11.70, 'od': 14.00, 'weight': 722.00, 'resistance': 0.30},
                -1: {'dia': 10.50, 'od': 12.30, 'weight': 566.00, 'resistance': 0.38},
                1: {'dia': 9.40, 'od': 11.10, 'weight': 437.00, 'resistance': 0.49},
                2: {'dia': 8.38, 'od': 9.96, 'weight': 344.00, 'resistance': 0.60},
                4: {'dia': 6.60, 'od': 8.03, 'weight': 227.00, 'resistance': 0.92},
                6: {'dia': 5.13, 'od': 6.43, 'weight': 144.00, 'resistance': 1.46},
                8: {'dia': 4.11, 'od': 5.13, 'weight': 91.50, 'resistance': 2.30},
                10: {'dia': 2.79, 'od': 3.61, 'weight': 50.60, 'resistance': 4.13},
                12: {'dia': 2.18, 'od': 2.97, 'weight': 32.40, 'resistance': 6.63},
                14: {'dia': 1.70, 'od': 2.41, 'weight': 21.60, 'resistance': 10.00},
                16: {'dia': 1.35, 'od': 2.06, 'weight': 14.40, 'resistance': 15.80},
                18: {'dia': 1.22, 'od': 1.85, 'weight': 11.40, 'resistance': 20.40},
                20: {'dia': 0.97, 'od': 1.57, 'weight': 7.71, 'resistance': 32.40},
                22: {'dia': 0.76, 'od': 1.37, 'weight': 5.24, 'resistance': 53.10},
                24: {'dia': 0.61, 'od': 1.19, 'weight': 3.65, 'resistance': 85.90}
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
                20: {'dia': 0.97, 'od': 1.57, 'weight': 7.38, 'resistance': 35.10},
                22: {'dia': 0.76, 'od': 1.37, 'weight': 5.06, 'resistance': 57.40},
                24: {'dia': 0.61, 'od': 1.19, 'weight': 3.45, 'resistance': 93.20},
                26: {'dia': 0.48, 'od': 1.07, 'weight': 2.49, 'resistance': 147.00}
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
                10: {'dia': 2.79, 'od': 3.48, 'weight': 49.30, 'resistance': 4.13},
                12: {'dia': 2.18, 'od': 2.80, 'weight': 31.30, 'resistance': 6.63},
                14: {'dia': 1.70, 'od': 2.21, 'weight': 20.40, 'resistance': 10.00},
                16: {'dia': 1.35, 'od': 1.83, 'weight': 13.30, 'resistance': 15.80},
                18: {'dia': 1.19, 'od': 1.60, 'weight': 10.30, 'resistance': 20.40},
                20: {'dia': 0.97, 'od': 1.35, 'weight': 6.85, 'resistance': 32.40},
                22: {'dia': 0.76, 'od': 1.14, 'weight': 4.52, 'resistance': 53.10},
                24: {'dia': 0.61, 'od': 0.97, 'weight': 3.01, 'resistance': 85.90},
                26: {'dia': 0.48, 'od': 0.86, 'weight': 2.26, 'resistance': 135.00}
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
                20: {'dia': 0.97, 'od': 1.35, 'weight': 6.62, 'resistance': 35.10},
                22: {'dia': 0.76, 'od': 1.14, 'weight': 4.27, 'resistance': 57.40},
                24: {'dia': 0.61, 'od': 0.97, 'weight': 2.86, 'resistance': 93.20},
                26: {'dia': 0.48, 'od': 0.86, 'weight': 2.02, 'resistance': 147.00}
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
                20: {'dia': 0.97, 'od': 1.78, 'weight': 9.06, 'resistance': 35.10},
                22: {'dia': 0.76, 'od': 1.57, 'weight': 6.40, 'resistance': 57.40},
                24: {'dia': 0.61, 'od': 1.40, 'weight': 4.66, 'resistance': 93.20},
                26: {'dia': 0.48, 'od': 1.27, 'weight': 3.54, 'resistance': 147.00},
                28: {'dia': 0.38, 'od': 1.14, 'weight': 2.65, 'resistance': 244.00}
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
                20: {'dia': 0.97, 'od': 1.78, 'weight': 9.06, 'resistance': 37.40},
                22: {'dia': 0.76, 'od': 1.57, 'weight': 6.40, 'resistance': 61.00},
                24: {'dia': 0.61, 'od': 1.40, 'weight': 4.66, 'resistance': 98.70},
                26: {'dia': 0.48, 'od': 1.27, 'weight': 3.54, 'resistance': 162.00},
                28: {'dia': 0.38, 'od': 1.14, 'weight': 2.65, 'resistance': 259.00}
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
                20: {'dia': 0.97, 'od': 1.52, 'weight': 7.72, 'resistance': 35.10},
                22: {'dia': 0.76, 'od': 1.30, 'weight': 5.28, 'resistance': 57.40},
                24: {'dia': 0.61, 'od': 1.14, 'weight': 3.74, 'resistance': 93.20},
                26: {'dia': 0.48, 'od': 1.02, 'weight': 2.74, 'resistance': 147.00},
                28: {'dia': 0.38, 'od': 0.89, 'weight': 1.89, 'resistance': 244.00}
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
                20: {'dia': 0.97, 'od': 1.52, 'weight': 7.84, 'resistance': 37.40},
                22: {'dia': 0.76, 'od': 1.30, 'weight': 5.39, 'resistance': 61.00},
                24: {'dia': 0.61, 'od': 1.14, 'weight': 3.79, 'resistance': 98.70},
                26: {'dia': 0.48, 'od': 1.02, 'weight': 2.77, 'resistance': 162.00},
                28: {'dia': 0.38, 'od': 0.89, 'weight': 1.92, 'resistance': 259.00}
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
                14: {'dia': 1.70, 'od': 2.39, 'weight': 22.00, 'resistance': 9.45},
                16: {'dia': 1.35, 'od': 2.01, 'weight': 14.50, 'resistance': 14.80},
                18: {'dia': 1.19, 'od': 1.80, 'weight': 11.40, 'resistance': 19.00},
                20: {'dia': 0.97, 'od': 1.55, 'weight': 7.80, 'resistance': 30.10},
                22: {'dia': 0.76, 'od': 1.32, 'weight': 5.22, 'resistance': 49.50},
                24: {'dia': 0.61, 'od': 1.17, 'weight': 3.68, 'resistance': 79.70},
                26: {'dia': 0.48, 'od': 1.04, 'weight': 2.68, 'resistance': 126.00},
                28: {'dia': 0.38, 'od': 0.91, 'weight': 1.89, 'resistance': 209.00}
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
                14: {'dia': 1.70, 'od': 2.39, 'weight': 22.00, 'resistance': 9.84},
                16: {'dia': 1.35, 'od': 2.01, 'weight': 14.50, 'resistance': 15.60},
                18: {'dia': 1.19, 'od': 1.80, 'weight': 11.40, 'resistance': 20.00},
                20: {'dia': 0.97, 'od': 1.55, 'weight': 7.80, 'resistance': 32.00},
                22: {'dia': 0.76, 'od': 1.32, 'weight': 5.22, 'resistance': 52.50},
                24: {'dia': 0.61, 'od': 1.17, 'weight': 3.68, 'resistance': 85.00},
                26: {'dia': 0.48, 'od': 1.04, 'weight': 2.68, 'resistance': 138.00},
                28: {'dia': 0.38, 'od': 0.91, 'weight': 1.89, 'resistance': 223.00}
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
                20: {'dia': 0.97, 'od': 1.55, 'weight': 7.80, 'resistance': 35.10},
                22: {'dia': 0.76, 'od': 1.32, 'weight': 5.22, 'resistance': 57.40},
                24: {'dia': 0.61, 'od': 1.17, 'weight': 3.68, 'resistance': 93.20},
                26: {'dia': 0.48, 'od': 1.04, 'weight': 2.68, 'resistance': 147.00},
                28: {'dia': 0.38, 'od': 0.91, 'weight': 1.89, 'resistance': 244.00}
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
                20: {'dia': 0.97, 'od': 1.55, 'weight': 7.86, 'resistance': 37.40},
                22: {'dia': 0.76, 'od': 1.32, 'weight': 5.24, 'resistance': 61.00},
                24: {'dia': 0.61, 'od': 1.17, 'weight': 3.69, 'resistance': 98.70},
                26: {'dia': 0.48, 'od': 1.04, 'weight': 2.69, 'resistance': 162.00},
                28: {'dia': 0.38, 'od': 0.91, 'weight': 1.90, 'resistance': 259.00}
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
                12: {'dia': 0.00, 'od': 2.62, 'weight': 29.00, 'resistance': 6.63},
                14: {'dia': 0.00, 'od': 2.16, 'weight': 19.00, 'resistance': 10.00},
                16: {'dia': 0.00, 'od': 1.73, 'weight': 12.30, 'resistance': 15.80},
                18: {'dia': 0.00, 'od': 1.52, 'weight': 9.67, 'resistance': 20.40},
                20: {'dia': 0.00, 'od': 1.27, 'weight': 6.40, 'resistance': 32.40},
                22: {'dia': 0.00, 'od': 1.09, 'weight': 4.17, 'resistance': 53.20},
                24: {'dia': 0.00, 'od': 0.94, 'weight': 2.98, 'resistance': 86.00},
                26: {'dia': 0.00, 'od': 0.81, 'weight': 2.08, 'resistance': 136.00},
                28: {'dia': 0.00, 'od': 0.68, 'weight': 1.35, 'resistance': 225.00},
                30: {'dia': 0.00, 'od': 0.61, 'weight': 0.98, 'resistance': 330.00}
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
    mfg_id = _manufacturers.get_mfg_id(con, 'TE')

    family_id = _families.get_family_id(con, 'Tefzel', mfg_id)

    for series, wire_data in mapping.items():
        series_id = _series.get_series_id(con, series, 2)
        plating_id = _platings.get_plating_id(con, wire_data['con_plate'])
        min_temp = str(wire_data['min_temp']) + '°C'
        max_temp = '+' + str(wire_data['max_temp']) + '°C'
        min_temp_id = _temperatures.get_temperature_id(con, min_temp)
        max_temp_id = _temperatures.get_temperature_id(con, max_temp)
        volts = wire_data['volts']
        material_id = _materials.get_material_id(con, wire_data['material'])

        for awg in range(wire_data['start'], wire_data['stop'], wire_data['step']):
            if awg not in wire_data['data']:
                continue

            dia = wire_data['data'][awg]['dia']
            od_mm = wire_data['data'][awg]['od']
            weight = wire_data['data'][awg]['weight'] * 1000.0
            resistance = wire_data['data'][awg]['resistance']

            mm_2 = __awg_to_mm2(awg)

            image_id = 0
            datasheet_id = 0
            cad_id = 0

            for p_id in range(10):
                part_number = pn_template.format(series=series, awg=awg, primary=p_id, secondary='')
                description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]} Tefzel milspec single conductor wire'
                s_id = 999999
                num_conductors = 1
                shielded = 0
                tpi = 0.0

                values.append((part_number, description, mfg_id, family_id, series_id,
                               p_id, image_id, datasheet_id, cad_id,  min_temp_id,
                               max_temp_id, material_id, s_id, plating_id, num_conductors,
                               shielded, tpi, dia, mm_2, awg, od_mm, weight, resistance, volts))
                for s_id in range(10):
                    if p_id == s_id:
                        continue
                    description = f'{awg}AWG ({mm_2}mm²) {color_mapping[p_id]}/{color_mapping[s_id]} Tefzel milspec single conductor wire'

                    values.append((part_number + str(s_id), description, mfg_id,
                                   family_id, series_id, p_id, image_id, datasheet_id,
                                   cad_id,  min_temp_id, max_temp_id, material_id,
                                   s_id, plating_id, num_conductors, shielded, tpi, dia,
                                   mm_2, awg, od_mm, weight, resistance, volts))

    return values
