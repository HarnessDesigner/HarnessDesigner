# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import json

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
    con.execute('SELECT 1 FROM temperatures LIMIT 1;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'temperatures.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Temperatures file...')
        splash.flush()

        _logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding temperature to db [0 | {data_len}]...', log=False)
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding temperature to db [{i + 1} | {data_len}]...', log=False)

            # temperatures.json is a pre-UUID-migration seed file and still
            # carries a leftover integer "id" per entry -- discard it so
            # every row gets a freshly generated UUID id instead of
            # colliding integers.
            item.pop('id', None)
            add_temperature(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_temperature(con, name, commit=True):  # NOQA
    """Add a temperature.

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
        'INSERT INTO temperatures (id, name) '
        'VALUES (?, ?);', (id, name)
        )

    _logger.database(f'temperature added "{name}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_temperature_id(con, name):
    """Return the temperature ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if name in ('', None):
        return _id_generator.NIL_UUID.bytes

    if isinstance(name, str):
        if '-' in name:
            name = -int(name[1:].replace('°', '').replace('C', ''))
        else:
            name = int(name.replace('°', '').replace('C', ''))

    if name > 0:
        name = '+' + str(name) + '°C'
    else:
        name = str(name) + '°C'

    con.execute('SELECT id FROM temperatures WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding temperature ("{name}")')
        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO temperatures (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'temperature added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'temperatures',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
