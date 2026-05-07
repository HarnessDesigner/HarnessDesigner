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

        splash.SetText(f'Adding plating to db [0 | {data_len}]...', log=False)
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding plating to db [{i + 1} | {data_len}]...', log=False)
            add_plating(con, commit=False, **item)

    con.commit()


def add_plating(con, symbol, description='', id=None, commit=True):  # NOQA

    if id is None:
        con.execute('INSERT INTO platings (symbol, description) '
                    'VALUES (?, ?);', (symbol, description))
    else:
        con.execute('INSERT INTO platings (id, symbol, description) '
                    'VALUES (?, ?, ?);', (id, symbol, description))

    _logger.logger.database(f'plating added "{symbol}" - "{description}"')

    if commit:
        con.commit()
        return con.lastrowid


def get_plating_id(con, symbol):
    if not symbol:
        return 0

    con.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";')
    rows = con.fetchall()

    if not rows:
        con.execute(f'SELECT id FROM platings WHERE description="{symbol}";')
        rows = con.fetchall()

    if not rows:
        con.execute(f'SELECT symbol, description FROM platings;')
        rows = con.fetchall()

        items = {}

        platings = {row[1]: row[0] for row in rows}

        for key, value in platings.items():
            if key.lower() in symbol.lower():
                items[symbol.lower().find(key.lower())] = value

        if items:
            description = symbol
            symbol = []
            for key in sorted(list(items.keys())):
                symbol.append(items[key])

            symbol = '/'.join(symbol)

            con.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";')
            rows = con.fetchall()

            if rows:
                return rows[0][0]

        else:
            description = ''

        _logger.logger.database(f'adding plating ("{symbol}", "{description}")')

        con.execute('INSERT INTO platings (symbol, description) VALUES (?, ?);',
                    (symbol, description))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'plating added "{symbol}" = {db_id}')

        return db_id
    else:
        return rows[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'platings',
    id_field,
    _con.TextField('symbol', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
