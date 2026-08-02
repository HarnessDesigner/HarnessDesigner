# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import shutil

from .. import db_connectors as _con
from . import file_types as _file_types
from ... import resources as _resources
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def get_datasheet_id(con, path: str):  # NOQA
    """
    Return the datasheet ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param path: Filesystem path.
    :type path: str

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not path:
        return None

    con.execute('SELECT id FROM datasheets WHERE path=?;', (path,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding datasheet ("{path}")')

        db_id = _id_generator.generate_global_row_id(con).bytes

        if path.startswith('http'):
            con.execute('INSERT INTO datasheets (id, path) VALUES (?, ?);', (db_id, path))
        else:
            values = _resources.collect_resource(con, _resources.RESOURCE_TYPE_DATASHEET, path)
            if values is None:
                return None

            uuid, file_type_id = values
            con.execute('SELECT value FROM settings WHERE name="datasheet_path";')
            datasheet_path = con.fetchall()[0][0]

            con.execute('SELECT extension FROM file_types WHERE id=?;', (file_type_id,))
            ext = con.fetchall()[0][0]

            dst = os.path.join(datasheet_path, uuid[:2])
            if not os.path.isdir(dst):
                os.mkdir(dst)

            dst = os.path.join(dst, f'{uuid}.{ext}')
            src = os.path.join(datasheet_path, f'{uuid}.{ext}')
            shutil.move(src, dst)

            con.execute('INSERT INTO datasheets (id, uuid, path, file_type_id) VALUES (?, ?, ?, ?);',
                        (db_id, uuid, path, file_type_id))

        con.commit()

        _logger.database(f'datasheet added "{path}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'datasheets',
    id_field,
    _con.TextField('uuid', default="NULL"),
    _con.UUIDField('file_type_id', default="NULL",
                  references=_con.SQLFieldReference(_file_types.table,
                                                    _file_types.id_field)),
    _con.BlobField('data', default='NULL'),
    _con.TextField('path', no_null=True)
)
