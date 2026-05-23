# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger


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
    con.execute('SELECT id FROM transition_series WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)

    splash.SetText(f'Adding transition series to db [1 | 1]...')
    splash.flush()

    con.executemany('INSERT INTO transition_series (id, name) VALUES (?, ?);', data)
    con.commit()


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
        return 0

    con.execute(f'SELECT id FROM transition_series WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding transition series ("{name}")')

        con.execute('INSERT INTO transition_series (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'transition series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'transition_series',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
