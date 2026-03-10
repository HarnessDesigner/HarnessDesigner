from ... import db_connectors as _con


def _add_adhesives(con, cur, splash):
    res = cur.execute('SELECT id FROM adhesives WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'None', 'No Adhesive', '[]'),
        (1, '225', 'Precoated latent-curing epoxy/polyamide', '[]'),
        (2, '42', 'Hot-melt/polyamide (Thermoplastic)', '[]'),
        (3, '86', 'Hot-melt,high performance (Thermoplastic)', '[]'),
        (4, 'S1006', 'Epoxy/polyamide two-part paste (Thermoset)', '[]'),
        (5, 'S1017', 'Hot-melt/polyamide (Thermoplastic)', '["S1017-1.0X50"]'),
        (6, 'S1030', 'Hot-melt/polyolefin (Thermoplastic)', '["S1030", "S1030-TAPE-3/4X33FT"]'),
        (7, 'S1048', 'Hot-melt,high performance (Thermoplastic)', '["S1048-TAPE-1X100-FT", "S1048-TAPE-3/4X100-FT"]'),
        (8, 'S1125', 'Epoxy/polyamide two-part paste (Thermoset)', '["S1125-KIT-1", "S1125-KIT-4", "S1125-KIT-5", "S1125-KIT-8","S1125-APPLICATOR"]')
    )

    splash.SetText(f'Adding adhesives to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO adhesives (id, code, description, accessory_part_nums) VALUES (?, ?, ?, ?);', data)
    splash.SetText(f'Adding adhesives to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_adhesive_id(con, cur, code):
    if not code:
        return 0

    res = cur.execute(f'SELECT id FROM adhesives WHERE code="{code}";').fetchall()

    if not res:
        print(f'DATABASE: adding adhesive ("{code}")')

        cur.execute('INSERT INTO adhesives (code) VALUES (?);', (code,))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: adhesive added "{code}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

ashesives_table = _con.SQLTable(
    'ashesives',
    id_field,
    _con.TextField('code', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.TextField('accessory_part_nums', default='"[]"', no_null=True)
)


def adhesives(con, cur):
    cur.execute('CREATE TABLE adhesives('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'code TEXT DEFAULT "" NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'accessory_part_nums TEXT DEFAULT "[]" NOT NULL'
                ');')
    con.commit()
