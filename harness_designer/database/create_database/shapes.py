from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, _):
    con.execute('SELECT id FROM shapes WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, 'No Shape'),)

    splash.SetText(f'Adding shape to db [1 | 1]...')
    splash.flush()

    con.executemany('INSERT INTO shapes (id, name) VALUES (?, ?);', data)
    con.commit()


def get_shape_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM shapes WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding shape ("{name}")')

        con.execute('INSERT INTO shapes (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'shape added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'shapes',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
