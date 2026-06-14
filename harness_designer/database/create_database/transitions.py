# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import temperatures as _temperatures
from . import colors as _colors
from . import materials as _materials
from . import shapes as _shapes
from . import protections as _protections
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import transition_branches as _transition_branches

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con
from ... import logger as _logger


def add_transition(con, part_number, description, mfg=None, family=None, series=None,
                   color=None, image=None, datasheet=None, cad=None, min_temp=None,
                   max_temp=None, material=None, shape=None, protection=None,
                   branch_count=0, adhesive_ids=None, weight=0.0, branches=[],
                   commit=True):
    """Add a transition.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param part_number: Value for ``part_number``.
    :type part_number: UNKNOWN
    :param description: Value for ``description``.
    :type description: UNKNOWN
    :param mfg: Value for ``mfg``.
    :type mfg: UNKNOWN
    :param family: Value for ``family``.
    :type family: UNKNOWN
    :param series: Value for ``series``.
    :type series: UNKNOWN
    :param color: Value for ``color``.
    :type color: UNKNOWN
    :param image: Value for ``image``.
    :type image: UNKNOWN
    :param datasheet: Value for ``datasheet``.
    :type datasheet: UNKNOWN
    :param cad: Value for ``cad``.
    :type cad: UNKNOWN
    :param min_temp: Value for ``min_temp``.
    :type min_temp: UNKNOWN
    :param max_temp: Value for ``max_temp``.
    :type max_temp: UNKNOWN
    :param material: Value for ``material``.
    :type material: UNKNOWN
    :param shape: Value for ``shape``.
    :type shape: UNKNOWN
    :param protection: Value for ``protection``.
    :type protection: UNKNOWN
    :param branch_count: Value for ``branch_count``.
    :type branch_count: UNKNOWN
    :param adhesive_ids: Identifier for the adhesive.
    :type adhesive_ids: UNKNOWN
    :param weight: Value for ``weight``.
    :type weight: UNKNOWN
    :param branches: Value for ``branches``.
    :type branches: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    """
    
    if adhesive_ids is None:
        adhesive_ids = []

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    shape_id = _shapes.get_shape_id(con, shape)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    protection_id = _protections.get_protection_id(con, protection)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)

    con.execute('INSERT INTO transitions (part_number, description, mfg_id, '
                'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                'min_temp_id, max_temp_id, material_id, shape_id, protection_id, '
                'branch_count, adhesive_ids, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, material_id,
                 shape_id, protection_id, branch_count,
                 str(adhesive_ids), weight))

    con.commit()
    _logger.logger.database(f'transition added "{part_number}"')

    transition_id = con.lastrowid

    for i, branch in enumerate(branches):
        try:
            _transition_branches.add_transition_branch(con, i, transition_id, commit=commit, **branch)
        except Exception as err:
            _logger.logger.traceback(err)


def add_pjt_transition(con, project_id, part_id, point3d_id=None, name='', notes='',
                       quat3d=None, angle3d=None, is_visible3d=1):
    """Add a PJT transition.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param project_id: Identifier for the project.
    :type project_id: UNKNOWN
    :param part_id: Identifier for the part.
    :type part_id: UNKNOWN
    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param notes: Value for ``notes``.
    :type notes: UNKNOWN
    :param quat3d: Value for ``quat3d``.
    :type quat3d: UNKNOWN
    :param angle3d: Value for ``angle3d``.
    :type angle3d: UNKNOWN
    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: UNKNOWN
    """
    
    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [0.0, 0.0, 0.0]

    con.execute('INSERT INTO pjt_transitions (project_id, part_id, point3d_id, name, '
                'notes, quat3d, angle3d, is_visible3d) VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, point3d_id, name, notes, quat3d, angle3d, is_visible3d))

    con.commit()


def add_transitions(con, data: tuple[dict] | list[dict]):
    """Add a transitions.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_transition(con, **line)


def add_records(con, splash, data_path):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """
    con.execute('SELECT id FROM transitions WHERE id=1;')
    if con.fetchall():
        return

    dirs = [('', data_path)]

    for file_name in os.listdir(data_path):
        file = os.path.join(data_path, file_name)
        if os.path.isdir(file):
            dirs.append((file_name + ' ', file))

    cwd = os.getcwd()
    for name, path in dirs:
        os.chdir(path)

        json_path = os.path.join(path, 'transitions.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading {name}trasitions file...')
            splash.flush()

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            data_len = len(data)

            splash.SetText(f'Adding {name}transition to db [0 | {data_len}]...', log=False)
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding {name}transition to db [{i + 1} | {data_len}]...', log=False)

                item['protection'] = '\n'.join(item['protection'])

                item['image'] = None
                item['datasheet'] = None
                item['cad'] = None

                try:
                    add_transition(con, commit=False, **item)
                except Exception as err:
                    _logger.logger.traceback(err)

            con.commit()

    os.chdir(cwd)


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'transitions',
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
    _con.IntField('shape_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_shapes.table,
                                                    _shapes.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('protection_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_protections.table,
                                                    _protections.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('branch_count', default='0', no_null=True),
    _con.TextField('adhesive_ids', default='"[]"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_transitions',
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

    _con.IntField('point3d_id', default="NULL",
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
