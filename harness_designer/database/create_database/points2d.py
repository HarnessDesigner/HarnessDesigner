
from . import projects as _projects

from .. import db_connectors as _con

pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_points2d',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True)
)

# def pjt_points2d(con, cur):
#     cur.execute('CREATE TABLE pjt_points2d('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'x REAL DEFAULT "0.0" NOT NULL, '
#                 'y REAL DEFAULT "0.0" NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
