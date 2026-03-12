from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM shapes WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, 'Internal Use DO NOT DELETE'),)

    splash.SetText(f'Adding core CPA lock to db [1 | 1]...')

    con.executemany('INSERT INTO shapes (id, name) VALUES (?, ?);', data)
    con.commit()


def get_shape_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM shapes WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding shape ("{name}")')

        con.execute('INSERT INTO shapes (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: shape added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'shapes',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def shapes(con, cur):
#     cur.execute('CREATE TABLE shapes('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
