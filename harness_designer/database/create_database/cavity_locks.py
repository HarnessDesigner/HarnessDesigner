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

    con.execute('SELECT 1 FROM cavity_locks LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building cavity locks...')
    splash.flush()

    names = ('Cavity Lock', 'Clean Body', 'Locking Lance', 'Clean Body and Lance',
             'Flex Arm', 'Insert Molded', 'Molded On', 'Nose Piece', 'Press Fit')

    data = ((_id_generator.NIL_UUID.bytes, 'No Lock'),) + tuple(
        (_id_generator.generate_global_row_id(con).bytes, name) for name in names)

    splash.SetText(f'Adding cavity locks to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO cavity_locks (id, name) VALUES (?, ?);', data)

    con.commit()


@_check_types.do
def get_cavity_lock_id(con, name):
    """
    Return the cavity lock ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM cavity_locks WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding cavity lock ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO cavity_locks (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'cavity lock added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'cavity_locks',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
