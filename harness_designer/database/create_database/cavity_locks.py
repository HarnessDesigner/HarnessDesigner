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
    con.execute('SELECT id FROM cavity_locks WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building cavity locks...')
    splash.flush()

    data = (
        (0, 'No Lock'),
        (1, 'Cavity Lock'),
        (2, 'Clean Body'),
        (3, 'Locking Lance'),
        (4, 'Clean Body and Lance'),
        (5, 'Flex Arm'),
        (6, 'Insert Molded'),
        (7, 'Molded On'),
        (8, 'Nose Piece'),
        (9, 'Press Fit')
    )

    splash.SetText(f'Adding cavity locks to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO cavity_locks (id, name) VALUES (?, ?);', data)

    con.commit()


def get_cavity_lock_id(con, name):
    """Return the cavity lock ID.

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

    con.execute(f'SELECT id FROM cavity_locks WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding cavity lock ("{name}")')

        con.execute('INSERT INTO cavity_locks (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'cavity lock added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cavity_locks',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
