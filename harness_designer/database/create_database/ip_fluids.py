import os

from .. import db_connectors as _con
from ... import logger as _logger


BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def add_records(con, splash):
    con.execute('SELECT id FROM ip_fluids WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building IP fluids...')
    splash.flush()

    data = (
        (0, '0', 'No Protection', 'No protection against ingress of water.', None),
        (1, '1', 'Dripping water', 'Dripping water (vertically falling drops) shall have no unsafe effect on the specimen when mounted upright.', open(f'{BASE_PATH}/image/ip/IPX1.png', 'rb').read()),
        (2, '2', 'Dripping water when tilted at 15°', 'Vertically dripping water shall have no harmful effect when the enclosure is tilted at an angle of 15° from its normal position.', open(f'{BASE_PATH}/image/ip/IPX2.png', 'rb').read()),
        (3, '3', 'Spraying water', 'Water falling as a spray at any angle up to 60° from the vertical shall have no harmful effect.', open(f'{BASE_PATH}/image/ip/IPX3.png', 'rb').read()),
        (4, '4', 'Splashing water', 'Water splashing against the enclosure from any direction shall have no harmful effect.', open(f'{BASE_PATH}/image/ip/IPX4.png', 'rb').read()),
        (5, '5', 'Water jets', 'Water projected by a nozzle (6.3 mm) against enclosure from any direction shall have no harmful effects.', open(f'{BASE_PATH}/image/ip/IPX5.png', 'rb').read()),
        (6, '6', 'Powerful water jets', 'Water projected in powerful jets (12.5 mm nozzle) against the enclosure from any direction shall have no harmful effects.', open(f'{BASE_PATH}/image/ip/IPX6.png', 'rb').read()),
        (7, '7', 'Immersion, up to 1 meter', 'Ingress of water in harmful quantity shall not be possible when the enclosure is immersed in water.', open(f'{BASE_PATH}/image/ip/IPX7.png', 'rb').read()),
        (8, '8', 'Immersion, 1 meter or more depth', 'The equipment is suitable for continuous immersion in water.', open(f'{BASE_PATH}/image/ip/IPX8.png', 'rb').read()),
        (9, '9', 'Powerful high-temperature water jets', 'Protected against close-range high-pressure, high-temperature spray downs.', open(f'{BASE_PATH}/image/ip/IPX9.png', 'rb').read()),
        (10, '6K', 'Powerful water jets with increased pressure', 'Water projected in powerful jets (6.3 mm nozzle) against the enclosure from any direction, under elevated pressure.', open(f'{BASE_PATH}/image/ip/IPX6K.png', 'rb').read()),
        (11, '9K', 'Steam Cleaning', 'Protection against high-pressure, high-temperature jet sprays, wash-downs or steam-cleaning procedures', open(f'{BASE_PATH}/image/ip/IPX9K.png', 'rb').read()),
        (12, 'X', 'Unknown', 'No data is available to specify a protection rating about this criterion.', None)
    )

    splash.SetText(f'Adding IP fluids to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO ip_fluids (id, name, short_desc, description, icon_data) VALUES (?, ?, ?, ?, ?);', data)

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'ip_fluids',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('short_desc', no_null=True),
    _con.TextField('description', no_null=True),
    _con.BlobField('icon_data', default='"NULL"'),

)
