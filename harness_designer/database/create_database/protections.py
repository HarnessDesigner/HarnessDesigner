from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM protections WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, 'No Protection'),)

    splash.SetText(f'Adding protections to db [{len(data)} | {len(data)}]...')
    con.executemany('INSERT INTO protections (id, name) VALUES (?, ?);', data)
    con.commit()


def get_protection_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM protections WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding protection ("{name}")')

        con.execute('INSERT INTO protections (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: protection added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'protections',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def protections(con, cur):
#     cur.execute('CREATE TABLE protections('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT NOT NULL'
#                 ');')
#     con.commit()
