from ... import db_connectors as _con


def add_directions(con, cur, splash):
    res = cur.execute('SELECT id FROM directions WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Left"), (2, "Right"), (3, "Straight"),
            (4, "90°"), (5, "180°"), (6, "270°"))

    splash.SetText(f'Adding directions to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO directions (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding directions to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_direction_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM directions WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding direction ("{name}")')

        cur.execute('INSERT INTO directions (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: direction added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'directions',
    id_field,
    _con.TextField('name', no_null=True)
)


# def directions(con, cur):
#     cur.execute('CREATE TABLE directions('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
