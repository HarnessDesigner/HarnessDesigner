


def _add_ip_solids(con, cur):
    res = cur.execute('SELECT id FROM ip_solids WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, '0', 'No Protection', 'No protection against contact and ingress of objects.', None),
        (1, '1', '>= 50.00mm sized objects', 'Any large surface of the body, such as the back of a hand, but no protection against deliberate contact with a body part.', open(f'{BASE_PATH}/image/ip/IP1X.png', 'rb').read()),
        (2, '2', '>= 12.50mm sized objects', 'Fingers or similar objects.', open(f'{BASE_PATH}/image/ip/IP2X.png', 'rb').read()),
        (3, '3', '>= 2.50mm sized objects', 'Tools, thick wires, etc.', open(f'{BASE_PATH}/image/ip/IP3X.png', 'rb').read()),
        (4, '4', '>= 1.00mm sized objects', 'Most wires, slender screws, large ants, etc.', open(f'{BASE_PATH}/image/ip/IP4X.png', 'rb').read()),
        (5, '5', 'Dust Protected', 'Ingress of dust is not entirely prevented.', open(f'{BASE_PATH}/image/ip/IP5X.png', 'rb').read()),
        (6, '6', 'Dust Tight', 'No ingress of dust.', open(f'{BASE_PATH}/image/ip/IP6X.png', 'rb').read()),
        (7, 'X', 'Unknown', 'No data is available to specify a protection rating about this criterion.', None)
    )

    splash.SetText(f'Adding IP solids to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_solids (id, name, short_desc, description, icon_data) VALUES (?, ?, ?, ?, ?);', data)
    splash.SetText(f'Adding IP solids to db [{len(data)} | {len(data)}]...')

    con.commit()


def ip_solids(con, cur):
    cur.execute('CREATE TABLE ip_solids('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'short_desc TEXT NOT NULL, '
                'description TEXT NOT NULL, '
                'icon_data BLOB DEFAULT NULL'
                ');')
    con.commit()

