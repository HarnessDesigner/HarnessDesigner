# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, data_path):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """
    con.execute('SELECT 1 FROM splice_types LIMIT 1;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'splice_types.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Splice Types file...')
        splash.flush()

        _logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding splice type to db [0 | {data_len}]...', log=False)
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding splice type to db [{i + 1} | {data_len}]...', log=False)

            # splice_types.json is a pre-UUID-migration seed file and still
            # carries a leftover integer "id" per entry -- discard it so
            # every row gets a freshly generated UUID id instead of
            # colliding integers.
            item.pop('id', None)
            add_splice_type(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_splice_type(con, name, commit=True):  # NOQA
    """Add a splice type.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    id = _id_generator.generate_global_row_id(con).bytes

    con.execute(
        'INSERT INTO splice_types (id, name) '
        'VALUES (?, ?);', (id, name)
        )

    _logger.database(f'splice type added "{name}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_splice_type_id(con, name):
    """Return the splice type ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM splice_types WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding splice type ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO splice_types (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'splice type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'splice_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
