from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM temperatures WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building temperatures...')
    data = _build_temps()
    splash.SetText(f'Adding temperatures to db [0 | {len(data)}]...')
    con.executemany('INSERT INTO temperatures (id, name) VALUES (?, ?);', data)
    splash.SetText(f'Adding temperatures to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_temperature_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding temperature ("{name}")')
        con.execute('INSERT INTO temperatures (name) VALUES (?);', (name,))

        con.commit()

        db_id = con.lastrowid
        print(f'DATABASE: temperature added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


def _build_temps():
    data = [(0, 'Unknown',)]

    for i in range(-100, 305, 5):
        if i > 0:
            i = '+' + str(i)
        else:
            i = str(i)

        i += '°C'
        data.append((len(data), i))

    return data


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'temperatures',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)


# def temperatures(con, cur):
#     cur.execute('CREATE TABLE temperatures('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL'
#                 ');')
#     con.commit()
