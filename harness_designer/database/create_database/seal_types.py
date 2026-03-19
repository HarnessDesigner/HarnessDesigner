from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash):
    con.execute('SELECT id FROM seal_types WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building seal types...')

    data = (
        (0, 'None'),
        (1, 'Unknown Seal'),
        (2, 'Axial Seal'),
        (3, 'Radial Seal'),
        (4, 'Rubber Cap Over Wires'),
        (5, 'Single Wire Seal'),
        (6, 'Mat Seal')
    )
    splash.SetText(f'Adding seal types to db [{len(data)} | {len(data)}]...')
    con.executemany('INSERT INTO seal_types (id, name) VALUES (?, ?);', data)

    con.commit()


def get_seal_type_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM seal_types WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding seal type ("{name}")')

        con.execute('INSERT INTO seal_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'seal type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'seal_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
