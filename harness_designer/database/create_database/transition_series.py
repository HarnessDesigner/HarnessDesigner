from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM transition_series WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)

    splash.SetText(f'Adding transition series to db [1 | 1]...')
    con.executemany('INSERT INTO transition_series (id, name) VALUES (?, ?);', data)
    con.commit()


def get_transition_series_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM transition_series WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding transition series ("{name}")')

        con.execute('INSERT INTO transition_series (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: transition series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'transition_series',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def transition_series(con, cur):
#     cur.execute('CREATE TABLE transition_series('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
