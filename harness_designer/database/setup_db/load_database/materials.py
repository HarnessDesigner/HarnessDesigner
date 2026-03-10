from ... import db_connectors as _con


def add_materials(con, cur, splash):
    res = cur.execute('SELECT * FROM materials;').fetchall()

    if res:
        return

    data = ((0, 'Unknown Material'),)

    try:
        splash.SetText(f'Adding materials to db [0 | {len(data)}]...')
        cur.executemany('INSERT INTO materials (id, name) VALUES(?, ?);', data)
        splash.SetText(f'Adding materials to db [{len(data)} | {len(data)}]...')
        con.commit()
    except:  # NOQA
        res = cur.execute('SELECT * FROM materials;').fetchall()
        print('ERROR:', res)
        raise


def get_material_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM materials WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding material ("{name}")')

        cur.execute('INSERT INTO materials (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: material added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

materials_table = _con.SQLTable(
    'materials',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)


def materials(con, cur):
    cur.execute('CREATE TABLE materials('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL'
                ');')
    con.commit()
