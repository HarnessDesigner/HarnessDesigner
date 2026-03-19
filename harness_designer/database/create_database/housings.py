import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import models3d as _models3d
from . import directions as _directions
from . import temperatures as _temperatures
from . import cavity_locks as _cavity_locks
from . import genders as _genders
from . import ip_ratings as _ip_ratings
from . import cpa_lock_types as _cpa_lock_types
from . import seal_types as _seal_types

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from .. import db_connectors as _con
from ... import logger as _logger


def add_housing(con, part_number, description, mfg=None, family=None, series=None,
                color=None, image=None, datasheet=None, cad=None, min_temp=None,
                max_temp=None, model3d=None, direction=None, gender=None, cavity_lock=None,
                ip_rating='IP00', seal_type=None, cpa_lock_type=None, sealing=0, rows=0,
                num_pins=0, terminal_sizes=None, terminal_size_counts=None, centerline=0.0,
                compat_cpas=None, compat_tpas=None, compat_covers=None, compat_terminals=None,
                compat_seals=None, compat_housings=None, compat_boots=None, length=0.0,
                width=0.0, height=0.0, weight=0.0, cover_point3d=None, seal_point3d=None,
                boot_point3d=None, tpa_lock_1_point3d=None, tpa_lock_2_point3d=None,
                cpa_lock_point3d=None):

    if compat_cpas is None:
        compat_cpas = []

    if compat_tpas is None:
        compat_tpas = []

    if compat_covers is None:
        compat_covers = []

    if compat_terminals is None:
        compat_terminals = []

    if compat_seals is None:
        compat_seals = []

    if compat_housings is None:
        compat_housings = []

    if compat_boots is None:
        compat_boots = []

    if cover_point3d is None:
        cover_point3d = [0.0, 0.0, 0.0]

    if seal_point3d is None:
        seal_point3d = [0.0, 0.0, 0.0]

    if boot_point3d is None:
        boot_point3d = [0.0, 0.0, 0.0]

    if tpa_lock_1_point3d is None:
        tpa_lock_1_point3d = [0.0, 0.0, 0.0]

    if tpa_lock_2_point3d is None:
        tpa_lock_2_point3d = [0.0, 0.0, 0.0]

    if cpa_lock_point3d is None:
        cpa_lock_point3d = [0.0, 0.0, 0.0]

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    direction_id = _directions.get_direction_id(con, direction)
    color_id = _colors.get_color_id(con, color)

    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cavity_lock)
    gender_id = _genders.get_gender_id(con, gender)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)
    ip_rating_id = _ip_ratings.get_ip_rating_id(con, ip_rating)
    seal_type_id = _seal_types.get_seal_type_id(con, seal_type)
    cpa_lock_type_id = _cpa_lock_types.get_cpa_lock_type_id(con, cpa_lock_type)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if num_pins:
            description += f' {num_pins} cavity'

        if gender:
            description += f' {gender}'

        if terminal_sizes:
            t_sizes = eval(terminal_sizes)
            for t_size in t_sizes:
                description += f' {t_size}mm'

        description += ' Housing'

    con.execute('INSERT INTO housings (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, direction_id, gender_id, cavity_lock_id, '
                'ip_rating_id, seal_type_id, cpa_lock_type_id, sealing, rows, num_pins, '
                'terminal_sizes, terminal_size_counts, centerline, compat_cpas, '
                'compat_tpas, compat_covers, compat_terminals, compat_seals, '
                'compat_housings, compat_boots, length, width, height, weight, '
                'cover_point3d, seal_point3d, boot_point3d, tpa_lock_1_point3d, '
                'tpa_lock_2_point3d, cpa_lock_point3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 direction_id, gender_id, cavity_lock_id, ip_rating_id, seal_type_id,
                 cpa_lock_type_id, sealing, rows, num_pins, str(terminal_sizes),
                 str(terminal_size_counts), centerline, str(compat_cpas), str(compat_tpas),
                 str(compat_covers), str(compat_terminals), str(compat_seals),
                 str(compat_housings), str(compat_boots), length, width, height,
                 weight, str(cover_point3d), str(seal_point3d), str(boot_point3d),
                 str(tpa_lock_1_point3d), str(tpa_lock_2_point3d), str(cpa_lock_point3d)))

    con.commit()


def add_housings(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_housing(con, **line)


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM housings WHERE id=0;')

    if con.fetchall():
        return

    splash.SetText(f'Adding core housing to db [1 | 1]...')

    con.execute('INSERT INTO housings (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    dirs = []
    for file in os.listdir(data_path):
        file = os.path.join(data_path, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'housings.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading housings file...')
            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding housings to db [0 | {data_len}]')
            for i, item in enumerate(data):
                splash.SetText(f'Adding housings to db [{i + 1} | {data_len}]')

                pn = item['part_number']
                con.execute(f'SELECT id FROM housings WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    if 'shared_cad' in item:
                        del item['shared_cad']

                    if 'shared_model3d' in item:
                        del item['shared_model3d']

                    add_housing(con, **item)

        con.commit()
    os.chdir(cwd)


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'housings',
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
    _con.IntField('gender_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_genders.table,
                                                    _genders.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('direction_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_directions.table,
                                                    _directions.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cavity_lock_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cavity_locks.table,
                                                    _cavity_locks.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('ip_rating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_ip_ratings.table,
                                                    _ip_ratings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('seal_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_seal_types.table,
                                                    _seal_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cpa_lock_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cpa_lock_types.table,
                                                    _cpa_lock_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('sealing', default='0', no_null=True),
    _con.IntField('rows', default='0', no_null=True),
    _con.IntField('num_pins', default='0', no_null=True),
    _con.TextField('terminal_sizes', default='"[]"', no_null=True),
    _con.TextField('terminal_size_counts', default='"[]"', no_null=True),
    _con.FloatField('centerline', default='"0.0"', no_null=True),
    _con.TextField('compat_cpas', default='"[]"', no_null=True),
    _con.TextField('compat_tpas', default='"[]"', no_null=True),
    _con.TextField('compat_covers', default='"[]"', no_null=True),
    _con.TextField('compat_terminals', default='"[]"', no_null=True),
    _con.TextField('compat_seals', default='"[]"', no_null=True),
    _con.TextField('compat_housings', default='"[]"', no_null=True),
    _con.TextField('compat_boots', default='"[]"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('cover_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('seal_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('boot_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('tpa_lock_1_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('tpa_lock_2_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('cpa_lock_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_housings',
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

    _con.IntField('cover_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('seal_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('boot_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('tpa_lock_1_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('tpa_lock_2_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cpa_lock_point3d_id', no_null=True,
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


    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
