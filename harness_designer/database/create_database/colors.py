# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger
import os
import json
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
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

    con.execute('SELECT * from colors WHERE name="Black";')
    if con.fetchall():
        return

    json_path = os.path.join(data_path, 'colors.json')

    splash.SetText(f'Loading colors file...')
    splash.flush()

    _logger.database(json_path)

    with open(json_path, 'r') as f:
        data = json.loads(f.read())

    if isinstance(data, dict):
        data = [value for value in data.values()]

    data_len = len(data)
    splash.SetText(f'Adding color to db [0 | {data_len}]...', log=False)
    splash.flush()

    for i, item in enumerate(data):
        splash.SetText(f'Adding color to db [{i + 1} | {data_len}]...', log=False)

        add_color(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_color(con, name, rgb, id=None, commit=True): # NOQA
    """
    Add a color.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :param rgb: Value for ``rgb``.
    :type rgb: UNKNOWN

    :param id: Identifier for the ID.
    :type id: UNKNOWN

    :param commit: Value for ``commit``.
    :type commit: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if id is None:
        id = _id_generator.generate_global_row_id(con).bytes

    con.execute('INSERT INTO colors (id, name, rgb) '
                'VALUES (?, ?, ?);', (id, name, rgb))

    _logger.database(f'color added "{name}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_color_id(con, name):
    """
    Return the color ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM colors WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        con.execute('SELECT id FROM colors WHERE name=?;', (name.title(),))
        res = con.fetchall()

    if not res:
        print('MISSING COLOR:', name)
        return _id_generator.NIL_UUID.bytes
        # raise RuntimeError(name)

    return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'colors',
    id_field,
    _con.TextField('name', no_null=True),
    _con.IntField('rgb', default='""', no_null=True)
)
