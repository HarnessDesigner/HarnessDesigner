# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger


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
    con.execute('SELECT id FROM seal_types WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'seal_types.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Seal Types file...')
        splash.flush()

        _logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding seal type to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding seal type to db [{i + 1} | {data_len}]...')
            add_seal_type(con, commit=False, **item)

    con.commit()


def add_seal_type(con, name, id=None, commit=True):  # NOQA
    """Add a seal type.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param id: Identifier for the ID.
    :type id: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if id is None:
        con.execute(
            'INSERT INTO seal_types (name) '
            'VALUES (?);', (name,)
            )
    else:
        con.execute(
            'INSERT INTO seal_types (id, name) '
            'VALUES (?, ?);', (id, name)
            )

    _logger.database(f'seal type added "{name}"')

    if commit:
        con.commit()
        return con.lastrowid


def get_seal_type_id(con, name):
    """Return the seal type ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if not name:
        return 0

    con.execute(f'SELECT id FROM seal_types WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.database(f'adding seal type ("{name}")')

        con.execute('INSERT INTO seal_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.database(f'seal type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'seal_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
