import json
import os

from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM seal_types WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'seal_types.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Seal Types file...')
        splash.flush()

        _logger.logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding seal type to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding seal type to db [{i + 1} | {data_len}]...')
            add_seal_type(con, **item)

    con.commit()


def add_seal_type(con, name, id=None):  # NOQA

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

    con.commit()


def get_seal_type_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM seal_types WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding seal type ("{name}")')

        con.execute('INSERT INTO seal_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'seal type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'seal_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
