from ... import db_connectors as _con


def add_platings(con, cur, splash):
    res = cur.execute('SELECT id FROM platings WHERE id=0;')
    if res.fetchall():
        return

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

    splash.SetText(f'Adding platings to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO platings (id, symbol, description) VALUES(?, ?, ?);', data)
    splash.SetText(f'Adding platings to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_plating_id(con, cur, symbol):
    if not symbol:
        return 0

    res = cur.execute(f'SELECT id FROM platings WHERE symbol="{symbol}";').fetchall()

    if not res:
        print(f'DATABASE: adding plating ("{symbol}")')

        cur.execute('INSERT INTO platings (symbol) VALUES (?);', (symbol,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: plating added "{symbol}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

platings_table = _con.SQLTable(
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
