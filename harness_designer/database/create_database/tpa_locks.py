import os
import json

from . import temperatures as _temperatures
from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import models3d as _models3d

from . import projects as _projects
from . import points3d as _points3d
from . import housings as _housings

from .. import db_connectors as _con
from ... import logger as _logger


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_tpa_lock(con, part_number, description, mfg=None, family=None, series=None,
                 color=None, image=None, datasheet=None, cad=None, min_temp=None,
                 max_temp=None, model3d=None, lock_type='', length=0.0, width=0.0,
                 height=0.0, weight=0.0, pins=0, terminal_size=0.0, compat_housings=None):

    if compat_housings is None:
        compat_housings = []

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        description += ' TPA Lock'

    _logger.logger.database(f'adding tpa lock {part_number}, {description}')

    con.execute('INSERT INTO tpa_locks (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, lock_type, length, width, height, weight, '
                'pins, terminal_size, compat_housings) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 lock_type, length, width, height, weight, pins, terminal_size,
                 str(compat_housings)))

    con.commit()
    db_id = con.lastrowid

    _logger.logger.database(f'tpa lock added "{part_number}" = {db_id}')


def add_pjt_tpa_lock(con, project_id, part_id, point3d_id=None, housing_id=None,
                     name='', notes='', quat3d=None, angle3d=None, is_visible3d=0):

    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [1.0, 0.0, 0.0, 0.0]

    con.execute('INSERT INTO pjt_tpa_locks (project_id, part_id, point3d_id, housing_id, '
                'name, notes, quat3d, angle3d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, point3d_id, housing_id, name,
                 notes, str(quat3d), str(angle3d), is_visible3d))

    con.commit()


def add_tpa_locks(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_tpa_lock(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM tpa_locks WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding TPA lock to db [1 | 1]...')
    con.execute('INSERT INTO tpa_locks (id, part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, lock_type, length, width, height, weight, '
                'pins, terminal_size, compat_housings) VALUES '
                '(0, "N/A", "No TPA Lock", 0, 0, 0, 999999, NULL, NULL, NULL, '
                '0, 0, NULL, 0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, "[]");')

    dirs = []
    for file in os.listdir(DATA_PATH):
        file = os.path.join(DATA_PATH, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'tpa_locks.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading TPA locks file...')
            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            for i, item in enumerate(data):
                splash.SetText(f'Adding TPA locks to db [{i} | {data_len}]...')

                pn = item['part_number']
                con.execute(f'SELECT id FROM tpa_locks WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    if 'shared_cad' in item:
                        del item['shared_cad']

                    if 'shared_model3d' in item:
                        del item['shared_model3d']

                    add_tpa_lock(con, **item)

        con.commit()
    os.chdir(cwd)


id_field = _con.PrimaryKeyField('id')


table = _con.SQLTable(
    'tpa_locks',
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
    _con.TextField('lock_type', default='""', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.IntField('pins', default='0', no_null=True),
    _con.FloatField('terminal_size', default='"0.0"', no_null=True),
    _con.TextField('compat_housings', default='"[]"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_tpa_locks',
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

    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('housing_id', no_null=True,
                  references=_con.SQLFieldReference(_housings.pjt_table,
                                                    _housings.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
