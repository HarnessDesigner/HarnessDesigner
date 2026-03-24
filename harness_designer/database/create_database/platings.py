import json
import os

from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM platings WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'platings.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Plating file...')
        splash.flush()

        _logger.logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding plating to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding plating to db [{i + 1} | {data_len}]...')
            add_plating(con, **item)

    con.commit()


def add_plating(con, symbol, description='', id=None):

    if id is None:
        con.execute(
            'INSERT INTO platings (symbol, description) '
            'VALUES (?);', (symbol, description)
            )
    else:
        con.execute(
            'INSERT INTO platings (id, symbol, description) '
            'VALUES (?, ?);', (id, symbol, description)
            )

    con.commit()


def get_plating_id(con, symbol):
    if not symbol:
        return 0

    con.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding plating ("{symbol}")')

        con.execute('INSERT INTO platings (symbol) VALUES (?);', (symbol,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'plating added "{symbol}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'platings',
    id_field,
    _con.TextField('symbol', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
