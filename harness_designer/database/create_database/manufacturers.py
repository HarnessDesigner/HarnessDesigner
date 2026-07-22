# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger


def inspect_mfg_fam_series(mfg_name, family_name, series_name):
    """
    Execute the inspect mfg fam series operation.

    :param mfg_name: Value for ``mfg_name``.
    :type mfg_name: UNKNOWN

    :param family_name: Value for ``family_name``.
    :type family_name: UNKNOWN

    :param series_name: Value for ``series_name``.
    :type series_name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if family_name is None:
        family_name = ''
    if series_name is None:
        series_name = ''

    if family_name.lower().startswith(mfg_name.lower()):
        family_name = family_name[len(mfg_name):]

    if series_name.lower().startswith(family_name.lower()):
        series_name = series_name[len(family_name):]

    if mfg_name in ('RAYCHEM', 'Raychem'):
        if not family_name.strip():
            family_name = 'Raychem'
        elif not series_name.strip():
            series_name = family_name.strip()
            family_name = 'Raychem'
        else:
            family_name = 'Raychem ' + family_name.strip()

        mfg_name = 'TE Connectivity'

    mfg_name = mfg_name.strip()
    family_name = family_name.strip()
    series_name = series_name.strip()

    if not family_name:
        family_name = None

    if not series_name:
        series_name = None

    return mfg_name, family_name, series_name


def add_records(con, splash, data_path):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param data_path: Value for ``data_path``.
    :type data_path: UNKNOWN
    """

    con.execute('SELECT id FROM manufacturers WHERE id=0;')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'manufacturers.json')

    if os.path.exists(json_path):
        splash.SetText(f'Loading Manufacturers file...')
        splash.flush()

        _logger.database(json_path)

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        if isinstance(data, dict):
            data = [value for value in data.values()]

        data_len = len(data)

        splash.SetText(f'Adding manufacturer to db [0 | {data_len}]...', log=False)
        splash.flush()

        for i, item in enumerate(data):
            splash.SetText(f'Adding manufacturer to db [{i + 1} | {data_len}]...', log=False)
            add_manufacturer(con, commit=False, **item)

    con.commit()


def add_manufacturer(con, name, description='', address='', contact_person='', phone='',
                     ext='', email='', website='', id=None, commit=True):  # NOQA
    """
    Add a manufacturer.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :param description: Value for ``description``.
    :type description: UNKNOWN

    :param address: Value for ``address``.
    :type address: UNKNOWN

    :param contact_person: Value for ``contact_person``.
    :type contact_person: UNKNOWN

    :param phone: Value for ``phone``.
    :type phone: UNKNOWN

    :param ext: Value for ``ext``.
    :type ext: UNKNOWN

    :param email: Value for ``email``.
    :type email: UNKNOWN

    :param website: Value for ``website``.
    :type website: UNKNOWN

    :param id: Identifier for the ID.
    :type id: UNKNOWN

    :param commit: Value for ``commit``.
    :type commit: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

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

    _logger.database(f'manufacturer added "{name}"')

    if commit:
        con.commit()
        return con.lastrowid


def get_mfg_id(con, name):
    """
    Return the mfg ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not name:
        return 0

    con.execute(f'SELECT id FROM manufacturers WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.database(f'adding manufacturer ("{name}", "", "", "", "")')
        con.execute('INSERT INTO manufacturers (name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?);', (name, '', '', '', ''))

        con.commit()
        db_id = con.lastrowid
        _logger.database(f'manufacturer added "{name}" = {db_id}')

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
