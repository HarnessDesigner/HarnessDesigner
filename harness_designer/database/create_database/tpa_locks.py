# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import json

from . import temperatures as _temperatures
from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
from . import models3d as _models3d
from . import projects as _projects
from . import points3d as _points3d
from . import housings as _housings
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_tpa_lock(con: "_connector_base.ConnectorBase", part_number: str,
                 description: str, mfg: str | None = None,
                 family: str | None = None, series: str | None = None,
                 color: str | None = None, image: str | None = None,
                 datasheet: str | None = None, cad: str | None = None,
                 min_temp: str | None = None, max_temp: str | None = None,
                 model3d: str | None = None, lock_type: str = '',
                 length: float = 0.0, width: float = 0.0, height: float = 0.0,
                 weight: float = 0.0, pins: int = 0, terminal_size: float = 0.0,
                 compat_housings: list[str] | None = None,
                 commit: bool = True) -> bytes:

    """
    Add a TPA lock.

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

    :param lock_type: Value for ``lock_type``.
    :type lock_type: str

    :param length: Value for ``length``.
    :type length: float

    :param width: Value for ``width``.
    :type width: float

    :param height: Value for ``height``.
    :type height: float

    :param weight: Value for ``weight``.
    :type weight: float

    :param pins: Value for ``pins``.
    :type pins: int

    :param terminal_size: Value for ``terminal_size``.
    :type terminal_size: float

    :param compat_housings: Value for ``compat_housings``.
    :type compat_housings: list[str] | None

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if compat_housings is None:
        compat_housings = []

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        description += ' TPA Lock'

    compat_housings_str = ', '.join(compat_housings)

    _logger.database(f'adding tpa lock {part_number}, {description}')

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO tpa_locks (id, part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, lock_type, length, width, height, weight, '
                'pins, terminal_size, compat_housings) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 lock_type, length, width, height, weight, pins, terminal_size,
                 compat_housings_str))

    _logger.database(f'tpa lock added "{part_number}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def add_pjt_tpa_lock(con: "_connector_base.ConnectorBase", project_id: int,
                     part_id: bytes, point3d_id: bytes | None = None,
                     housing_id: bytes | None = None, name: str = '',
                     notes: str = '', quat3d: list[float] | None = None,
                     angle3d: list[float] | None = None,
                     is_visible3d: int = 0) -> None:

    """
    Add a PJT TPA lock.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param project_id: Identifier for the project.
    :type project_id: int

    :param part_id: Identifier for the part.
    :type part_id: bytes

    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: bytes | None

    :param housing_id: Identifier for the housing.
    :type housing_id: bytes | None

    :param name: Name value.
    :type name: str

    :param notes: Value for ``notes``.
    :type notes: str

    :param quat3d: Value for ``quat3d``.
    :type quat3d: list[float] | None

    :param angle3d: Value for ``angle3d``.
    :type angle3d: list[float] | None

    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: int
    """

    if quat3d is None:
        quat3d = [1.0, 0.0, 0.0, 0.0]

    if angle3d is None:
        angle3d = [1.0, 0.0, 0.0, 0.0]

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_tpa_locks (id, part_id, point3d_id, housing_id, '
                'name, notes, quat3d, angle3d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_id, point3d_id, housing_id, name,
                 notes, str(quat3d), str(angle3d), is_visible3d))

    con.commit()


@_check_types.do
def add_tpa_locks(con: "_connector_base.ConnectorBase",
                  data: tuple[dict] | list[dict]) -> None:

    """
    Add a TPA locks.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_tpa_lock(con, **line)


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
    'tpa_locks',
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
    _con.TextField('lock_type', default='""', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('pins', default='""', no_null=True),
    _con.FloatField('terminal_size', default='"0.0"', no_null=True),
    _con.TextField('compat_housings', default='""', no_null=True)
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_tpa_locks',
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
    _con.UUIDField('scale3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('housing_id', default='NULL',
                   references=_con.SQLFieldReference(_housings.pjt_table,
                                                     _housings.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
