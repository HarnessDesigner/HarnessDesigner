# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con

id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'app_users',
    id_field,
    _con.TextField('mysql_account', is_unique=True, no_null=True),
    _con.TextField('display_name', default='""', no_null=True)
)
