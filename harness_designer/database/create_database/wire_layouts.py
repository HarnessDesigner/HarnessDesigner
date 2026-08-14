# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import points_pegboard as _points_pegboard

from .. import db_connectors as _con
from ... import check_types as _check_types
from .. import id_generator as _id_generator


pjt_id_field = _con.UUIDField('id', is_primary=True)


@_check_types.do
def add_pjt_wire_layout(con, project_id, point2d_id=None, point3d_id=None, notes='',
                        is_visible2d=0, is_visible3d=0):
    """Add a PJT wire layout.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param project_id: Identifier for the project.
    :type project_id: UNKNOWN
    :param point2d_id: Identifier for the point 2D.
    :type point2d_id: UNKNOWN
    :param point3d_id: Identifier for the point 3D.
    :type point3d_id: UNKNOWN
    :param notes: Value for ``notes``.
    :type notes: UNKNOWN
    :param is_visible2d: Boolean flag for whether visible 2D.
    :type is_visible2d: UNKNOWN
    :param is_visible3d: Boolean flag for whether visible 3D.
    :type is_visible3d: UNKNOWN
    """

    new_id = _id_generator.generate_project_row_id(con, project_id).bytes

    con.execute('INSERT INTO pjt_wire_layouts (id, point2d_id, point3d_id, '
                'notes, is_visible2d, is_visible3d) VALUES (?, ?, ?, ?, ?, ?);',
                (new_id, point2d_id, point3d_id, notes, is_visible2d, is_visible3d))

    con.commit()


pjt_table = _con.SQLTable(
    'pjt_wire_layouts',
    pjt_id_field,
    _con.UUIDField('point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_CASCADE)),

    _con.UUIDField('point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_CASCADE)),
    # Exactly one of point2d_id/point3d_id/point_pegboard_id is ever
    # non-NULL per row -- a waypoint's layout is keyed to the specific
    # view it was placed in, since waypoint counts differ per view (see
    # PJTWireLayout's own exclusive position handling).
    _con.UUIDField('point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
