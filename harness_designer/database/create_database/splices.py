import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import materials as _materials
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import platings as _platings
from . import splice_types as _splice_types
from . import temperatures as _temperatures
from . import models3d as _models3d

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import circuits as _circuits

from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM splices WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding splice to db [1 | 1]...')
    con.execute('INSERT INTO splices (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    dirs = []
    for file in os.listdir(data_path):
        file = os.path.join(data_path, file)
        if os.path.isdir(file):
            dirs.append(file)

    cwd = os.getcwd()
    for path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'splices.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading splices file...')
            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            for i, item in enumerate(data):
                splash.SetText(f'Adding splices to db [{i + 1} | {data_len}]')

                pn = item['part_number']
                con.execute(f'SELECT id FROM splices WHERE part_number="{pn}";')
                rows = con.fetchall()
                if not rows:
                    add_splice(con, **item)

        con.commit()
    os.chdir(cwd)


def add_splices(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_splice(con, **line)


def add_splice(con, part_number, description, mfg=None, family=None, series=None,
               color=None, image=None, datasheet=None, cad=None, min_temp=None,
               max_temp=None, model3d=None, material=None, plating=None,  type=None,  # NOQA
               min_dia=0.0, max_dia=0.0, resistance=0.0, length=0.0, weight=0.0):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    image_id = _images.get_image_id(con, image)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    cad_id = _cads.get_cad_id(con, cad)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    plating_id = _platings.get_plating_id(con, plating)
    type_id = _splice_types.get_splice_type_id(con, type)
    model3d_id = _models3d.get_model3d_id(con, model3d)

    con.execute('INSERT INTO splices (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, material_id, plating_id, type_id, min_dia, '
                'max_dia, resistance, length, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 material_id, plating_id, type_id, min_dia, max_dia, resistance,
                 length, weight))
    con.commit()


def add_pjt_splice(con, project_id, part_id, start_point3d_id=None, stop_point3d_id=None,
                   branch_point3d_id=None, point2d_id=None, circuit_id=None, name='',
                   notes='', is_visible2d=0, is_visible3d=0):

    con.execute('INSERT INTO pjt_splices (project_id, part_id, start_point3d_id, '
                'stop_point3d_id, branch_point3d_id, point2d_id, circuit_id, name, '
                'notes, is_visible2d, is_visible3d) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, start_point3d_id, stop_point3d_id, branch_point3d_id,
                 point2d_id, circuit_id, name, notes, is_visible2d, is_visible3d))

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'splices',
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
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('plating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_splice_types.table,
                                                    _splice_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('min_dia', default='"0.0"', no_null=True),
    _con.FloatField('max_dia', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_splices',
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

    _con.IntField('branch_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', no_null=True,
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
