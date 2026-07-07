# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import shutil

from .. import db_connectors as _con
from . import file_types as _file_types
from ... import resources as _resources
from ... import logger as _logger


def get_datasheet_id(con, path: str):  # NOQA
    """Return the datasheet ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param path: Filesystem path.
    :type path: str
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if not path:
        return None

    con.execute(f'SELECT id FROM datasheets WHERE path="{path}";')
    res = con.fetchall()

    if not res:
        _logger.database(f'adding datasheet ("{path}")')

        if path.startswith('http'):
            con.execute('INSERT INTO datasheets (path) VALUES (?);', (path,))
        else:
            values = _resources.collect_resource(con, _resources.RESOURCE_TYPE_DATASHEET, path)
            if values is None:
                return None

            uuid, file_type_id = values
            con.execute(f'SELECT value FROM settings WHERE name="datasheet_path";')
            datasheet_path = con.fetchall()[0][0]

            con.execute(f'SELECT extension FROM file_types WHERE id={file_type_id};')
            ext = con.fetchall()[0][0]

            dst = os.path.join(datasheet_path, uuid[:2])
            if not os.path.isdir(dst):
                os.mkdir(dst)

            dst = os.path.join(dst, f'{uuid}.{ext}')
            src = os.path.join(datasheet_path, f'{uuid}.{ext}')
            shutil.move(src, dst)

            con.execute('INSERT INTO datasheets (uuid, path, file_type_id) VALUES (?, ?, ?);', (uuid, path, file_type_id))

        con.commit()
        db_id = con.lastrowid

        _logger.database(f'datasheet added "{path}" = {db_id}')

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

