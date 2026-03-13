from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')


def add_pjt_wire_layout(con, project_id, point2d_id=None, point3d_id=None, notes='',
                        is_visible2d=0, is_visible3d=0):

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
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_wire_layouts(con, cur):
#     cur.execute('CREATE TABLE pjt_wire_layouts('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'point3d_id INTEGER DEFAULT NULL, '  # absolute, shared with wire
#                 'point2d_id INTEGER DEFAULT NULL, '
#                 'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
