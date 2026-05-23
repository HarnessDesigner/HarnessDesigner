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
    con.execute('SELECT id FROM directions WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building directions...')
    splash.flush()

    data = ((0, "Unknown"), (1, "Left"), (2, "Right"), (3, "Straight"),
            (4, "90°"), (5, "180°"), (6, "270°"))

    splash.SetText(f'Adding directions to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO directions (id, name) VALUES(?, ?);', data)
    con.commit()


def get_direction_id(con, name):
    """Return the direction ID.

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

    con.execute(f'SELECT id FROM directions WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding direction ("{name}")')

        con.execute('INSERT INTO directions (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'direction added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'directions',
    id_field,
    _con.TextField('name', no_null=True)
)
