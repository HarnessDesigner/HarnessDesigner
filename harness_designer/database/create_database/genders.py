from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM genders WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, "Unknown"), (1, "Male"), (2, "Female"))

    splash.SetText(f'Adding genders to db [0 | {len(data)}]...')
    con.executemany('INSERT INTO genders (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding genders to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_gender_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM genders WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding gender ("{name}")')
        con.execute('INSERT INTO genders (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: gender added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'genders',
    id_field,
    _con.TextField('name', no_null=True)
)


# def genders(con, cur):
#     cur.execute('CREATE TABLE genders('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
