import os

from .. import db_connectors as _con


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def add_records(con, splash, _=None):
    con.execute('SELECT id FROM ip_solids WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building IP solids...')
    splash.flush()

    data = (
        (0, '0', 'No Protection',
         'No protection against contact and ingress of objects.', None),

        (1, '1', '>= 50.00mm sized objects',
         '>= 50.00mm sized objects\n'
         'Any large surface of the body, such as the back\n'
         'of a hand, but no protection against deliberate\n'
         'contact with a body part.'),

        (2, '2', '>= 12.50mm sized objects',
         '>= 12.50mm sized objects\n'
         'Fingers or similar objects.'),

        (3, '3', '>= 2.50mm sized objects',
         '>= 2.50mm sized objects\n'
         'Tools, thick wires, etc.'),

        (4, '4', '>= 1.00mm sized objects',
         '>= 1.00mm sized objects\n'
         'Most wires, slender screws, large ants, etc.'),

        (5, '5', 'Dust Protected',
         'Dust Protected\n'
         'Ingress of dust is not entirely prevented.'),

        (6, '6', 'Dust Tight',
         'Dust Tight\n'
         'No ingress of dust.'),

        (7, 'X', 'Unknown',
         'No data is available to specify a protection\n'
         'rating about this criterion.')
    )

    splash.SetText(f'Adding IP solids to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO ip_solids (id, name, short_desc, description) VALUES (?, ?, ?, ?);', data)

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'ip_solids',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('short_desc', no_null=True),
    _con.TextField('description', no_null=True)
)
