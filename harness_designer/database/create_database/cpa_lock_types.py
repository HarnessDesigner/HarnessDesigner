from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, _):
    con.execute('SELECT id FROM cpa_lock_types WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building cpa lock types...')
    splash.flush()

    data = (
        (0, 'No Lock'),
        (1, 'Lever'),
        (2, 'Steel Lever'),
        (3, 'Lever at Cover'),
        (4, 'Locking Lever'),
        (5, 'Lever Claw'),
        (6, 'Locking Slide'),
        (7, 'Slide'),
        (8, 'Lever and Locking Slide'),
        (9, 'Locking Lever and Locking Slide'),
        (10, 'External CPA Lock'),
        (11, 'Plastic Clip or Metal Holder'),
        (12, 'Plastic Lever or Metal Lever'),
        (13, 'Plastic Clip'),
        (14, 'Groove')
    )

    splash.SetText(f'Adding cpa lock types to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO cpa_lock_types (id, name) VALUES (?, ?);', data)

    con.commit()


def get_cpa_lock_type_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM cpa_lock_types WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding cpa lock type ("{name}")')

        con.execute('INSERT INTO cpa_lock_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'cpa lock type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cpa_lock_types',
    id_field,
    _con.TextField('name', no_null=True)
)
