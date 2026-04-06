
from . import projects as _projects
from . import points3d as _points3d
from . import circuits as _circuits
from . import wires as _wires

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')


def add_pjt_wire_service_loop(con, project_id, part_id, start_point3d_id=None,
                              stop_point3d_id=None, circuit_id=None, notes='',
                              quat3d=[1.0, 0.0, 0.0, 0.0], angle3d=[0.0, 0.0, 0.0],
                              is_visible3d=1):

    con.execute('INSERT INTO pjt_wire_service_loops (project_id, part_id, '
                'start_point3d_id, stop_point3d_id, circuit_id, notes, quat3d, '
                'angle3d, is_visible3d) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, start_point3d_id, stop_point3d_id, circuit_id,
                 notes, quat3d, angle3d, is_visible3d))
    con.commit()


pjt_table = _con.SQLTable(
    'pjt_wire_service_loops',
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
