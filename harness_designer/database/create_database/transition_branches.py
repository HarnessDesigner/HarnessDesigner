# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import transitions as _transitions
from . import projects as _projects
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard
from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ..db_connectors import base as _connector_base


@_check_types.do
def _offset_to_text(offset: list | tuple | None) -> str:
    """Convert a branch offset from the catalog JSON into the stored
    ``"[x, y, z]"`` text. The JSON still uses the old form -- missing, or
    ``[x, y]`` -- so a missing value becomes the origin and a missing z
    becomes 0.0. Remove the 2 value handling once the JSON is updated.
    """
    if offset is None:
        return '[0.0, 0.0, 0.0]'

    values = [float(v) for v in offset]

    if len(values) == 2:
        values.append(0.0)

    return str(values)


@_check_types.do
def _angle_to_text(angle: int | float | list | tuple | None) -> str:
    """Convert a branch angle from the catalog JSON into the stored
    ``"[x, y, z]"`` euler-degrees text. The JSON still holds the old single
    float, which was a rotation about Z (so it becomes ``[0, 0, angle]``);
    a missing value becomes no rotation. Remove the single float handling
    once the JSON is updated.
    """
    if angle is None:
        return '[0.0, 0.0, 0.0]'

    if isinstance(angle, (list, tuple)):
        return str([float(v) for v in angle])

    return str([0.0, 0.0, float(angle)])


@_check_types.do
def add_transition_branch(con: "_connector_base.ConnectorBase", idx: int, transition_id: bytes, bulb_offset: list[float] | None = None, bulb_length: float | None = None,
                          min_dia: float = 0.0, max_dia: float = 0.0, length: float = 0.0, offset: list[float] | tuple[float, ...] | None = None, angle: int | float | list[float] | tuple[float, ...] | None = None,
                          flange_height: float | None = None, flange_width: float | None = None, commit: bool = True) -> bytes:
    """Add a transition branch.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param idx: Value for ``idx``.
    :type idx: UNKNOWN
    :param transition_id: Identifier for the transition.
    :type transition_id: UNKNOWN
    :param bulb_offset: Value for ``bulb_offset``.
    :type bulb_offset: UNKNOWN
    :param bulb_length: Value for ``bulb_length``.
    :type bulb_length: UNKNOWN
    :param min_dia: Value for ``min_dia``.
    :type min_dia: UNKNOWN
    :param max_dia: Value for ``max_dia``.
    :type max_dia: UNKNOWN
    :param length: Value for ``length``.
    :type length: UNKNOWN
    :param offset: Value for ``offset``.
    :type offset: UNKNOWN
    :param angle: Value for ``angle``.
    :type angle: UNKNOWN
    :param flange_height: Value for ``flange_height``.
    :type flange_height: UNKNOWN
    :param flange_width: Value for ``flange_width``.
    :type flange_width: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    offset = _offset_to_text(offset)
    angle = _angle_to_text(angle)

    if bulb_offset is not None:
        bulb_offset = str(bulb_offset)

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO transition_branches (id, transition_id, idx, bulb_offset, '
                'bulb_length, min_dia, max_dia, length, offset, angle, flange_height, '
                'flange_width) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, transition_id, idx, bulb_offset, bulb_length, min_dia, max_dia,
                 length, offset, angle, flange_height, flange_width))

    _logger.database(f'transition branch added {idx} - {transition_id}')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def add_pjt_transition_branch(con: "_connector_base.ConnectorBase", project_id: bytes, part_id: bytes, transition_id: bytes,
                              point3d_id: bytes | None = None, diameter: float = 0.0, branch_id: bytes | None = 0) -> None:
    """Add a PJT transition branch.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param project_id: Identifier for the project.
    :type project_id: UNKNOWN
    :param part_id: Identifier for the part.
    :type part_id: UNKNOWN
    :param transition_id: Identifier for the transition.
    :type transition_id: UNKNOWN
    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: UNKNOWN
    :param diameter: Value for ``diameter``.
    :type diameter: UNKNOWN
    :param branch_id: Identifier for the branch.
    :type branch_id: UNKNOWN
    """

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute(f'INSERT INTO pjt_transition_branches (id, part_id, transition_id, '
                f'point3d_id, diameter, branch_id) VALUES (?, ?, ?, ?, ?, ?);',
                (new_id, part_id, transition_id, point3d_id, diameter, branch_id))

    con.commit()


id_field = _con.UUIDField('id', is_primary=True)


table = _con.SQLTable(
    'transition_branches',
    id_field,
    _con.UUIDField('transition_id', no_null=True,
                  references=_con.SQLFieldReference(_transitions.table,
                                                    _transitions.id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    _con.TextField('bulb_offset', default='NULL'),
    _con.FloatField('bulb_length', default='NULL'),
    _con.FloatField('min_dia', no_null=True),
    _con.FloatField('max_dia', no_null=True),
    _con.FloatField('length', no_null=True),
    # Both are "[x, y, z]" strings: ``offset`` in mm, ``angle`` as euler
    # degrees about the X, Y and Z axes.
    _con.TextField('offset', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.FloatField('flange_height', default='NULL'),
    _con.FloatField('flange_width', default='NULL')
)


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_transition_branches',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(table,
                                                     id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('transition_id', no_null=True,
                   references=_con.SQLFieldReference(_transitions.pjt_table,
                                                     _transitions.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point3d_id', no_null=True,
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.FloatField('diameter', no_null=True),
    _con.IntField('branch_id', no_null=True),
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
    _con.IntField('table_hidden', default='0', no_null=True)
)
