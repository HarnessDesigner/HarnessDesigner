# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, _):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param _: Value for ``_``.
    :type _: UNKNOWN
    """

    con.execute('SELECT 1 FROM genders LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building genders...')
    splash.flush()

    data = (
        (_id_generator.NIL_UUID.bytes, "Unknown"),
        (_id_generator.generate_global_row_id(con).bytes, "Male"),
        (_id_generator.generate_global_row_id(con).bytes, "Female"),
    )

    splash.SetText(f'Adding genders to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO genders (id, name) VALUES(?, ?);', data)
    con.commit()


@_check_types.do
def get_gender_id(con, name):
    """
    Return the gender ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM genders WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding gender ("{name}")')
        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO genders (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'gender added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'genders',
    id_field,
    _con.TextField('name', no_null=True)
)
