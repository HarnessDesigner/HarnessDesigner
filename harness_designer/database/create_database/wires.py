# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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
from . import wire_types as _wire_types
from . import projects as _projects
from . import points2d as _points2d
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard
from . import circuits as _circuits
from . import bundle_covers as _bundle_covers
from . import transitions as _transitions
from . import concentric_layers as _concentric_layers
from harness_designer.database import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_wires(con: "_connector_base.ConnectorBase",
              data: tuple[dict] | list[dict]) -> None:

    """
    Add a wires.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_wire(con, **line)


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase",  # NOQA
                splash: "_splash_screen.Splash", data_path: str) -> None:  # NOQA

    """
    Add a records.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param splash: Value for ``splash``.
    :type splash: _splash_screen.Splash

    :param data_path: Value for ``data_path``.
    :type data_path: str
    """

    raise NotImplementedError


@_check_types.do
def add_wire(con: "_connector_base.ConnectorBase", part_number: str,
             description: str, mfg: str | None = None, family: str | None = None,
             series: str | None = None, color: str | None = None,
             image: str | None = None, datasheet: str | None = None,
             cad: str | None = None, min_temp: str | None = None,
             max_temp: str | None = None, material: str | None = None,
             stripe_color: str | None = None, core_material: str | None = None,
             num_conductors: int = 1, shielded: int = 0, tpi: float = 0.0,
             wire_size_dia: float | None = None,
             wire_size_cross: float | None = None,
             wire_size_awg: int | None = None, od_mm: float = 0.0,
             weight_1km: float = 0.0, resistance_1km: float = 0.0,
             volts: float = 0.0, strands: int = 1, wire_type: str | None = None,
             commit: bool = True) -> bytes:

    """
    Add a wire.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param part_number: Value for ``part_number``.
    :type part_number: str

    :param description: Value for ``description``.
    :type description: str

    :param mfg: Value for ``mfg``.
    :type mfg: str | None

    :param family: Value for ``family``.
    :type family: str | None

    :param series: Value for ``series``.
    :type series: str | None

    :param color: Value for ``color``.
    :type color: str | None

    :param image: Value for ``image``.
    :type image: str | None

    :param datasheet: Value for ``datasheet``.
    :type datasheet: str | None

    :param cad: Value for ``cad``.
    :type cad: str | None

    :param min_temp: Value for ``min_temp``.
    :type min_temp: str | None

    :param max_temp: Value for ``max_temp``.
    :type max_temp: str | None

    :param material: Value for ``material``.
    :type material: str | None

    :param stripe_color: Value for ``stripe_color``.
    :type stripe_color: str | None

    :param core_material: Value for ``core_material``.
    :type core_material: str | None

    :param num_conductors: Value for ``num_conductors``.
    :type num_conductors: int

    :param shielded: Value for ``shielded``.
    :type shielded: int

    :param tpi: Value for ``tpi``.
    :type tpi: float

    :param wire_size_dia: Value for ``wire_size_dia``.
    :type wire_size_dia: float | None

    :param wire_size_cross: Value for ``wire_size_cross``.
    :type wire_size_cross: float | None

    :param wire_size_awg: Value for ``wire_size_awg``.
    :type wire_size_awg: int | None

    :param od_mm: Value for ``od_mm``.
    :type od_mm: float

    :param weight_1km: Value for ``weight_1km``.
    :type weight_1km: float

    :param resistance_1km: Value for ``resistance_1km``.
    :type resistance_1km: float

    :param volts: Value for ``volts``.
    :type volts: float

    :param strands: Value for ``strands``.
    :type strands: int

    :param wire_type: Name of the wire type ("Wire", "Coaxial", "Ribbon", ...); blank is "Wire".
    :type wire_type: str | None

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
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
    wire_type_id = _wire_types.get_wire_type_id(con, wire_type)

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO wires (id, part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, material_id, stripe_color_id, core_material_id, '
                'num_conductors, shielded, tpi, wire_size_dia, wire_size_cross, wire_size_awg, '
                'od_mm, weight_1km, resistance_1km, volts, strands, wire_type_id) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, material_id,
                 stripe_color_id, core_material_id, num_conductors, shielded, tpi,
                 wire_size_dia, wire_size_cross, wire_size_awg, od_mm, weight_1km, resistance_1km,
                 volts, strands, wire_type_id))

    _logger.database(f'wire added "{part_number}"')

    if commit:
        con.commit()
        return new_id


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'wires',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.UUIDField('mfg_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_manufacturers.table,
                                                     _manufacturers.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('family_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_families.table,
                                                     _families.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('series_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_series.table,
                                                     _series.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('color_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('image_id', default='NULL',
                   references=_con.SQLFieldReference(_images.table,
                                                     _images.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('datasheet_id', default='NULL',
                   references=_con.SQLFieldReference(_datasheets.table,
                                                     _datasheets.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cad_id', default='NULL',
                   references=_con.SQLFieldReference(_cads.table,
                                                     _cads.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('min_temp_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_temperatures.table,
                                                     _temperatures.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('max_temp_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_temperatures.table,
                                                     _temperatures.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_materials.table,
                                                     _materials.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stripe_color_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('core_material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_platings.table,
                                                     _platings.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
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
    _con.UUIDField('wire_type_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_wire_types.table,
                                                     _wire_types.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_wires',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(table,
                                                     id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('circuit_id', default='NULL',
                   references=_con.SQLFieldReference(_circuits.pjt_table,
                                                     _circuits.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('bundle_id', default='NULL',
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('transition_id', default='NULL',
                   references=_con.SQLFieldReference(_transitions.pjt_table,
                                                     _transitions.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point2d_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point2d_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('layer_view_point_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('layer_id', default="NULL",
                   references=_con.SQLFieldReference(_concentric_layers.pjt_table,
                                                     _concentric_layers.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('is_filler_wire', default='0', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.TextField('name', default='""', no_null=True),
    _con.FloatField('operating_temp', default='NULL')
)
