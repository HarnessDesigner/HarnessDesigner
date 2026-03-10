from ... import db_connectors as _con


def add_cavity_locks(con, cur, splash):
    res = cur.execute('SELECT id FROM cavity_locks WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'No Lock'),
        (1, 'Cavity Lock'),
        (2, 'Clean Body'),
        (3, 'Locking Lance'),
        (4, 'Clean Body and Lance'),
        (5, 'Flex Arm'),
        (6, 'Insert Molded'),
        (7, 'Molded On'),
        (8, 'Nose Piece'),
        (9, 'Press Fit')
    )

    splash.SetText(f'Adding cavity locks to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO cavity_locks (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding cavity locks to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_cavity_lock_id(con, cur, name):
    if not name:
        return 0

    res = cur.execute(f'SELECT id FROM cavity_locks WHERE name="{name}";').fetchall()

    if not res:
        print(f'DATABASE: adding cavity lock ("{name}")')

        cur.execute('INSERT INTO cavity_locks (name) VALUES (?);', (name,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: cavity lock added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cavity_locks',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)


# def cavity_locks(con, cur):
#     cur.execute('CREATE TABLE cavity_locks('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL'
#                 ');')
#     con.commit()
