# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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
from . import points_pegboard as _points_pegboard
from . import circuits as _circuits
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


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
def add_splices(con: "_connector_base.ConnectorBase",
                data: tuple[dict] | list[dict]) -> None:

    """
    Add a splices.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_splice(con, **line)


@_check_types.do
def add_splice(con: "_connector_base.ConnectorBase", part_number: str,
               description: str, mfg: str | None = None, family: str | None = None,
               series: str | None = None, color: str | None = None,
               image: str | None = None, datasheet: str | None = None,
               cad: str | None = None, min_temp: str | None = None,
               max_temp: str | None = None, model3d: str | None = None,  # NOQA
               material: str | None = None, plating: str | None = None,  # NOQA
               type: str | None = None, min_dia: float = 0.0, max_dia: float = 0.0,  # NOQA
               resistance: float = 0.0, length: float = 0.0, weight: float = 0.0,
               wire_size_awg_min: int | None = None,
               wire_size_awg_max: int | None = None,
               wire_size_dia_min: float | None = None,
               wire_size_dia_max: float | None = None,
               wire_size_cross_min: float | None = None,
               wire_size_cross_max: float | None = None,
               num_wires: int | None = None, commit: bool = True) -> bytes:

    """
    Add a splice.

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

    :param model3d: Value for ``model3d``.
    :type model3d: str | None

    :param material: Value for ``material``.
    :type material: str | None

    :param plating: Value for ``plating``.
    :type plating: str | None

    :param type: Value for ``type``.
    :type type: str | None

    :param min_dia: Value for ``min_dia``.
    :type min_dia: float

    :param max_dia: Value for ``max_dia``.
    :type max_dia: float

    :param resistance: Value for ``resistance``.
    :type resistance: float

    :param length: Value for ``length``.
    :type length: float

    :param weight: Value for ``weight``.
    :type weight: float

    :param wire_size_awg_min: Value for ``wire_size_awg_min``.
    :type wire_size_awg_min: int | None

    :param wire_size_awg_max: Value for ``wire_size_awg_max``.
    :type wire_size_awg_max: int | None

    :param wire_size_dia_min: Value for ``wire_size_dia_min``.
    :type wire_size_dia_min: float | None

    :param wire_size_dia_max: Value for ``wire_size_dia_max``.
    :type wire_size_dia_max: float | None

    :param wire_size_cross_min: Value for ``wire_size_cross_min``.
    :type wire_size_cross_min: float | None

    :param wire_size_cross_max: Value for ``wire_size_cross_max``.
    :type wire_size_cross_max: float | None

    :param num_wires: Value for ``num_wires``.
    :type num_wires: int | None

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

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

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO splices (id, part_number, description, mfg_id, '
                'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                'min_temp_id, max_temp_id, model3d_id, material_id, plating_id, type_id, '
                'min_dia, max_dia, resistance, length, weight, wire_size_awg_min, '
                'wire_size_awg_max, wire_size_dia_min, wire_size_dia_max, '
                'wire_size_cross_min, wire_size_cross_max, num_wires) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id,
                 color_id, image_id, datasheet_id, cad_id, min_temp_id, max_temp_id,
                 model3d_id, material_id, plating_id, type_id, min_dia, max_dia,
                 resistance, length, weight, wire_size_awg_min, wire_size_awg_max,
                 wire_size_dia_min, wire_size_dia_max, wire_size_cross_min,
                 wire_size_cross_max, num_wires))

    _logger.database(f'splice added "{part_number}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def add_pjt_splice(con: "_connector_base.ConnectorBase", project_id: int,
                   part_id: bytes, start_point3d_id: bytes | None = None,
                   stop_point3d_id: bytes | None = None,
                   branch_point3d_id: bytes | None = None,
                   point2d_id: bytes | None = None,
                   circuit_id: bytes | None = None, name: str = '',
                   notes: str = '', is_visible2d: int = 0,
                   is_visible3d: int = 0) -> None:

    """
    Add a PJT splice.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param project_id: Identifier for the project.
    :type project_id: int

    :param part_id: Identifier for the part.
    :type part_id: bytes

    :param start_point3d_id: Identifier for the start point 3D.
    :type start_point3d_id: bytes | None

    :param stop_point3d_id: Identifier for the stop point 3D.
    :type stop_point3d_id: bytes | None

    :param branch_point3d_id: Identifier for the branch point 3D.
    :type branch_point3d_id: bytes | None

    :param point2d_id: Identifier for the point 2D.
    :type point2d_id: bytes | None

    :param circuit_id: Identifier for the circuit.
    :type circuit_id: bytes | None

    :param name: Name value.
    :type name: str

    :param notes: Value for ``notes``.
    :type notes: str

    :param is_visible2d: Boolean flag for whether visible 2D.
    :type is_visible2d: int

    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: int
    """

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_splices (id, part_id, start_point3d_id, '
                'stop_point3d_id, branch_point3d_id, point2d_id, circuit_id, name, '
                'notes, is_visible2d, is_visible3d) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_id, start_point3d_id, stop_point3d_id,
                 branch_point3d_id, point2d_id, circuit_id, name, notes,
                 is_visible2d, is_visible3d))

    con.commit()


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'splices',
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
    _con.UUIDField('model3d_id', default='NULL',
                   references=_con.SQLFieldReference(_models3d.table,
                                                     _models3d.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_materials.table,
                                                     _materials.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('plating_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_platings.table,
                                                     _platings.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('type_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_splice_types.table,
                                                     _splice_types.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.FloatField('min_dia', default='"0.0"', no_null=True),
    _con.FloatField('max_dia', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.IntField('wire_size_awg_min', default='NULL'),
    _con.IntField('wire_size_awg_max', default='NULL'),
    _con.FloatField('wire_size_dia_min', default='NULL'),
    _con.FloatField('wire_size_dia_max', default='NULL'),
    _con.FloatField('wire_size_cross_min', default='NULL'),
    _con.FloatField('wire_size_cross_max', default='NULL'),
    _con.IntField('num_wires', default='NULL'),
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_splices',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(table,
                                                     id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('branch_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point2d_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('branch_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('table_point_peg_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('quat_pegboard', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle_pegboard', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.UUIDField('circuit_id', default='NULL',
                   references=_con.SQLFieldReference(_circuits.pjt_table,
                                                     _circuits.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.FloatField('operating_temp', default='NULL')
)
