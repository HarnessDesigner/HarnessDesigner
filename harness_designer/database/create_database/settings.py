# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
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


@_check_types.do
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
    con.execute('SELECT id FROM settings WHERE name="model_path";')
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

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO settings (id, name, value) VALUES(?, "model_path", ?);',
                (new_id, model_path))

    splash.SetText(f'Adding setting to db [2 | 4]...')
    splash.flush()

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO settings (id, name, value) VALUES(?, "image_path", ?);',
                (new_id, image_path))

    splash.SetText(f'Adding setting to db [3 | 4]...')
    splash.flush()

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO settings (id, name, value) VALUES(?, "cad_path", ?);',
                (new_id, cad_path))

    splash.SetText(f'Adding setting to db [4 | 4]...')
    splash.flush()

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO settings (id, name, value) VALUES(?, "datasheet_path", ?);',
                (new_id, datasheet_path))

    con.commit()


@_check_types.do
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

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO settings (id, name, value) VALUES (?, ?, ?);',
                (new_id, key, value))

    _logger.database(f'setting added "{key}"')

    if commit:
        con.commit()
        return new_id


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'settings',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('value', no_null=True)
)
