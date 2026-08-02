# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, _=None):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param _: Value for ``_``.
    :type _: UNKNOWN
    """

    con.execute('SELECT 1 FROM ip_supps LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building IP suppliments...')
    splash.flush()

    names = (
        ('D', 'Wire'),
        ('G', 'Oil resistant'),
        ('F', 'Oil resistant'),
        ('H', 'High voltage apparatus'),
        ('M', 'Motion during water test'),
        ('S', 'Stationary during water test'),
        ('W', 'Weather conditions')
    )

    data = tuple(
        (_id_generator.generate_global_row_id(con).bytes, name, description)
        for name, description in names)

    splash.SetText(f'Adding IP suppliments to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO ip_supps (id, name, description) VALUES (?, ?, ?);', data)
    con.commit()


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'ip_supps',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', no_null=True)
)
