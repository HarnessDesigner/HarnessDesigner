
def add_covers(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_cover(con, cur, **line)


def _covers(con, cur):
    res = cur.execute('SELECT id FROM covers WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_series(con, cur)
    _add_families(con, cur)
    _add_temperatures(con, cur)
    _add_colors(con, cur)
    _add_directions(con, cur)

    splash.SetText(f'Adding core cover to db [1 | 1]...')

    cur.execute('INSERT INTO covers (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # os.path.join(DATA_PATH, 'covers.json'),
    json_paths = [os.path.join(DATA_PATH, 'aptiv_covers.json')]

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading covers file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding covers to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding covers to db [{i} | {data_len}]...')
                add_cover(con, cur, **item)

            con.commit()



def add_cover(con, cur, part_number, description, mfg, series, length, width,
              height, color, min_temp, max_temp, direction=None, pins='', weight=0.0,
              family='', image=None, datasheet=None, cad=None, model3d=None):

    mfg_id = _get_mfg_id(con, cur, mfg)
    series_id = _get_series_id(con, cur, series, mfg_id)
    color_id = _get_color_id(con, cur, color)
    direction_id = _get_direction_id(con, cur, direction)

    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _add_model3d(con, cur, model3d)

    if min_temp is None:
        min_temp = 0

    if max_temp is None:
        max_temp = 0

    if min_temp > 0:
        min_temp = '+' + str(min_temp) + '°C'
    else:
        min_temp = str(min_temp) + '°C'

    if max_temp > 0:
        max_temp = '+' + str(max_temp) + '°C'
    else:
        max_temp = str(max_temp) + '°C'

    min_temp_id = _get_temperature_id(con, cur, min_temp)
    max_temp_id = _get_temperature_id(con, cur, max_temp)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if family:
            description += f' {family}'

        if color:
            description += f' {color}'

        if direction:
            description += f' {direction}'

        description += ' Cover'

    print(f'DATABASE: adding cover {part_number}: {description}')

    cur.execute('INSERT INTO covers (part_number, description, mfg_id, series_id, '
                'color_id, direction_id, min_temp_id, max_temp_id, length, width, '
                'height, pins, image_id, datasheet_id, cad_id, model3d_id, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, color_id,
                 direction_id, min_temp_id, max_temp_id, length, width, height,
                 pins, image_id, datasheet_id, cad_id, model3d_id, weight))

    con.commit()
    db_id = cur.lastrowid

    print(f'DATABASE: cover added "{part_number}" = {db_id}')



def covers(con, cur):
    cur.execute('CREATE TABLE covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '       
                'direction_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'pins TEXT DEFAULT "" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()




def cover_crossref(con, cur):
    cur.execute('CREATE TABLE cover_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'cover_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'cover_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (cover_id1) REFERENCES covers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cover_id2) REFERENCES covers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
