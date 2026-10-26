# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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
from . import points_pegboard as _points_pegboard
from . import wires as _wires
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_wire_markers(con: "_connector_base.ConnectorBase",
                     data: tuple[dict] | list[dict]) -> None:

    """
    Add a wire markers.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_wire_marker(con, **line)


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
def add_wire_marker(con: "_connector_base.ConnectorBase", part_number: str,
                    description: str, mfg: str | None = None,
                    family: str | None = None, series: str | None = None,
                    color: str | None = None, image: str | None = None,
                    datasheet: str | None = None, cad: str | None = None,
                    min_temp: str | None = None, max_temp: str | None = None,
                    min_diameter: float = 0.0, max_diameter: float = 0.0,
                    wire_size_awg_min: int | None = None,
                    wire_size_awg_max: int | None = None,
                    wire_size_dia_min: float | None = None,
                    wire_size_dia_max: float | None = None,
                    wire_size_cross_min: float | None = None,
                    wire_size_cross_max: float | None = None, length: float = 0.0,
                    weight: float = 0.0, has_label: int = 0,
                    commit: bool = True) -> bytes:

    """
    Add a wire marker.

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

    :param min_diameter: Value for ``min_diameter``.
    :type min_diameter: float

    :param max_diameter: Value for ``max_diameter``.
    :type max_diameter: float

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

    :param length: Value for ``length``.
    :type length: float

    :param weight: Value for ``weight``.
    :type weight: float

    :param has_label: Boolean flag for whether label is available.
    :type has_label: int

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
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

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO wire_markers (id, part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, min_diameter, max_diameter, wire_size_awg_min, wire_size_awg_max, '
                'wire_size_dia_min, wire_size_dia_max, wire_size_cross_min, wire_size_cross_max, '
                'length, weight, has_label) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, min_diameter,
                 max_diameter, wire_size_awg_min, wire_size_awg_max, wire_size_dia_min,
                 wire_size_dia_max, wire_size_cross_min, wire_size_cross_max, length,
                 weight, has_label))

    _logger.database(f'wire marker added "{part_number}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def add_pjt_wire_marker(con: "_connector_base.ConnectorBase", project_id: int,
                        part_id: bytes, point3d_id: bytes | None = None,
                        point2d_id: bytes | None = None,
                        wire_id: bytes | None = None, name: str = '',
                        notes: str = '', label: str = '', is_visible2d: int = 1,
                        is_visible3d: int = 1) -> None:

    """
    Add a PJT wire marker.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param project_id: Identifier for the project.
    :type project_id: int

    :param part_id: Identifier for the part.
    :type part_id: bytes

    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: bytes | None

    :param point2d_id: Identifier for the point 2D.
    :type point2d_id: bytes | None

    :param wire_id: Identifier for the wire.
    :type wire_id: bytes | None

    :param name: Name value.
    :type name: str

    :param notes: Value for ``notes``.
    :type notes: str

    :param label: Value for ``label``.
    :type label: str

    :param is_visible2d: Boolean flag for whether visible 2D.
    :type is_visible2d: int

    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: int
    """

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_wire_markers (id, part_id, point3d_id, '
                'point2d_id, wire_id, name, notes, label, is_visible2d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_id, point3d_id, point2d_id, wire_id, name, notes,
                 label, is_visible2d, is_visible3d))

    con.commit()


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'wire_markers',
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


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_wire_markers',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(table,
                                                     id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),

    _con.UUIDField('point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('wire_id', default='NULL',
                   references=_con.SQLFieldReference(_wires.pjt_table,
                                                     _wires.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('label', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
