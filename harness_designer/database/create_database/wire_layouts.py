# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')


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

    con.execute('INSERT INTO pjt_wire_layouts (project_id, point2d_id, point3d_id, '
                'notes, is_visible2d, is_visible3d) VALUES (?, ?, ?, ?, ?, ?);',
                (project_id, point2d_id, point3d_id, notes, is_visible2d, is_visible3d))

    con.commit()


pjt_table = _con.SQLTable(
    'pjt_wire_layouts',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', default='NULL',
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('point3d_id', default='NULL',
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
