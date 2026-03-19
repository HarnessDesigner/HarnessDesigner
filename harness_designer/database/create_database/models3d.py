from .. import db_connectors as _con
from . import file_types as _file_types
from ... import resources as _resources
from ... import logger as _logger


def get_model3d_id(con, path: str):  # NOQA
    if not path:
        return None

    con.execute(f'SELECT id FROM models3d WHERE path="{path}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding model3d ("{path}")')

        if path.startswith('http'):
            con.execute('INSERT INTO models3d (path) VALUES (?);', (path,))
        else:
            values = _resources.collect_resource(con, _resources.IMAGE_TYPE_MODEL, path)
            if values is None:
                return None

            uuid, file_type_id = values
            con.execute('INSERT INTO models3d (uuid, path, file_type_id) VALUES (?, ?, ?);', (uuid, path, file_type_id))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'model3d added "{path}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'models3d',
    id_field,
    _con.TextField('uuid', default="NULL"),
    _con.IntField('file_type_id', default="NULL",
                  references=_con.SQLFieldReference(_file_types.table,
                                                    _file_types.id_field)),
    _con.IntField('target_count', default='25000', no_null=True),
    _con.FloatField('aggressiveness', default='"5.0"', no_null=True),
    _con.IntField('update_rate', default='150', no_null=True),
    _con.IntField('iterations', default='1', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('scale', default='"[1.0, 1.0, 1.0]"', no_null=True),
    _con.IntField('simplify', default='0', no_null=True),
    _con.TextField('path', no_null=True, is_unique=True)
)
