
from . import projects as _projects
from . import concentric_layers as _concentric_layers
from . import wires as _wires
from . import points2d as _points2d

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_concentric_wires',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('layer_id', no_null=True,
                  references=_con.SQLFieldReference(_concentric_layers.pjt_table,
                                                    _concentric_layers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('wire_id', no_null=True,
                  references=_con.SQLFieldReference(_wires.pjt_table,
                                                    _wires.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.IntField('is_filler', no_null=True),
    _con.TextField('notes', default='""', no_null=True)
)

# def pjt_concentric_wires(con, cur):
#     cur.execute('CREATE TABLE pjt_concentric_wires('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'idx INTEGER NOT NULL, '
#                 'layer_id INTEGER NOT NULL, '
#                 'wire_id INTEGER NOT NULL, '
#                 'point_id INTEGER NOT NULL, '
#                 'is_filler INTEGER DEFAULT 0 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (layer_id) REFERENCES pjt_concentric_layers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (wire_id) REFERENCES pjt_wires(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point_id) REFERENCES pjt_point2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
