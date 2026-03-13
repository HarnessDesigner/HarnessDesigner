from . import transitions as _transitions

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con


def add_transition_branch(con, transition_id, idx, name='', bulb_offset=None,
                          bulb_length=None, min_dia=0.0, max_dia=0.0, length=0.0,
                          offset=None, angle=None, flange_height=None, flange_width=None):

    con.execute(f'INSERT INTO transition_branches (transition_id, idx, name, bulb_offset, '
                f'bulb_length, min_dia, max_dia, length, offset, angle, flange_height, '
                f'flange_width) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (transition_id, idx, name, bulb_offset, bulb_length, min_dia, max_dia,
                 length, offset, angle, flange_height, flange_width))

    con.commit()


def add_pjt_transition_branch(con, project_id, part_id, transition_id,
                              point3d_id=None, diameter=0.0, branch_id=0):

    con.execute(f'INSERT INTO pjt_transition_branches (project_id, part_id, transition_id, '
                f'point3d_id, diameter, branch_id) VALUES (?, ?, ?, ?, ?, ?);',
                (project_id, part_id, transition_id, point3d_id, diameter, branch_id))

    con.commit()


id_field = _con.PrimaryKeyField('id')


table = _con.SQLTable(
    'transition_branches',
    id_field,
    _con.IntField('transition_id', no_null=True,
                  references=_con.SQLFieldReference(_transitions.table,
                                                    _transitions.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('bulb_offset', default='NULL'),
    _con.FloatField('bulb_length', default='NULL'),
    _con.FloatField('min_dia', no_null=True),
    _con.FloatField('max_dia', no_null=True),
    _con.FloatField('length', no_null=True),
    _con.TextField('offset', default='NULL'),
    _con.FloatField('angle', default='NULL'),
    _con.FloatField('flange_height', default='NULL'),
    _con.FloatField('flange_width', default='NULL')
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_transition_branches',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('part_id', no_null=True,
                  references=_con.SQLFieldReference(table,
                                                    id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('transition_id', no_null=True,
                  references=_con.SQLFieldReference(_transitions.pjt_table,
                                                    _transitions.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('diameter', no_null=True),
    _con.IntField('branch_id', no_null=True)
)


# def pjt_transition_branches(con, cur):
#     cur.execute('CREATE TABLE pjt_transition_branches('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'branch_id INTEGER NOT NULL, '
#                 'transition_id INTEGER NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # can be shared with a bundle cover
#                 'diameter REAL DEFAULT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (transition_id) REFERENCES pjt_transitions(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def transition_branches(con, cur):
#     cur.execute('CREATE TABLE transition_branches('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'transition_id INTEGER NOT NULL, '
#                 'idx INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'bulb_offset TEXT DEFAULT NULL, '
#                 'bulb_length REAL DEFUALT NULL, '
#                 'min_dia REAL NOT NULL, '
#                 'max_dia REAL NOT NULL, '
#                 'length REAL NOT NULL, '
#                 'offset TEXT DEFAULT NULL, '
#                 'angle REAL DEFAULT NULL, '
#                 'flange_height REAL DEFAULT NULL, '
#                 'flange_width REAL DEFAULT NULL, '
#                 'FOREIGN KEY (transition_id) REFERENCES transitions(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
