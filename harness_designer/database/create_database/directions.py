from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash, _):
    con.execute('SELECT id FROM directions WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building directions...')
    splash.flush()

    data = ((0, "Unknown"), (1, "Left"), (2, "Right"), (3, "Straight"),
            (4, "90°"), (5, "180°"), (6, "270°"))

    splash.SetText(f'Adding directions to db [{len(data)} | {len(data)}]...')
    splash.flush()

    con.executemany('INSERT INTO directions (id, name) VALUES(?, ?);', data)
    con.commit()


def get_direction_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM directions WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding direction ("{name}")')

        con.execute('INSERT INTO directions (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'direction added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'directions',
    id_field,
    _con.TextField('name', no_null=True)
)
