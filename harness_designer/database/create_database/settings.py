# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from .. import db_connectors as _con
from ... import logger as _logger


def get_setting(con, name):  # NOQA
    """Return the setting.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    con.execute(f'SELECT value FROM settings WHERE name="{name}";')
    res = con.fetchall()
    return res[0][0]


def add_records(con, splash, appdata):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param appdata: Value for ``appdata``.
    :type appdata: UNKNOWN
    """
    con.execute('SELECT id FROM settings WHERE id=1;')
    if con.fetchall():
        return

    splash.SetText(f'Building settings...')
    splash.flush()

    model_path = os.path.join(appdata, 'models')
    image_path = os.path.join(appdata, 'images')
    cad_path = os.path.join(appdata, 'cads')
    datasheet_path = os.path.join(appdata, 'datasheets')

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    if not os.path.exists(image_path):
        os.makedirs(image_path)

    if not os.path.exists(cad_path):
        os.makedirs(cad_path)

    if not os.path.exists(datasheet_path):
        os.makedirs(datasheet_path)

    for i in range(0x00, 0x100):
        i = f'{i:02x}'
        for pth in (model_path, image_path, cad_path, datasheet_path):
            pth = os.path.join(pth, i)
            if not os.path.exists(pth):
                os.mkdir(pth)

    splash.SetText(f'Adding setting to db [1 | 4]...')
    splash.flush()

    con.execute(f'INSERT INTO settings (id, name, value) VALUES(1, "model_path", "{model_path}");')

    splash.SetText(f'Adding setting to db [2 | 4]...')
    splash.flush()

    con.execute(f'INSERT INTO settings (id, name, value) VALUES(2, "image_path", "{image_path}");')

    splash.SetText(f'Adding setting to db [3 | 4]...')
    splash.flush()

    con.execute(f'INSERT INTO settings (id, name, value) VALUES(3, "cad_path", "{cad_path}");')

    splash.SetText(f'Adding setting to db [4 | 4]...')
    splash.flush()

    con.execute(f'INSERT INTO settings (id, name, value) VALUES(4, "datasheet_path", "{datasheet_path}");')

    con.commit()


def add_setting(con, key, value, commit=True):
    """Add a setting.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param key: Lookup key.
    :type key: UNKNOWN
    :param value: Value to store or process.
    :type value: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    con.execute(f'INSERT INTO pjt_transition_branches (name, value) VALUES (?, ?);',
                (key, value))

    _logger.logger.database(f'setting added "{key}"')

    if commit:
        con.commit()
        return con.lastrowid


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'settings',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('value', no_null=True)
)
