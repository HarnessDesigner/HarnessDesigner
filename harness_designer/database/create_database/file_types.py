# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger

import os
import json


def add_records(con, splash, data_path):
    con.execute('SELECT * from file_types WHERE id=1;')
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


def add_file_type(con, name, extension, is_model, mimetype='', commit=True):
    con.execute('INSERT INTO file_types (mimetype, extension, name, is_model) '
                'VALUES (?, ?, ?, ?);', (mimetype, extension, name, is_model))

    _logger.logger.database(f'file type added "{extension}"')

    if commit:
        con.commit()
        return con.lastrowid


def get_file_type(con, extension=None, mimetype=None):
    if extension is None and mimetype is None:
        return None

    if extension is not None and mimetype is not None:
        con.execute(f'SELECT id FROM file_types WHERE extension="{extension}" AND mimetype="{mimetype}";')
        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.logger.database(f'adding file type ("{extension}", "{mimetype}")')

        con.execute('INSERT INTO file_types (extension, mimetype) VALUES (?, ?);', (extension, mimetype))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif extension is not None:
        con.execute(f'SELECT id FROM file_types WHERE extension="{extension}";')
        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.logger.database(f'adding file type ("{extension}")')

        con.execute('INSERT INTO file_types (extension,) VALUES (?);', (extension,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif mimetype is not None:
        con.execute(f'SELECT id FROM file_types WHERE mimetype="{mimetype}";')
        res = con.fetchall()

        if res:
            return res[0][0]

        return None


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'file_types',
    id_field,
    _con.TextField('extension', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('mimetype', default='""', no_null=True),
    _con.IntField('is_model', default='1', no_null=True)

)
