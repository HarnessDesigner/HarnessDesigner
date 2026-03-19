from .. import db_connectors as _con
from . import file_types as _file_types
from ... import resources as _resources
from ... import logger as _logger


def get_datasheet_id(con, path: str):  # NOQA
    if not path:
        return None

    con.execute(f'SELECT id FROM datasheets WHERE path="{path}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding datasheet ("{path}")')

        if path.startswith('http'):
            con.execute('INSERT INTO datasheets (path) VALUES (?);', (path,))
        else:
            values = _resources.collect_resource(con, _resources.IMAGE_TYPE_DATASHEET, path)
            if values is None:
                return None

            uuid, file_type_id = values
            con.execute('INSERT INTO datasheets (uuid, path, file_type_id) VALUES (?, ?, ?);', (uuid, path, file_type_id))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'datasheet added "{path}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'datasheets',
    id_field,
    _con.TextField('uuid', default="NULL"),
    _con.IntField('file_type_id', default="NULL",
                  references=_con.SQLFieldReference(_file_types.table,
                                                    _file_types.id_field)),
    _con.BlobField('data', default='NULL'),
    _con.TextField('path', no_null=True)
)
