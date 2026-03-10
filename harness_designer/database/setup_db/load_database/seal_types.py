from ... import db_connectors as _con


def add_seal_types(con, cur, splash):
    res = cur.execute('SELECT id FROM seal_types WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'None'),
        (1, 'Unknown Seal'),
        (2, 'Axial Seal'),
        (3, 'Radial Seal'),
        (4, 'Rubber Cap Over Wires'),
        (5, 'Single Wire Seal'),
        (5, 'Mat Seal')
    )

    splash.SetText(f'Adding seal types to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO seal_types (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding seal types to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_seal_type_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM seal_types WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding seal type ("{name}")')

        cur.execute('INSERT INTO seal_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: seal type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

seal_types_table = _con.SQLTable(
    'seal_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def seal_types(con, cur):
#     cur.execute('CREATE TABLE seal_types('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL);')
#     con.commit()
