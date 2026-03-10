from ... import db_connectors as _con
from . import housings as _housings

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
