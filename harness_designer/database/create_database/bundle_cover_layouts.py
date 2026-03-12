
from . import projects as _projects
from . import points3d as _points3d


from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_bundle_layouts',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)


# def pjt_bundle_layouts(con, cur):
#     cur.execute('CREATE TABLE pjt_bundle_layouts('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # absolute, share with bundle
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id)'
#                 ');')
#     con.commit()
