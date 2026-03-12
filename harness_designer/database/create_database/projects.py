
from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'projects',
    pjt_id_field,
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('user_model', default='""', no_null=True),
    _con.TextField('creator', default='""', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('object_count', default='0', no_null=True)
)

# def projects(con, cur):
#     cur.execute('CREATE TABLE projects('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT NOT NULL, '
#                 'user_model TEXT DEFAULT "" NOT NULL, '
#                 'creator TEXT DEFAULT "" NOT NULL, '
#                 'object_count INTEGER DEFAULT 0 NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL'
#                 ');')
#     con.commit()
