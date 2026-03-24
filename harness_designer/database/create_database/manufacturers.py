import json
import os

from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, data_path):
    con.execute('SELECT id FROM manufacturers WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'manufacturers.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Manufacturers file...')
        splash.flush()

        _logger.logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding manufacturer to db [0 | {data_len}]...')
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding manufacturer to db [{i + 1} | {data_len}]...')
            add_manufacturer(con, **item)

    con.commit()


def add_manufacturer(con, name, description='', address='', contact_person='', phone='',
                     ext='', email='', website='', id=None):

    if id is None:
        con.execute(
            'INSERT INTO manufacturers (name, description, address, contact_person, phone, ext, email, website) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
            (name, description, address, contact_person, phone, ext, email, website)
            )
    else:
        con.execute(
            'INSERT INTO manufacturers (id, name, description, address, contact_person, phone, ext, email, website) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
            (id, name, description, address, contact_person, phone, ext, email, website)
            )

    con.commit()


def get_mfg_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM manufacturers WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding manufacturer ("{name}", "", "", "", "")')
        con.execute('INSERT INTO manufacturers (name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?);', (name, '', '', '', ''))

        con.commit()
        db_id = con.lastrowid
        _logger.logger.database(f'manufacturer added "{name}" = {db_id}')

        return db_id

    else:
        return res[0][0]



id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'manufacturers',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.TextField('address', default='""', no_null=True),
    _con.TextField('contact_person', default='""', no_null=True),
    _con.TextField('phone', default='""', no_null=True),
    _con.TextField('ext', default='""', no_null=True),
    _con.TextField('email', default='""', no_null=True),
    _con.TextField('website', default='""', no_null=True)
)
