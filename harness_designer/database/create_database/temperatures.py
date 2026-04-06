import os
import json

from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM temperatures WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'temperatures.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Temperatures file...')
        splash.flush()

        _logger.logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding temperature to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding temperature to db [{i + 1} | {data_len}]...')
            add_temperature(con, **item)

    con.commit()


def add_temperature(con, name, id=None):  # NOQA

    if id is None:
        con.execute(
            'INSERT INTO temperatures (name) '
            'VALUES (?);', (name,)
            )
    else:
        con.execute(
            'INSERT INTO temperatures (id, name) '
            'VALUES (?, ?);', (id, name)
            )

    con.commit()


def get_temperature_id(con, name):
    if name in ('', None):
        return 0

    if isinstance(name, str):
        if '-' in name:
            name = -int(name[1:].replace('°', '').replace('C', ''))
        else:
            name = int(name.replace('°', '').replace('C', ''))

    if name > 0:
        name = '+' + str(name) + '°C'
    else:
        name = str(name) + '°C'

    con.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding temperature ("{name}")')
        con.execute('INSERT INTO temperatures (name) VALUES (?);', (name,))

        con.commit()

        db_id = con.lastrowid
        _logger.logger.database(f'temperature added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'temperatures',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
