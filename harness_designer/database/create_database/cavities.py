from . import housings as _housings

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from .. import db_connectors as _con

id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cavities',
    id_field,
    _con.IntField('housing_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_housings.table,
                                                    _housings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('point2d', default='"[0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),

    _con.TextField('point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.FloatField('length', default='2.0', no_null=True),
    _con.TextField('terminal_sizes', default='"[]"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_cavities',
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

    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('housing_id', no_null=True,
                  references=_con.SQLFieldReference(_housings.pjt_table,
                                                    _housings.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)


# def pjt_cavities(con, cur):
#     cur.execute('CREATE TABLE pjt_cavities('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER DEFAULT NULL, '
#                 'housing_id INTEGER NOT NULL, '
#                 'point2d_id INTEGER NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # Relative to housing
#
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES cavities(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def cavities(con, cur):
#     # cavities point positions are relitive to the housing with the
#     # housing being centered at x=0, y=0, z=0
#
#     cur.execute('CREATE TABLE cavities('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'housing_id INTEGER NOT NULL, '
#                 'idx INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'point2d TEXT DEFAULT "[0.0, 0.0]" NOT NULL, '
#                 'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'length REAL DEFAULT "2.0" NOT NULL, '
#                 'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
#                 'FOREIGN KEY (housing_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
