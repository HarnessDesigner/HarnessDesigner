
from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_circuits',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_num', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('description', default='""', no_null=True)
)

# def pjt_circuits(con, cur):
#     cur.execute('CREATE TABLE pjt_circuits('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'circuit_num INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
