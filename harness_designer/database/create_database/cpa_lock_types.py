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

    con.execute('SELECT 1 FROM cpa_lock_types LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building cpa lock types...')
    splash.flush()

    names = ('Lever', 'Steel Lever', 'Lever at Cover', 'Locking Lever', 'Lever Claw',
             'Locking Slide', 'Slide', 'Lever and Locking Slide',
             'Locking Lever and Locking Slide', 'External CPA Lock',
             'Plastic Clip or Metal Holder', 'Plastic Lever or Metal Lever',
             'Plastic Clip', 'Groove')

    data = ((_id_generator.NIL_UUID.bytes, 'No Lock'),) + tuple(
        (_id_generator.generate_global_row_id(con).bytes, name) for name in names)

    splash.SetText(f'Adding cpa lock types to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO cpa_lock_types (id, name) VALUES (?, ?);', data)

    con.commit()


@_check_types.do
def get_cpa_lock_type_id(con, name):
    """
    Return the CPA lock type ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param name: Name value.
    :type name: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM cpa_lock_types WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding cpa lock type ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO cpa_lock_types (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'cpa lock type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'cpa_lock_types',
    id_field,
    _con.TextField('name', no_null=True)
)
