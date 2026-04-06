import os

from .. import db_connectors as _con


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def add_records(con, splash, _=None):
    con.execute('SELECT id FROM ip_fluids WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building IP fluids...')
    splash.flush()

    data = (
        (0, '0', 'No Protection', 'No protection against ingress of water.', None),
        (1, '1', 'Dripping water',
         'Dripping water (vertically falling drops)\n'
         'shall have no unsafe effect on the specimen\n'
         'when mounted upright.'),

        (2, '2', 'Dripping water when tilted at 15°',
         'Vertically dripping water shall have no harmful\n'
         'effect when the enclosure is tilted at an angle\n'
         'of 15° from its normal position.'),

        (3, '3', 'Spraying water',
         'Water falling as a spray at any angle up to 60°\n'
         'from the vertical shall have no harmful effect.'),

        (4, '4', 'Splashing water',
         'Water splashing against the enclosure from any\n'
         'direction shall have no harmful effect.'),

        (5, '5', 'Water jets',
         'Water projected by a nozzle (6.3 mm) against enclosure\n'
         'from any direction shall have no harmful effects.'),

        (6, '6', 'Powerful water jets',
         'Water projected in powerful jets (12.5 mm nozzle)\n'
         'against the enclosure from any direction shall have\n'
         'no harmful effects.'),

        (7, '7', 'Immersion, up to 1 meter',
         'Ingress of water in harmful quantity shall not be\n'
         'possible when the enclosure is immersed in water.'),

        (8, '8', 'Immersion, 1 meter or more depth',
         'The equipment is suitable for continuous\n'
         'immersion in water.'),

        (9, '9', 'Powerful high-temperature water jets',
         'Protected against close-range high-pressure,\n'
         'high-temperature spray downs.'),

        (10, '6K', 'Powerful water jets with increased pressure',
         'Water projected in powerful jets (6.3 mm nozzle)\n'
         'against the enclosure from any direction, under\n'
         'elevated pressure.'),

        (11, '9K', 'Steam Cleaning',
         'Protection against high-pressure, high-temperature\n'
         'jet sprays, wash-downs or steam-cleaning procedures'),

        (12, 'X', 'Unknown',
         'No data is available to specify a\n'
         'protection rating about this criterion.')
    )

    splash.SetText(f'Adding IP fluids to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO ip_fluids (id, name, short_desc, description) VALUES (?, ?, ?, ?);', data)

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'ip_fluids',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('short_desc', no_null=True),
    _con.TextField('description', no_null=True)
)
