# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
# from . import adhesives as _adhesives
from . import protections as _protections
from . import temperatures as _temperatures

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con
from ... import logger as _logger


def add_bundle_covers(con, data: tuple[dict] | list[dict]):
    """
    Add a bundle covers.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_bundle_cover(con, **line)


def add_records(con, splash, data_path):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """

    con.execute('SELECT id FROM bundle_covers WHERE id=1;')
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

        json_path = os.path.join(path, 'bundles.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading {name}bundle covers file...')
            splash.flush()

            _logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)
            splash.SetText(f'Adding {name}bundle cover to db [0 | {data_len}]', log=False)
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding {name}bundle cover to db [{i + 1} | {data_len}]', log=False)

                try:
                    add_bundle_cover(con, commit=False, **item)
                except Exception as err:
                    _logger.traceback(err)

            con.commit()

    os.chdir(cwd)


def add_bundle_cover(con, part_number, description, mfg=None, family=None, series=None,
                     color=None, material=None, image=None, datasheet=None, cad=None,
                     shrink_temp=None, min_temp=None, max_temp=None, protection=None,
                     rigidity='', shrink_ratio='', wall='', min_dia=0.0, max_dia=0.0,
                     adhesive_ids=None, weight=0.0, commit=True):
    """
    Add a bundle cover.

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

    :param material: Value for ``material``.
    :type material: UNKNOWN

    :param image: Value for ``image``.
    :type image: UNKNOWN

    :param datasheet: Value for ``datasheet``.
    :type datasheet: UNKNOWN

    :param cad: Value for ``cad``.
    :type cad: UNKNOWN

    :param shrink_temp: Value for ``shrink_temp``.
    :type shrink_temp: UNKNOWN

    :param min_temp: Value for ``min_temp``.
    :type min_temp: UNKNOWN

    :param max_temp: Value for ``max_temp``.
    :type max_temp: UNKNOWN

    :param protection: Value for ``protection``.
    :type protection: UNKNOWN

    :param rigidity: Value for ``rigidity``.
    :type rigidity: UNKNOWN

    :param shrink_ratio: Value for ``shrink_ratio``.
    :type shrink_ratio: UNKNOWN

    :param wall: Value for ``wall``.
    :type wall: UNKNOWN

    :param min_dia: Value for ``min_dia``.
    :type min_dia: UNKNOWN

    :param max_dia: Value for ``max_dia``.
    :type max_dia: UNKNOWN

    :param adhesive_ids: Identifier for the adhesive.
    :type adhesive_ids: UNKNOWN

    :param weight: Value for ``weight``.
    :type weight: UNKNOWN

    :param commit: Value for ``commit``.
    :type commit: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if adhesive_ids is None:
        adhesive_ids = []

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    image_id = _images.get_image_id(con, image)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    cad_id = _cads.get_cad_id(con, cad)
    shrink_temp_id = _temperatures.get_temperature_id(con, shrink_temp)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    protection_id = _protections.get_protection_id(con, protection)

    adhesive_ids = ', '.join(adhesive_ids)

    con.execute('INSERT INTO bundle_covers (part_number, description, mfg_id, family_id, '
                'series_id, color_id, material_id, image_id, datasheet_id, cad_id, '
                'shrink_temp_id, min_temp_id, max_temp_id, protection_id, rigidity, '
                'shrink_ratio, wall, min_dia, max_dia, adhesive_ids, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id, material_id,
                 image_id, datasheet_id, cad_id, shrink_temp_id, min_temp_id, max_temp_id,
                 protection_id, rigidity, shrink_ratio, wall, min_dia, max_dia, adhesive_ids,
                 weight))

    _logger.database(f'bundle cover added "{part_number}"')

    if commit:
        con.commit()
        return con.lastrowid


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'bundle_covers',
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
    _con.IntField('shrink_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('protection_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_protections.table,
                                                    _protections.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('rigidity', default='""', no_null=True),
    _con.IntField('shrink_ratio', default='""', no_null=True),
    _con.IntField('wall', default='""', no_null=True),
    _con.FloatField('min_dia', default='"0.0"', no_null=True),
    _con.FloatField('max_dia', default='"0.0"', no_null=True),
    _con.IntField('adhesive_ids', default='""', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_bundles',
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
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    # No SQLFieldReference to pjt_points_peg here (unlike the same column on
    # pjt_housings/pjt_transition_branches) -- pjt_points_peg's own schema
    # already references pjt_bundles (its bundle_id waypoint column), and
    # SQLFieldReference requires the real target SQLTable object at
    # construction time, not a lazy/string reference, so a real FK back the
    # other way here would be a circular module import. Still holds a
    # pjt_points_peg row id -- just without a DB-enforced constraint.
    _con.IntField('table_point_peg_id', default="NULL"),
    _con.IntField('table_hidden', default='0', no_null=True)
)
