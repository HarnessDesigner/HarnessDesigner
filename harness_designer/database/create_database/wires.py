# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import json

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
from . import concentric_layers as _concentric_layers


from harness_designer.database import db_connectors as _con
from ... import logger as _logger


def add_wires(con, data: tuple[dict] | list[dict]):
    """Add a wires.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """
    for line in data:
        add_wire(con, **line)


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
    con.execute('SELECT id FROM wires WHERE id=1;')
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

        json_path = os.path.join(path, 'wires.json')

        if os.path.exists(json_path):

            splash.SetText(f'Loading {name}wires file...')
            splash.flush()

            _logger.database(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding {name}wire to db [0 | {data_len}]...', log=False)
            splash.flush()

            for i, item in enumerate(data):
                splash.SetText(f'Adding {name}wire to db [{i + 1} | {data_len}]...', log=False)

                try:
                    add_wire(con, commit=False, **item)
                except Exception as err:
                    _logger.traceback(err)

            con.commit()

    os.chdir(cwd)


def add_wire(con, part_number, description, mfg=None, family=None, series=None,
             color=None, image=None, datasheet=None, cad=None, min_temp=None,
             max_temp=None, material=None, stripe_color=None, core_material=None,
             num_conductors=1, shielded=0, tpi=0.0, wire_size_dia=None, wire_size_cross=None,
             wire_size_awg=None, od_mm=0.0, weight_1km=0.0, resistance_1km=0.0, volts=0.0,
             strands=1, commit=True):
    """Add a wire.

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
    :param stripe_color: Value for ``stripe_color``.
    :type stripe_color: UNKNOWN
    :param core_material: Value for ``core_material``.
    :type core_material: UNKNOWN
    :param num_conductors: Value for ``num_conductors``.
    :type num_conductors: UNKNOWN
    :param shielded: Value for ``shielded``.
    :type shielded: UNKNOWN
    :param tpi: Value for ``tpi``.
    :type tpi: UNKNOWN
    :param wire_size_dia: Value for ``wire_size_dia``.
    :type wire_size_dia: UNKNOWN
    :param wire_size_cross: Value for ``wire_size_cross``.
    :type wire_size_cross: UNKNOWN
    :param wire_size_awg: Value for ``wire_size_awg``.
    :type wire_size_awg: UNKNOWN
    :param od_mm: Value for ``od_mm``.
    :type od_mm: UNKNOWN
    :param weight_1km: Value for ``weight_1km``.
    :type weight_1km: UNKNOWN
    :param resistance_1km: Value for ``resistance_1km``.
    :type resistance_1km: UNKNOWN
    :param volts: Value for ``volts``.
    :type volts: UNKNOWN
    :param strands: Value for ``strands``.
    :type strands: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    core_material_id = _platings.get_plating_id(con, core_material)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    stripe_color_id = _colors.get_color_id(con, stripe_color)
    material_id = _materials.get_material_id(con, material)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)

    con.execute('INSERT INTO wires (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, material_id, stripe_color_id, core_material_id, '
                'num_conductors, shielded, tpi, wire_size_dia, wire_size_cross, wire_size_awg, '
                'od_mm, weight_1km, resistance_1km, volts, strands) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, material_id,
                 stripe_color_id, core_material_id, num_conductors, shielded, tpi,
                 wire_size_dia, wire_size_cross, wire_size_awg, od_mm, weight_1km, resistance_1km,
                 volts, strands))

    _logger.database(f'wire added "{part_number}"')

    if commit:
        con.commit()
        return con.lastrowid


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
    _con.FloatField('wire_size_dia', default='NULL'),
    _con.FloatField('wire_size_cross', default='NULL'),
    _con.IntField('wire_size_awg', default='NULL'),
    _con.FloatField('od_mm', no_null=True),
    _con.FloatField('weight_1km', default='"0.0"', no_null=True),
    _con.FloatField('resistance_1km', default='"0.0"', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True),
    _con.IntField('strands', default='1'),
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
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('bundle_id', default='NULL',
                  references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                    _bundle_covers.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('transition_id', default='NULL',
                  references=_con.SQLFieldReference(_transitions.pjt_table,
                                                    _transitions.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('start_point3d_id', default="NULL",
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point3d_id', default="NULL",
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('start_point2d_id', default="NULL",
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point2d_id', default="NULL",
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('layer_view_point_id', default="NULL",
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('layer_id', default="NULL",
                  references=_con.SQLFieldReference(_concentric_layers.pjt_table,
                                                    _concentric_layers.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('is_filler_wire', default='0', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.TextField('name', default='""', no_null=True),
    # Offset (mm) into the shared stripe helix mesh where this wire
    # segment's own start sits -- 0.0 for a standalone wire, otherwise
    # inherited/pushed from whichever wire's stop_point3d_id equals this
    # wire's start_point3d_id. Only meaningful for wires with a stripe
    # (see PJTWire.has_stripe). See objects.objects3d.wire.Wire and
    # gl.shaders.faces' stripeClipStart/stripeClipStop uniforms.
    _con.FloatField('stripe_clip_start', default='"0.0"', no_null=True)
)
