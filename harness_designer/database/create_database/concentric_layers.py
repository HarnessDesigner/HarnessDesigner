
from . import projects as _projects
from . import concentrics as _concentrics

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_concentric_layers',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('concentric_id', no_null=True,
                  references=_con.SQLFieldReference(_concentrics.pjt_table,
                                                    _concentrics.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.FloatField('diameter', default='"0.0"', no_null=True),
    _con.IntField('num_wires', default='0', no_null=True),
    _con.IntField('num_fillers', default='0', no_null=True)
)

# def pjt_concentric_layers(con, cur):
#     cur.execute('CREATE TABLE pjt_concentric_layers('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'idx INTEGER NOT NULL, '
#                 'diameter REAL DEFULT "0.0" NOT NULL, '
#                 'num_wires INTEGER DEFAULT 0 NOT NULL, '
#                 'num_fillers INTEGER DEFAULT 0 NOT NULL, '
#                 'concentric_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (concentric_id) REFERENCES pjt_concentrics(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
