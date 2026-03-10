

def _add_ip_supps(con, cur):
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


def ip_supps(con, cur):
    cur.execute('CREATE TABLE ip_supps('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'description TEXT NOT NULL'
                ');')
    con.commit()

