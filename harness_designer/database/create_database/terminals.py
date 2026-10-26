# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import genders as _genders
from . import platings as _platings
from . import cavity_locks as _cavity_locks
from . import temperatures as _temperatures
from . import colors as _colors
from . import models3d as _models3d
from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import points_pegboard as _points_pegboard
from . import circuits as _circuits
from . import cavities as _cavities
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_terminal(con: "_connector_base.ConnectorBase", part_number: str,
                 description: str, mfg: str | None = None,
                 family: str | None = None, series: str | None = None,
                 color: str | None = None, image: str | None = None,
                 datasheet: str | None = None, cad: str | None = None,
                 min_temp: str | None = None, max_temp: str | None = None,
                 model3d: str | None = None, plating: str | None = None,
                 gender: str | None = None, cavity_lock: str | None = None,
                 sealing: int = 0, blade_size: float = 0.0,
                 resistance: float = 0.0, mating_cycles: int = 0,
                 max_vibration_g: int = 0, max_current_ma: int = 0,
                 wire_size_awg_min: int | None = None,
                 wire_size_awg_max: int | None = None,
                 wire_size_dia_min: float | None = None,
                 wire_size_dia_max: float | None = None,
                 wire_size_cross_min: float | None = None,
                 wire_size_cross_max: float | None = None, length: float = 0.0,
                 width: float = 0.0, height: float = 0.0, weight: float = 0.0,
                 compat_housings: list[str] | None = None,
                 compat_seals: list[str] | None = None,
                 commit: bool = True) -> bytes:

    """
    Add a terminal.

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

    :param plating: Value for ``plating``.
    :type plating: str | None

    :param gender: Value for ``gender``.
    :type gender: str | None

    :param cavity_lock: Value for ``cavity_lock``.
    :type cavity_lock: str | None

    :param sealing: Value for ``sealing``.
    :type sealing: int

    :param blade_size: Value for ``blade_size``.
    :type blade_size: float

    :param resistance: Value for ``resistance``.
    :type resistance: float

    :param mating_cycles: Value for ``mating_cycles``.
    :type mating_cycles: int

    :param max_vibration_g: Value for ``max_vibration_g``.
    :type max_vibration_g: int

    :param max_current_ma: Value for ``max_current_ma``.
    :type max_current_ma: int

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

    :param width: Value for ``width``.
    :type width: float

    :param height: Value for ``height``.
    :type height: float

    :param weight: Value for ``weight``.
    :type weight: float

    :param compat_housings: Value for ``compat_housings``.
    :type compat_housings: list[str] | None

    :param compat_seals: Value for ``compat_seals``.
    :type compat_seals: list[str] | None

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if compat_housings is None:
        compat_housings = []

    if compat_seals is None:
        compat_seals = []

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cavity_lock)
    plating_id = _platings.get_plating_id(con, plating)
    gender_id = _genders.get_gender_id(con, gender)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)

    if not width and blade_size:
        width = blade_size

    if not height and blade_size:
        height = blade_size

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if gender:
            description += f' {gender}'

        if blade_size:
            description += f' {blade_size}mm'

        if plating:
            description += f' {plating}'

        if wire_size_cross_min:
            description += f' {wire_size_cross_min}mm²'

        if wire_size_cross_max:
            if wire_size_cross_min:
                description += f' -'

            description += f' {wire_size_cross_max}mm²'

        description += ' Terminal'

    compat_housings_str = ', '.join(compat_housings)
    compat_seals_str = ', '.join(compat_seals)

    _logger.database(f'adding terminal {part_number}, {description}')

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO terminals (id, part_number, description, '
                'mfg_id, family_id, series_id, color_id, image_id, datasheet_id, '
                'cad_id, min_temp_id, max_temp_id, model3d_id, plating_id, '
                'gender_id, cavity_lock_id, sealing, blade_size, resistance, '
                'mating_cycles, max_vibration_g, max_current_ma, wire_size_awg_min, '
                'wire_size_awg_max, wire_size_dia_min, wire_size_dia_max, '
                'wire_size_cross_min, wire_size_cross_max, length, width, height, '
                'weight, compat_housings, compat_seals) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id,
                 color_id, image_id, datasheet_id, cad_id, min_temp_id, max_temp_id,
                 model3d_id, plating_id, gender_id, cavity_lock_id, sealing, blade_size,
                 resistance, mating_cycles, max_vibration_g, max_current_ma,
                 wire_size_awg_min, wire_size_awg_max, wire_size_dia_min,
                 wire_size_dia_max, wire_size_cross_min, wire_size_cross_max, length,
                 width, height, weight, compat_housings_str, compat_seals_str))

    _logger.database(f'terminal added "{part_number}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def add_pjt_terminal(con: "_connector_base.ConnectorBase", project_id: int,
                     part_id: bytes, cavity_id: bytes | None = None,
                     circuit_id: bytes | None = None,
                     wire_point3d_id: bytes | None = None,
                     point3d_id: bytes | None = None,
                     point2d_id: bytes | None = None,
                     wire_point2d_id: bytes | None = None, name: str = '',
                     notes: str = '', quat3d: list[float] | None = None,
                     angle3d: list[float] | None = None,
                     quat2d: list[float] | None = None,
                     angle2d: list[float] | None = None, is_start: int = 0,
                     volts: float = 0.0, load: float = 0.0,
                     voltage_drop: float = 0.0, is_visible3d: int = 0,
                     is_visible2d: int = 0) -> None:

    """
    Add a PJT terminal.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param project_id: Identifier for the project.
    :type project_id: int

    :param part_id: Identifier for the part.
    :type part_id: bytes

    :param cavity_id: Identifier for the cavity.
    :type cavity_id: bytes | None

    :param circuit_id: Identifier for the circuit.
    :type circuit_id: bytes | None

    :param wire_point3d_id: Identifier for the wire point 3D.
    :type wire_point3d_id: bytes | None

    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: bytes | None

    :param point2d_id: Identifier for the point 2D.
    :type point2d_id: bytes | None

    :param wire_point2d_id: Identifier for the wire point 2D.
    :type wire_point2d_id: bytes | None

    :param name: Name value.
    :type name: str

    :param notes: Value for ``notes``.
    :type notes: str

    :param quat3d: Value for ``quat3d``.
    :type quat3d: list[float] | None

    :param angle3d: Value for ``angle3d``.
    :type angle3d: list[float] | None

    :param quat2d: Value for ``quat2d``.
    :type quat2d: list[float] | None

    :param angle2d: Value for ``angle2d``.
    :type angle2d: list[float] | None

    :param is_start: Boolean flag for whether start.
    :type is_start: int

    :param volts: Value for ``volts``.
    :type volts: float

    :param load: Value for ``load``.
    :type load: float

    :param voltage_drop: Value for ``voltage_drop``.
    :type voltage_drop: float

    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: int

    :param is_visible2d: Boolean flag for whether visible 2D.
    :type is_visible2d: int
    """

    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [0.0, 0.0, 0.0]

    if quat2d is None:
        quat2d = [1.0, 0.0, 0.0, 0.0]

    if angle2d is None:
        angle2d = [0.0, 0.0, 0.0]

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_terminals (id, part_id, cavity_id, circuit_id, '
                'wire_point3d_id, point3d_id, point2d_id, wire_point2d_id, name, notes, '
                'quat3d, angle3d, quat2d, angle2d, is_start, volts, load, voltage_drop, '
                'is_visible3d, is_visible2d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_id, cavity_id, circuit_id, wire_point3d_id, point3d_id,
                 point2d_id, wire_point2d_id, name, notes, str(quat3d), str(angle3d),
                 str(quat2d), str(angle2d), is_start, volts, load, voltage_drop,
                 is_visible3d, is_visible2d))

    con.commit()


@_check_types.do
def add_terminals(con: "_connector_base.ConnectorBase",
                  data: tuple[dict] | list[dict]) -> None:

    """
    Add a terminals.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_terminal(con, **line)


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


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'terminals',
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
    _con.UUIDField('plating_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_platings.table,
                                                     _platings.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('gender_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_genders.table,
                                                     _genders.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cavity_lock_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_cavity_locks.table,
                                                     _cavity_locks.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('sealing', default='0', no_null=True),
    _con.IntField('round_terminal', default='0'),
    _con.FloatField('blade_size', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.IntField('mating_cycles', default='0', no_null=True),
    _con.IntField('max_vibration_g', default='0', no_null=True),
    _con.IntField('max_current_ma', default='0', no_null=True),
    _con.IntField('wire_size_awg_min', default='NULL'),
    _con.IntField('wire_size_awg_max', default='NULL'),
    _con.FloatField('wire_size_dia_min', default='NULL'),
    _con.FloatField('wire_size_dia_max', default='NULL'),
    _con.FloatField('wire_size_cross_min', default='NULL'),
    _con.FloatField('wire_size_cross_max', default='NULL'),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('compat_housings', default='""', no_null=True),
    _con.TextField('compat_seals', default='""', no_null=True)
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_terminals',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(table,
                                                     id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cavity_id', default='NULL',
                   references=_con.SQLFieldReference(_cavities.pjt_table,
                                                     _cavities.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('circuit_id', default='NULL',
                   references=_con.SQLFieldReference(_circuits.pjt_table,
                                                     _circuits.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('wire_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Peg-board mirror of wire_point3d_id -- same lazily-created-on-first-
    # access shape, just against pjt_points_pegboard.
    _con.UUIDField('wire_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Wire-attachment/crimp point -- 1/3 up from the back of the terminal,
    # where the wire's WireLayout actually attaches. Lazily computed (via
    # PJTTerminal._wire_side_extent()) and persisted the first time it's
    # needed; see PJTTerminal.attach_position3d. Distinct from
    # wire_point3d_id, which is the layout point at the very back of the
    # terminal.
    _con.UUIDField('attach_point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Peg-board mirror of attach_point3d_id.
    _con.UUIDField('attach_point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point3d_id', default="NULL",
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point2d_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('wire_point2d_id', default="NULL",
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('seal_point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('seal_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat_pegboard', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle_pegboard', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_start', default='1', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True),
    _con.FloatField('load', default='"0.0"', no_null=True),
    _con.FloatField('voltage_drop', default='"0.0"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.FloatField('operating_temp', default='NULL'),
    _con.IntField('load_type', default='0', no_null=True)
)
