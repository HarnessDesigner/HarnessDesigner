import os
import json

from . import temperatures as _temperatures
from . import manufacturers as _manufacturers
from . import series as _series
from . import colors as _colors
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import models3d as _models3d
from . import seal_types as _seal_types
from . import families as _families

from . import projects as _projects
from . import points3d as _points3d
from . import housings as _housings
from . import cavities as _cavities
from . import terminals as _terminals

from harness_designer.database import db_connectors as _con
from ... import logger as _logger


def add_seal(con, part_number, description, mfg=None, family=None, series=None,
             color=None, image=None, datasheet=None, cad=None, min_temp=None,
             max_temp=None, model3d=None, type=None, hardness=-1, lubricant='',
             length=0.0, width=0.0, height=0.0, weight=0.0, o_dia=0.0, i_dia=0.0,
             wire_dia_min=0.0, wire_dia_max=0.0, compat_housings=None, compat_terminals=None):

    if compat_housings is None:
        compat_housings = []

    if compat_terminals is None:
        compat_terminals = []

    if color is None:
        color = 'Dark Gray'

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)
    type_id = _seal_types.get_seal_type_id(con, type)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        if wire_dia_min:
            description += f' {wire_dia_min}mm'

        if wire_dia_max:
            if wire_dia_min:
                description += f' -'

            description += f' {wire_dia_max}mm'

        if type:
            description += f' {type}'

        description += ' Seal'

    _logger.logger.database(f'adding seal {part_number}, {description}')
    con.execute('INSERT INTO seals (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, type_id, hardness, lubricant, length, '
                'width, height, weight, o_dia, i_dia, wire_dia_min, wire_dia_max, '
                'compat_housings, compat_terminals) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 type_id, hardness, lubricant, length, width, height, weight, o_dia,
                 i_dia, wire_dia_min, wire_dia_max, str(compat_housings), str(compat_terminals)))

    con.commit()
    db_id = con.lastrowid

    _logger.logger.database(f'seal added "{part_number}" = {db_id}')


def add_pjt_seal(con, project_id, part_id, point3d_id=None, housing_id=None,
                 terminal_id=None, name='', notes='', quat3d=None, angle3d=None,
                 is_visible3d=0):

    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [0.0, 0.0, 0.0]

    con.execute('INSERT INTO pjt_seals (project_id, part_id, point3d_id, housing_id, '
                'terminal_id, name, notes, quat3d, angle3d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, point3d_id, housing_id, terminal_id, name,
                 notes, str(quat3d), str(angle3d), is_visible3d))

    con.commit()


def add_seals(con, data: tuple[dict] | list[dict]):
    for line in data:
        add_seal(con, **line)


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM seals WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding seal to db [1 | 1]...')
    splash.flush()

    con.execute('INSERT INTO seals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    dirs = []
    for file in os.listdir(data_path):
        file = os.path.join(data_path, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'seals.json')
        if os.path.exists(json_path):
            splash.SetText(f'Loading seals file...')
            splash.flush()

            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding seals to db [0 | {data_len}]...')
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding seals to db [{i + 1} | {data_len}]...')

                pn = item['part_number']
                con.execute(f'SELECT id FROM seals WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    if 'shared_cad' in item:
                        del item['shared_cad']

                    if 'shared_model3d' in item:
                        del item['shared_model3d']

                    add_seal(con, **item)

        con.commit()
    os.chdir(cwd)


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'seals',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.table,
                                                    _series.id_field,
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
    _con.IntField('type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_seal_types.table,
                                                    _seal_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('hardness', default='-1', no_null=True),
    _con.TextField('lubricant', default='""', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.FloatField('o_dia', default='"0.0"', no_null=True),
    _con.FloatField('i_dia', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_min', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_max', default='"0.0"', no_null=True),
    _con.TextField('compat_housings', default='"[]"', no_null=True),
    _con.TextField('compat_terminals', default='"[]"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_seals',
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
    _con.IntField('terminal_id', no_null=True,
                  references=_con.SQLFieldReference(_terminals.pjt_table,
                                                    _terminals.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
