from .. import db_connectors as _con
from ... import logger as _logger


def add_records(con, splash):
    con.execute('SELECT id FROM splice_types WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building splice types...')

    data = ((0, "Unknown"), (1, "Butt"), (2, "Cable"), (3, "Closed End"),
            (4, "Parallel"), (5, "Pigtail"), (6, "Tap"),
            (7, "Thru"), (8, "Solder Sleeve"), (9, "Solder Sleeve w/Pigtail"))

    splash.SetText(f'Adding splice types to db [{len(data)} | {len(data)}]...')
    con.executemany('INSERT INTO splice_types (id, name) VALUES(?, ?);', data)
    con.commit()


def get_splice_type_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM splice_types WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        _logger.logger.database(f'adding splice type ("{name}")')

        con.execute('INSERT INTO splice_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        _logger.logger.database(f'splice type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'splice_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
