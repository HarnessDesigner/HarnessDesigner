from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash):
    con.execute('SELECT * FROM materials;')
    if con.fetchall():
        return

    data = ((0, 'Unknown Material'),)

    try:
        splash.SetText(f'Adding materials to db [{len(data)} | {len(data)}]...')
        con.executemany('INSERT INTO materials (id, name) VALUES(?, ?);', data)
        con.commit()
    except:  # NOQA
        res = con.execute('SELECT * FROM materials;').fetchall()
        _logger.logger.error(res)
        raise


def get_material_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM materials WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding material ("{name}")')

        con.execute('INSERT INTO materials (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'material added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'materials',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
