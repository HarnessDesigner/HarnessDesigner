# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from .. import db_connectors as _con
from ... import check_types as _check_types
from .. import id_generator as _id_generator


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


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

    con.execute('SELECT 1 FROM ip_solids LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building IP solids...')
    splash.flush()

    rows = (
        ('0', 'No Protection',
         'No protection against contact and ingress of objects.'),

        ('1', '>= 50.00mm sized objects',
         '>= 50.00mm sized objects\n'
         'Any large surface of the body, such as the back\n'
         'of a hand, but no protection against deliberate\n'
         'contact with a body part.'),

        ('2', '>= 12.50mm sized objects',
         '>= 12.50mm sized objects\n'
         'Fingers or similar objects.'),

        ('3', '>= 2.50mm sized objects',
         '>= 2.50mm sized objects\n'
         'Tools, thick wires, etc.'),

        ('4', '>= 1.00mm sized objects',
         '>= 1.00mm sized objects\n'
         'Most wires, slender screws, large ants, etc.'),

        ('5', 'Dust Protected',
         'Dust Protected\n'
         'Ingress of dust is not entirely prevented.'),

        ('6', 'Dust Tight',
         'Dust Tight\n'
         'No ingress of dust.'),

        ('X', 'Unknown',
         'No data is available to specify a protection\n'
         'rating about this criterion.')
    )

    data = tuple(
        (_id_generator.generate_global_row_id(con).bytes, name, short_desc, description)
        for name, short_desc, description in rows)

    splash.SetText(f'Adding IP solids to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO ip_solids (id, name, short_desc, description) VALUES (?, ?, ?, ?);', data)

    con.commit()


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'ip_solids',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('short_desc', no_null=True),
    _con.TextField('description', no_null=True)
)
