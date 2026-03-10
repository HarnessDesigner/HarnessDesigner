from ... import db_connectors as _con


def add_splice_types(con, cur, splash):
    res = cur.execute('SELECT id FROM splice_types WHERE id=0;')
    if res.fetchall():
        return

    data = ((0, "Unknown"), (1, "Butt"), (2, "Cable"), (3, "Closed End"),
            (4, "Parallel"), (5, "Pigtail"), (6, "Tap"),
            (7, "Thru"), (8, "Solder Sleeve"), (9, "Solder Sleeve w/Pigtail"))

    splash.SetText(f'Adding splice types to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO splice_types (id, name) VALUES(?, ?);', data)
    splash.SetText(f'Adding splice types to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_splice_type_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM splice_types WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding splice type ("{name}")')

        cur.execute('INSERT INTO splice_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: splice type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'splice_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def splice_types(con, cur):
#     cur.execute('CREATE TABLE splice_types('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
