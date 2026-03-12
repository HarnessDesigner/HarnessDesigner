
from . import projects as _projects
from . import points3d as _points3d
from . import circuits as _circuits
from . import wires as _wires

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_boots',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('part_id', no_null=True,
                  references=_con.SQLFieldReference(_wires.table,
                                                    _wires.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('start_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', no_null=True,
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_wire_service_loops(con, cur):
#     cur.execute('CREATE TABLE pjt_wire_service_loops('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'start_point3d_id INTEGER NOT NULL, '  # can be shared with a terminal or wire_layout
#                 'stop_point3d_id INTEGER NOT NULL, '  # can be shared with a terminal or wire layout
#                 'part_id INTEGER NOT NULL, '
#                 'circuit_id INTEGER NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (start_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES wires(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (circuit_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE'');')
#     con.commit()
