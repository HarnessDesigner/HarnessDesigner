from ... import db_connectors as _con


def add_ip_supps(con, cur, splash):
    res = cur.execute('SELECT id FROM ip_supps WHERE id=0;')
    if res.fetchall():
        return

    data = (
        ('D', 'Wire'),
        ('G', 'Oil resistant'),
        ('F', 'Oil resistant'),
        ('H', 'High voltage apparatus'),
        ('M', 'Motion during water test'),
        ('S', 'Stationary during water test'),
        ('W', 'Weather conditions')
    )
    splash.SetText(f'Adding IP suppliments to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_supps (name, description) VALUES (?, ?);', data)
    splash.SetText(f'Adding IP suppliments to db [{len(data)} | {len(data)}]...')
    con.commit()


id_field = _con.PrimaryKeyField('id')

ip_supps_table = _con.SQLTable(
    'ip_supps',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', no_null=True)
)


# def ip_supps(con, cur):
#     cur.execute('CREATE TABLE ip_supps('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL, '
#                 'description TEXT NOT NULL'
#                 ');')
#     con.commit()
