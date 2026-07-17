# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import transitions as _transitions

from . import projects as _projects
from . import points3d as _points3d
from . import points_peg as _points_peg

from .. import db_connectors as _con
from ... import logger as _logger


def add_transition_branch(con, idx, transition_id, bulb_offset=None, bulb_length=None,
                          min_dia=0.0, max_dia=0.0, length=0.0, offset=None, angle=None,
                          flange_height=None, flange_width=None, commit=True):
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

    if offset is not None:
        offset = str(offset)

    if bulb_offset is not None:
        bulb_offset = str(bulb_offset)

    con.execute(f'INSERT INTO transition_branches (transition_id, idx, bulb_offset, '
                f'bulb_length, min_dia, max_dia, length, offset, angle, flange_height, '
                f'flange_width) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (transition_id, idx, bulb_offset, bulb_length, min_dia, max_dia,
                 length, offset, angle, flange_height, flange_width))

    _logger.database(f'transition branch added {idx} - {transition_id}')

    if commit:
        con.commit()
        return con.lastrowid


def add_pjt_transition_branch(con, project_id, part_id, transition_id,
                              point3d_id=None, diameter=0.0, branch_id=0):
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

    con.execute(f'INSERT INTO pjt_transition_branches (project_id, part_id, transition_id, '
                f'point3d_id, diameter, branch_id) VALUES (?, ?, ?, ?, ?, ?);',
                (project_id, part_id, transition_id, point3d_id, diameter, branch_id))

    con.commit()


id_field = _con.PrimaryKeyField('id')


table = _con.SQLTable(
    'transition_branches',
    id_field,
    _con.IntField('transition_id', no_null=True,
                  references=_con.SQLFieldReference(_transitions.table,
                                                    _transitions.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.TextField('bulb_offset', default='NULL'),
    _con.FloatField('bulb_length', default='NULL'),
    _con.FloatField('min_dia', no_null=True),
    _con.FloatField('max_dia', no_null=True),
    _con.FloatField('length', no_null=True),
    _con.TextField('offset', default='NULL'),
    _con.FloatField('angle', default='NULL'),
    _con.FloatField('flange_height', default='NULL'),
    _con.FloatField('flange_width', default='NULL')
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_transition_branches',
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
    _con.IntField('transition_id', no_null=True,
                  references=_con.SQLFieldReference(_transitions.pjt_table,
                                                    _transitions.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('diameter', no_null=True),
    _con.IntField('branch_id', no_null=True),
    _con.IntField('table_point_peg_id', default="NULL",
                  references=_con.SQLFieldReference(_points_peg.pjt_table,
                                                    _points_peg.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('table_hidden', default='0', no_null=True)
)
