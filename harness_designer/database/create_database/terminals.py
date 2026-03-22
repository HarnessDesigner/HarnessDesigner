import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import genders as _genders
from . import platings as _platings
from . import cavity_locks as _cavity_locks
from . import temperatures as _temperatures
from . import colors as _colors
from . import models3d as _models3d

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import circuits as _circuits
from . import cavities as _cavities

from .. import db_connectors as _con
from ... import logger as _logger


def add_terminal(con, part_number, description, mfg=None, family=None, series=None,
                 color=None, image=None, datasheet=None, cad=None, min_temp=None,
                 max_temp=None, model3d=None, plating=None, gender=None, cavity_lock=None,
                 sealing=0, blade_size=0.0, resistance=0.0, mating_cycles=0, max_vibration_g=0,
                 max_current_ma=0, wire_size_min_awg=-1, wire_size_max_awg=-1, wire_dia_min=0.0,
                 wire_dia_max=0.0, min_wire_cross=0.0, max_wire_cross=0.0, length=0.0,
                 width=0.0, height=0.0, weight=0.0, compat_housings=None, compat_seals=None):

    if compat_housings is None:
        compat_housings = []

    if compat_seals is None:
        compat_seals = []

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cavity_lock)
    plating_id = _platings.get_plating_id(con, plating)
    gender_id = _genders.get_gender_id(con, gender)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)

    if not width and blade_size:
        width = blade_size

    if not height and blade_size:
        height = blade_size

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if gender:
            description += f' {gender}'

        if blade_size:
            description += f' {blade_size}mm'

        if plating:
            description += f' {plating}'

        if min_wire_cross:
            description += f' {min_wire_cross}mm²'

        if max_wire_cross:
            if min_wire_cross:
                description += f' -'

            description += f' {max_wire_cross}mm²'

        description += ' Terminal'

    _logger.logger.database(f'adding terminal {part_number}, {description}')

    con.execute('INSERT INTO terminals (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, plating_id, gender_id, cavity_lock_id, '
                'sealing, blade_size, resistance, mating_cycles, max_vibration_g, '
                'max_current_ma, wire_size_min_awg, wire_size_max_awg, wire_dia_min, '
                'wire_dia_max, min_wire_cross, max_wire_cross, length, width, height, '
                'weight, compat_housings, compat_seals) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 plating_id, gender_id, cavity_lock_id, sealing, blade_size, resistance,
                 mating_cycles, max_vibration_g, max_current_ma, wire_size_min_awg,
                 wire_size_max_awg, wire_dia_min, wire_dia_max, min_wire_cross,
                 max_wire_cross, length, width, height, weight, str(compat_housings),
                 str(compat_seals)))

    con.commit()
    db_id = con.lastrowid

    _logger.logger.database(f'terminal added "{part_number}" = {db_id}')


def add_pjt_terminal(con, project_id, part_id, cavity_id=None, circuit_id=None,
                     wire_point3d_id=None, point3d_id=None, point2d_id=None,
                     wire_point2d_id=None, name='', notes='', quat3d=None,
                     angle3d=None, quat2d=None, angle2d=None, is_start=0, volts=0.0,
                     load=0.0, voltage_drop=0.0, is_visible3d=0, is_visible2d=0):

    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [0.0, 0.0, 0.0]

    if quat2d is None:
        quat2d = [1.0, 0.0, 0.0, 0.0]

    if angle2d is None:
        angle2d = [0.0, 0.0, 0.0]

    con.execute('INSERT INTO pjt_terminals (project_id, part_id, cavity_id, circuit_id, '
                'wire_point3d_id, point3d_id, point2d_id, wire_point2d_id, name, notes, '
                'quat3d, angle3d, quat2d, angle2d, is_start, volts, load, voltage_drop, '
                'is_visible3d, is_visible2d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, cavity_id, circuit_id, wire_point3d_id, point3d_id,
                 point2d_id, wire_point2d_id, name, notes, str(quat3d), str(angle3d),
                 str(quat2d), str(angle2d), is_start, volts, load, voltage_drop,
                 is_visible3d, is_visible2d))

    con.commit()


def add_terminals(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_terminal(con, **line)


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM terminals WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding terminal to db [1 | 1]...')
    splash.flush()

    con.execute('INSERT INTO terminals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    dirs = []
    for file in os.listdir(data_path):
        file = os.path.join(data_path, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'terminals.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading terminals file...')
            splash.flush()

            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding terminals to db [0 | {data_len}]...')
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding terminals to db [{i + 1} | {data_len}]...')

                pn = item['part_number']
                con.execute(f'SELECT id FROM terminals WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    if 'shared_cad' in item:
                        del item['shared_cad']

                    if 'shared_model3d' in item:
                        del item['shared_model3d']

                    add_terminal(con, **item)

            con.commit()
    os.chdir(cwd)


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'terminals',
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
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('plating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('gender_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_genders.table,
                                                    _genders.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cavity_lock_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cavity_locks.table,
                                                    _cavity_locks.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('sealing', default='0', no_null=True),
    _con.FloatField('blade_size', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.IntField('mating_cycles', default='0', no_null=True),
    _con.IntField('max_vibration_g', default='0', no_null=True),
    _con.IntField('max_current_ma', default='0', no_null=True),
    _con.IntField('wire_size_min_awg', default='-1', no_null=True),
    _con.IntField('wire_size_max_awg', default='-1', no_null=True),
    _con.FloatField('wire_dia_min', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_max', default='"0.0"', no_null=True),
    _con.FloatField('min_wire_cross', default='"0.0"', no_null=True),
    _con.FloatField('max_wire_cross', default='"0.0"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('compat_housings', default='"[]"', no_null=True),
    _con.TextField('compat_seals', default='"[]"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_terminals',
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
    _con.IntField('cavity_id', no_null=True,
                  references=_con.SQLFieldReference(_cavities.pjt_table,
                                                    _cavities.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', no_null=True,
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('wire_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('wire_point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_start', default='1', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True),
    _con.FloatField('load', default='"0.0"', no_null=True),
    _con.FloatField('voltage_drop', default='"0.0"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True)

)
