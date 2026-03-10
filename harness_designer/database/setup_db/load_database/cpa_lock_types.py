from ... import db_connectors as _con


def add_cpa_lock_types(con, cur, splash):
    res = cur.execute('SELECT id FROM cpa_lock_types WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'No Lock'),
        (1, 'Lever'),
        (2, 'Steel Lever'),
        (3, 'Lever at Cover'),
        (4, 'Locking Lever'),
        (5, 'Lever Claw'),
        (6, 'Locking Slide'),
        (7, 'Slide'),
        (8, 'Lever and Locking Slide'),
        (9, 'Locking Lever and Locking Slide'),
        (10, 'External CPA Lock'),
        (11, 'Plastic Clip or Metal Holder'),
        (12, 'Plastic Lever or Metal Lever'),
        (13, 'Plastic Clip'),
        (14, 'Groove')
    )

    splash.SetText(f'Adding cpa lock types to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO cpa_lock_types (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding cpa lock types to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_cpa_lock_type_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM cpa_lock_types WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding cpa lock type ("{name}")')

        cur.execute('INSERT INTO cpa_lock_types (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: cpa lock type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cpa_lock_types',
    id_field,
    _con.TextField('name', no_null=True)
)


# def cpa_lock_types(con, cur):
#     cur.execute('CREATE TABLE cpa_lock_types('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
