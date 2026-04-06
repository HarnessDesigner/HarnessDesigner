
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

    for line in data:
        add_wire_marker(con, **line)


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM wire_markers WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding wire marker to db [1 | 1]...')
    splash.flush()

    con.execute('INSERT INTO wire_markers (id, part_number, description, mfg_id, '
                'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                'min_temp_id, max_temp_id, min_diameter, max_diameter, min_awg, '
                'max_awg, length, weight, has_label) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 'Internal Use DO NOT DELETE', 0, 0, 0, 999999, None, None,
                 None, 0, 0, 0.0, 0.0, -1, -1, 0.0, 0.0, 0))
    con.commit()

    json_path = os.path.join(data_path, 'wire_markers.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Wire Markers file...')
        splash.flush()

        _logger.logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding wire marker to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding wire marker to db [{i + 1} | {data_len}]...')
            add_wire_marker(con, **item)

    con.commit()


def add_wire_marker(con, part_number, description, mfg=None, family=None, series=None,
                    color=None, image=None, datasheet=None, cad=None, min_temp=None,
                    max_temp=None, min_diameter=0.0, max_diameter=0.0, min_awg=-1,
                    max_awg=-1, length=0.0, weight=0.0, has_label=0):

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
                'max_temp_id, min_diameter, max_diameter, min_awg, max_awg, length, '
                'weight, has_label) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, min_diameter,
                 max_diameter, min_awg, max_awg, length, weight, has_label))

    con.commit()


def add_pjt_wire_marker(con, project_id, part_id, point3d_id=None, point2d_id=None,
                        wire_id=None, name='', notes='', label='', is_visible2d=1,
                        is_visible3d=1):

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
    _con.IntField('min_awg', default='NULL'),
    _con.IntField('max_awg', default='NULL'),
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
