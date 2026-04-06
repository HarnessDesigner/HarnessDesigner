
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
