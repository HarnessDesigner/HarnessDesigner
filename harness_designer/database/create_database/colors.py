from .. import db_connectors as _con
from ... import logger as _logger
import os
import json


def add_records(con, splash, data_path):
    con.execute('SELECT * from colors WHERE name="Black";')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'colors.json')

    splash.SetText(f'Loading colors file...')
    splash.flush()

    _logger.logger.database(json_path)

    with open(json_path, 'r') as f:
        data = json.loads(f.read())

    if isinstance(data, dict):
        data = [value for value in data.values()]

    data_len = len(data)
    splash.SetText(f'Adding color to db [0 | {data_len}]...')
    splash.flush()

    for i, item in enumerate(data):
        splash.SetText(f'Adding color to db [{i + 1} | {data_len}]...')

        add_color(con, **item)

    con.commit()


def add_color(con, name, rgb, id=None):
    if id is None:
        con.execute('INSERT INTO colors (name, rgb) '
                    'VALUES (?, ?);', (name, rgb))
    else:
        con.execute('INSERT INTO colors (id, name, rgb) '
                    'VALUES (?, ?, ?);', (id, name, rgb))

    con.commit()


def get_color_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM colors WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        con.execute(f'SELECT id FROM colors WHERE name="{name.title()}";')
        res = con.fetchall()

    if not res:
        raise RuntimeError(name)

    return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'colors',
    id_field,
    _con.TextField('name', no_null=True),
    _con.IntField('rgb', default='""', no_null=True)
)
