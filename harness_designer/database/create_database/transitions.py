# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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
from . import points_pegboard as _points_pegboard
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_transition(con: "_connector_base.ConnectorBase", part_number: str,
                   description: str, mfg: str | None = None,
                   family: str | None = None, series: str | None = None,
                   color: str | None = None, image: str | None = None,
                   datasheet: str | None = None, cad: str | None = None,
                   min_temp: str | None = None, max_temp: str | None = None,
                   material: str | None = None, shape: str | None = None,
                   protection: str | None = None, branch_count: int = 0,
                   adhesive_ids: list[bytes] | None = None, weight: float = 0.0,
                   branches: list[dict] = [], commit: bool = True) -> None:

    """
    Add a transition.

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

    :param shape: Value for ``shape``.
    :type shape: str | None

    :param protection: Value for ``protection``.
    :type protection: str | None

    :param branch_count: Value for ``branch_count``.
    :type branch_count: int

    :param adhesive_ids: Identifier for the adhesive.
    :type adhesive_ids: list[bytes] | None

    :param weight: Value for ``weight``.
    :type weight: float

    :param branches: Value for ``branches``.
    :type branches: list[dict]

    :param commit: Value for ``commit``.
    :type commit: bool
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

    transition_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO transitions (id, part_number, description, mfg_id, '
                'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                'min_temp_id, max_temp_id, material_id, shape_id, protection_id, '
                'branch_count, adhesive_ids, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (transition_id, part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, material_id,
                 shape_id, protection_id, branch_count,
                 str(adhesive_ids), weight))

    con.commit()
    _logger.database(f'transition added "{part_number}"')

    for i, branch in enumerate(branches):
        try:
            _transition_branches.add_transition_branch(con, i, transition_id, commit=commit, **branch)
        except Exception as err:
            _logger.traceback(err)


@_check_types.do
def add_pjt_transition(con: "_connector_base.ConnectorBase", project_id: int,
                       part_id: bytes, point3d_id: bytes | None = None,
                       name: str = '', notes: str = '',
                       quat3d: list[float] | None = None,
                       angle3d: list[float] | None = None,
                       is_visible3d: int = 1) -> None:

    """
    Add a PJT transition.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param project_id: Identifier for the project.
    :type project_id: int

    :param part_id: Identifier for the part.
    :type part_id: bytes

    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: bytes | None

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
        angle3d = [0.0, 0.0, 0.0]

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_transitions (id, part_id, point3d_id, name, '
                'notes, quat3d, angle3d, is_visible3d) VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_id, point3d_id, name, notes, quat3d, angle3d, is_visible3d))

    con.commit()


@_check_types.do
def add_transitions(con: "_connector_base.ConnectorBase",
                    data: tuple[dict] | list[dict]) -> None:

    """
    Add a transitions.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param data: Data payload.
    :type data: tuple[dict] | list[dict]
    """

    for line in data:
        add_transition(con, **line)


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
    'transitions',
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
    _con.UUIDField('shape_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_shapes.table,
                                                     _shapes.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('protection_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_protections.table,
                                                     _protections.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('branch_count', default='0', no_null=True),
    _con.TextField('adhesive_ids', default='"[]"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_transitions',
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
    _con.UUIDField('point_pegboard_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('table_point_peg_id', default="NULL",
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    # Defaulted to a -90-degree X rotation (quat [w, x, y, z] =
    # [0.7071067811865476, -0.7071067811865476, 0.0, 0.0], confirmed via
    # Angle.from_euler(-90.0, 0.0, 0.0)._q -- NOT identity, unlike every
    # other pegboard-placed table's own quat_pegboard/angle_pegboard
    # default) -- a transition's own branch geometry is built in the
    # SAME native/catalog orientation the 3D view uses (no separate
    # "flatten" transform anywhere in objects_pegboard/transition.py),
    # so this default is what makes it render flat on the peg-board
    # right out of the gate. The peg-board's own rotation UI only ever
    # touches Y (see TRANSITION_DESIGN.md), so this X component is never
    # written again after a transition is first placed. See
    # TRANSITION_DESIGN.md's own record of this decision.
    _con.TextField(
        'quat_pegboard',
        default='"[0.7071067811865476, -0.7071067811865476, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle_pegboard', default='"[-90.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
