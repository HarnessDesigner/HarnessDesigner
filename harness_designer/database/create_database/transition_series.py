# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, _):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param _: Value for ``_``.
    :type _: UNKNOWN
    """
    con.execute('SELECT 1 FROM transition_series LIMIT 1;')
    if con.fetchall():
        return

    data = ((_id_generator.generate_global_row_id(con).bytes, 'Internal Use DO NOT DELETE'),)

    splash.SetText(f'Adding transition series to db [1 | 1]...')
    splash.flush()

    con.executemany('INSERT INTO transition_series (id, name) VALUES (?, ?);', data)
    con.commit()


@_check_types.do
def get_transition_series_id(con, name):
    """Return the transition series ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM transition_series WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding transition series ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO transition_series (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'transition series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'transition_series',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
