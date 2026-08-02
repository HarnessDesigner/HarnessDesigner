# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger

import os
import json
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, data_path):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """

    con.execute('SELECT 1 FROM file_types LIMIT 1;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'file_types.json')

    splash.SetText(f'Loading file types file...')
    splash.flush()

    with open(json_path, 'r') as f:
        data = json.loads(f.read())

    if isinstance(data, dict):
        data = [value for value in data.values()]

    data_len = len(data)
    splash.SetText(f'Adding file type to db [0 | {data_len}]...', log=False)
    splash.flush()

    for i, item in enumerate(data):
        splash.SetText(f'Adding file type to db [{i + 1} | {data_len}]...', log=False)

        add_file_type(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_file_type(con, name, extension, is_model: bool | int = 0,
                  is_image: bool | int = 0, is_datasheet: bool | int = 0,
                  is_cad: bool | int = 0, mimetype: str = '', commit: bool = True):
    """
    Add a file type.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :param extension: Value for ``extension``.
    :type extension: UNKNOWN

    :param is_model: Boolean flag for whether model.
    :type is_model: UNKNOWN

    :param is_image: Boolean flag for whether model.
    :type is_image: UNKNOWN

    :param is_datasheet: Boolean flag for whether model.
    :type is_datasheet: UNKNOWN

    :param is_cad: Boolean flag for whether model.
    :type is_cad: UNKNOWN

    :param mimetype: Value for ``mimetype``.
    :type mimetype: UNKNOWN

    :param commit: Value for ``commit``.
    :type commit: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO file_types (id, mimetype, extension, name, is_model, is_image, is_datasheet, is_cad) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, mimetype, extension, name, int(is_model), int(is_image), int(is_datasheet), int(is_cad)))

    _logger.database(f'file type added "{extension}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def get_file_type(con, extension=None, mimetype=None):
    """
    Return the file type.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param extension: Value for ``extension``.
    :type extension: UNKNOWN

    :param mimetype: Value for ``mimetype``.
    :type mimetype: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if extension is None and mimetype is None:
        return None

    if extension is not None and mimetype is not None:
        con.execute('SELECT id FROM file_types WHERE extension=? AND mimetype=?;', (extension, mimetype))
        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.database(f'adding file type ("{extension}", "{mimetype}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO file_types (id, extension, mimetype) VALUES (?, ?, ?);',
                    (db_id, extension, mimetype))

        con.commit()

        _logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif extension is not None:
        con.execute('SELECT id FROM file_types WHERE extension=?;', (extension,))
        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.database(f'adding file type ("{extension}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO file_types (id, extension) VALUES (?, ?);', (db_id, extension))

        con.commit()

        _logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif mimetype is not None:
        con.execute('SELECT id FROM file_types WHERE mimetype=?;', (mimetype,))
        res = con.fetchall()

        if res:
            return res[0][0]

        return None


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'file_types',
    id_field,
    _con.TextField('extension', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('mimetype', default='""', no_null=True),
    _con.IntField('is_model', default='0', no_null=True),
    _con.IntField('is_image', default='0', no_null=True),
    _con.IntField('is_datasheet', default='0', no_null=True),
    _con.IntField('is_cad', default='0', no_null=True)
)
