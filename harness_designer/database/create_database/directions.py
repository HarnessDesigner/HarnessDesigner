from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM directions WHERE id=0;')
    if con.fetchall():
        return

    data = ((0, "Unknown"), (1, "Left"), (2, "Right"), (3, "Straight"),
            (4, "90°"), (5, "180°"), (6, "270°"))

    splash.SetText(f'Adding directions to db [0 | {len(data)}]...')
    con.executemany('INSERT INTO directions (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding directions to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_direction_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM directions WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding direction ("{name}")')

        con.execute('INSERT INTO directions (name) VALUES (?);', (name,))

        con.commit()
        db_id = con.lastrowid

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
