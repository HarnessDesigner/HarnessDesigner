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
    con.execute('SELECT id FROM genders WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building genders...')
    splash.flush()

    data = ((0, "Unknown"), (1, "Male"), (2, "Female"))

    splash.SetText(f'Adding genders to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO genders (id, name) VALUES(?, ?);', data)
    con.commit()


def get_gender_id(con, name):
    """Return the gender ID.

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

    con.execute(f'SELECT id FROM genders WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding gender ("{name}")')
        con.execute('INSERT INTO genders (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'gender added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'genders',
    id_field,
    _con.TextField('name', no_null=True)
)
