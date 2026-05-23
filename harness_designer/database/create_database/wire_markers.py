# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os

from . import manufacturers as _manufacturers
from . import colors as _colors
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import series as _series
from . import families as _families
from . import temperatures as _temperatures

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import wires as _wires

from .. import db_connectors as _con
from ... import logger as _logger


def add_wire_markers(con, data: tuple[dict] | list[dict]):
    """Add a wire markers.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_wire_marker(con, **line)


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
    con.execute('SELECT id FROM wire_markers WHERE id=1;')
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

        json_path = os.path.join(path, 'wire_markers.json')

        if os.path.exists(json_path):
            splash.SetText(f'Loading {name}wire markers file...')
            splash.flush()

            _logger.logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding {name}wire marker to db [0 | {data_len}]...', log=False)
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding {name}wire marker to db [{i + 1} | {data_len}]...', log=False)

                try:
                    add_wire_marker(con, commit=False, **item)
                except Exception as err:
                    _logger.logger.traceback(err)

            con.commit()

    os.chdir(cwd)


def add_wire_marker(con, part_number, description, mfg=None, family=None, series=None,
                    color=None, image=None, datasheet=None, cad=None, min_temp=None,
                    max_temp=None, min_diameter=0.0, max_diameter=0.0, wire_size_awg_min=None,
                    wire_size_awg_max=None, wire_size_dia_min=None, wire_size_dia_max=None,
                    wire_size_cross_min=None, wire_size_cross_max=None, length=0.0,
                    weight=0.0, has_label=0, commit=True):
    """Add a wire marker.

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
    :param min_diameter: Value for ``min_diameter``.
    :type min_diameter: UNKNOWN
    :param max_diameter: Value for ``max_diameter``.
    :type max_diameter: UNKNOWN
    :param wire_size_awg_min: Value for ``wire_size_awg_min``.
    :type wire_size_awg_min: UNKNOWN
    :param wire_size_awg_max: Value for ``wire_size_awg_max``.
    :type wire_size_awg_max: UNKNOWN
    :param wire_size_dia_min: Value for ``wire_size_dia_min``.
    :type wire_size_dia_min: UNKNOWN
    :param wire_size_dia_max: Value for ``wire_size_dia_max``.
    :type wire_size_dia_max: UNKNOWN
    :param wire_size_cross_min: Value for ``wire_size_cross_min``.
    :type wire_size_cross_min: UNKNOWN
    :param wire_size_cross_max: Value for ``wire_size_cross_max``.
    :type wire_size_cross_max: UNKNOWN
    :param length: Value for ``length``.
    :type length: UNKNOWN
    :param weight: Value for ``weight``.
    :type weight: UNKNOWN
    :param has_label: Boolean flag for whether label is available.
    :type has_label: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    image_id = _images.get_image_id(con, image)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    cad_id = _cads.get_cad_id(con, cad)

    con.execute('INSERT INTO wire_markers (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, min_diameter, max_diameter, wire_size_awg_min, wire_size_awg_max, '
                'wire_size_dia_min, wire_size_dia_max, wire_size_cross_min, wire_size_cross_max, '
                'length, weight, has_label) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, min_diameter,
                 max_diameter, wire_size_awg_min, wire_size_awg_max, wire_size_dia_min,
                 wire_size_dia_max, wire_size_cross_min, wire_size_cross_max, length,
                 weight, has_label))

    _logger.logger.database(f'wire marker added "{part_number}"')

    if commit:
        con.commit()
        return con.lastrowid


def add_pjt_wire_marker(con, project_id, part_id, point3d_id=None, point2d_id=None,
                        wire_id=None, name='', notes='', label='', is_visible2d=1,
                        is_visible3d=1):
    """Add a PJT wire marker.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param project_id: Identifier for the project.
    :type project_id: UNKNOWN
    :param part_id: Identifier for the part.
    :type part_id: UNKNOWN
    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: UNKNOWN
    :param point2d_id: Identifier for the point 2D.
    :type point2d_id: UNKNOWN
    :param wire_id: Identifier for the wire.
    :type wire_id: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param notes: Value for ``notes``.
    :type notes: UNKNOWN
    :param label: Value for ``label``.
    :type label: UNKNOWN
    :param is_visible2d: Boolean flag for whether visible 2D.
    :type is_visible2d: UNKNOWN
    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: UNKNOWN
    """

    con.execute('INSERT INTO pjt_wire_markers (project_id, part_id, point3d_id, '
                'point2d_id, wire_id, name, notes, label, is_visible2d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, point3d_id, point2d_id, wire_id, name, notes,
                 label, is_visible2d, is_visible3d))

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'wire_markers',
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
    _con.FloatField('min_diameter', default='"0.0"', no_null=True),
    _con.FloatField('max_diameter', default='"0.0"', no_null=True),
    _con.IntField('wire_size_awg_min', default='NULL'),
    _con.IntField('wire_size_awg_max', default='NULL'),
    _con.FloatField('wire_size_dia_min', default='NULL'),
    _con.FloatField('wire_size_dia_max', default='NULL'),
    _con.FloatField('wire_size_cross_min', default='NULL'),
    _con.FloatField('wire_size_cross_max', default='NULL'),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.IntField('has_label', default='0', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_wire_markers',
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
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('wire_id', no_null=True,
                  references=_con.SQLFieldReference(_wires.pjt_table,
                                                    _wires.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('label', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)
