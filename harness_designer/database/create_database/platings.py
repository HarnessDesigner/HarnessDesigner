from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM platings WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building platings...')

    data = (
        (0, 'Unknown', 'Unknown Plating'),
        (1, 'Sn', 'Tin'),
        (2, 'Cu', 'Copper'),
        (3, 'Al', 'Aluminum'),
        (4, 'Ti', 'Titanium'),
        (5, 'Zn', 'Zinc'),
        (6, 'Au', 'Gold'),
        (7, 'Ag', 'Silver'),
        (8, 'Ni', 'Nickel'),
        (9, 'Ag/Cu', 'Silver-plated Copper'),
        (10, 'Sn/Cu', 'Tin-plated Copper'),
        (11, 'Au/Cu', 'Gold-plated Copper'),
        (12, 'Ni/Cu', 'Nickel-plated Copper'),
        (13, 'Ag/Al', 'Silver-plated Aluminum'),
        (14, 'Sn/Al', 'Tin-plated Aluminum'),
        (15, 'Au/Al', 'Gold-plated Aluminum')
    )

    splash.SetText(f'Adding platings to db [{len(data)} | {len(data)}]...')

    con.executemany('INSERT INTO platings (id, symbol, description) VALUES(?, ?, ?);', data)
    con.commit()


def get_plating_id(con, symbol):
    if not symbol:
        return 0

    con.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding plating ("{symbol}")')

        con.execute('INSERT INTO platings (symbol) VALUES (?);', (symbol,))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: plating added "{symbol}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'platings',
    id_field,
    _con.TextField('symbol', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)


# def platings(con, cur):
#     cur.execute('CREATE TABLE platings('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'symbol TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL'
#                 ');')
#     con.commit()
