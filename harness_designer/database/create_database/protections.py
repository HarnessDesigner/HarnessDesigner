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
    con.execute('SELECT id FROM protections WHERE id=0;')
    if con.fetchall():
        return

    data = (dict(id=0, name='No Protection'),)

    splash.SetText(f'Adding protections to db [0 | {len(data)}]...')
    splash.flush()

    for item in data:
        splash.SetText(f'Adding protections to db [1 | {len(data)}]...')
        add_protection(con, commit=False, **item)


def add_protection(con, name, id=None, commit=True):  # NOQA
    """Add a protection.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param id: Identifier for the ID.
    :type id: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if id is None:
        con.execute(
            'INSERT INTO protections (name) '
            'VALUES (?);', (name,)
            )
    else:
        con.execute(
            'INSERT INTO protections (id, name) '
            'VALUES (?, ?);', (id, name)
            )

    _logger.logger.database(f'protection added "{repr(name)}"')

    if commit:
        con.commit()
        return con.lastrowid


def get_protection_id(con, name):
    """Return the protection ID.

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

    con.execute(f'SELECT id FROM protections WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding protection ("{name}")')

        con.execute('INSERT INTO protections (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'protection added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'protections',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
