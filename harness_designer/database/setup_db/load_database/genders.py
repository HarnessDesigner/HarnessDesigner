from ... import db_connectors as _con


def add_genders(con, cur, splash):
    res = cur.execute('SELECT id FROM genders WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Male"), (2, "Female"))

    splash.SetText(f'Adding genders to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO genders (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding genders to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_gender_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM genders WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding gender ("{name}")')
        cur.execute('INSERT INTO genders (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: gender added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

genders_table = _con.SQLTable(
    'genders',
    id_field,
    _con.TextField('name', no_null=True)
)


def genders(con, cur):
    cur.execute('CREATE TABLE genders('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL'
                ');')
    con.commit()
