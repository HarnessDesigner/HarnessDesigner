from ... import db_connectors as _con


def add_transition_series(con, cur, splash):
    res = cur.execute('SELECT id FROM transition_series WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)
    cur.executemany('INSERT INTO transition_series (id, name) VALUES (?, ?);', data)
    con.commit()


def get_transition_series_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM transition_series WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding transition series ("{name}")')

        cur.execute('INSERT INTO transition_series (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

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
