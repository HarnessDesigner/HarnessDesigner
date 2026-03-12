from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM manufacturers WHERE id=0;')
    if con.fetchall():
        return

    data = (
        (0, 'Internal Use DO NOT DELETE', '', '', '', ''),
        (1, 'TE', '1-800-522-6752', '', '', 'https://www.te.com/en/home.html'),
        (2, 'Bosch', '+49 304 036 94077',
         'Robert-Bosch-Platz 1\n70839 Gerlingen-Schillerhöhe\nGERMANY\n',
         'Connectors-Webshop-Hotline.PSCTS1-CO@de.bosch.com',
         'https://bosch-connectors.com/bcp/b2bshop-psconnectors/en/EUR'),
        (3, 'Aptiv', '', '', '', 'https://www.aptiv.com/en/contact'),
        (4, 'Molex', '+800-786-6539', '2222 Wellington Ct\nLisle, IL 60532, USA', '',
         'https://www.molex.com/en-us/products/connectors'),
        (5, 'EPC', '', '', '', ''),
        (6, 'Yazaki', '', '', '', ''),
        (7, 'Milspecwiring.com', '', '', '', 'https://www.milspecwiring.com'),

    )
    splash.SetText(f'Adding manufacturers to db [0 | {len(data)}]...')
    con.executemany('INSERT INTO manufacturers (id, name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?, ?);', data)
    splash.SetText(f'Adding manufacturers to db [{len(data)} | {len(data)}]...')
    con.commit()


def get_mfg_id(con, name):
    if not name:
        return 0

    con.execute(f'SELECT id FROM manufacturers WHERE name="{name}";')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding manufacturer ("{name}", "", "", "", "")')
        con.execute('INSERT INTO manufacturers (name, phone, address, email, website) '
                    'VALUES (?, ?, ?, ?, ?);', (name, '', '', '', ''))

        con.commit()
        db_id = con.lastrowid
        print(f'DATABASE: manufacturer added "{name}" = {db_id}')

        return db_id

    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'manufacturers',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.TextField('address', default='""', no_null=True),
    _con.TextField('contact_person', default='""', no_null=True),
    _con.TextField('phone', default='""', no_null=True),
    _con.TextField('ext', default='""', no_null=True),
    _con.TextField('email', default='""', no_null=True),
    _con.TextField('website', default='""', no_null=True)
)


# def manufacturers(con, cur):
#     cur.execute('CREATE TABLE manufacturers('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'address TEXT DEFAULT "" NOT NULL, '
#                 'contact_person TEXT DEFAULT "" NOT NULL, '
#                 'phone TEXT DEFAULT "" NOT NULL, '
#                 'ext TEXT DEFAULT "" NOT NULL, '
#                 'email TEXT DEFAULT "" NOT NULL, '
#                 'website TEXT DEFAULT "" NOT NULL'
#                 ');')
#     con.commit()
