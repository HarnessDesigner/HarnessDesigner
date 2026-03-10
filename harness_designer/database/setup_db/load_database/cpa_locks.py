

def add_cpa_lock(con, cur, part_number, description, mfg, series, family, length,
                 width, height, color, min_temp, max_temp, pins='', weight=0.0,
                 terminal_size=0.0, image=None, datasheet=None, cad=None, model3d=None, lock_type=''):

    mfg_id = _get_mfg_id(con, cur, mfg)
    series_id = _get_series_id(con, cur, series, mfg_id)
    family_id = _get_family_id(con, cur, family, mfg_id)
    color_id = _get_color_id(con, cur, color)

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

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if color:
            description += f' {color}'

        description += ' CPA Lock'

    print(f'DATABASE: adding cpa lock {part_number}, {description}')

    cur.execute('INSERT INTO cpa_locks (part_number, description, mfg_id, series_id, '
                'family_id, color_id, terminal_size, min_temp_id, max_temp_id, length, '
                'width, height, pins, image_id, datasheet_id, cad_id, model3d_id, weight, lock_type) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, family_id, color_id,
                 terminal_size, min_temp_id, max_temp_id, length, width, height,
                 pins, image_id, datasheet_id, cad_id, model3d_id, weight, lock_type))

    con.commit()
    db_id = cur.lastrowid

    print(f'DATABASE: cpa lock added "{part_number}" = {db_id}')


def add_cpa_locks(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_cpa_lock(con, cur, **line)


def _cpa_locks(con, cur):
    res = cur.execute('SELECT id FROM cpa_locks WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_series(con, cur)
    _add_families(con, cur)
    _add_temperatures(con, cur)
    _add_colors(con, cur)

    splash.SetText(f'Adding core CPA lock to db [1 | 1]...')

    cur.execute('INSERT INTO cpa_locks (id, part_number, description) VALUES(0, "None", "No CPA Lock");')

    # os.path.join(DATA_PATH, 'cpa_locks.json')
    json_paths = [os.path.join(DATA_PATH, 'aptiv_cpa_locks.json')]

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading CPA locks file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding CPA locks to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding CPA locks to db [{i} | {data_len}]...')
                add_cpa_lock(con, cur, **item)

            con.commit()


def cpa_locks(con, cur):
    cur.execute('CREATE TABLE cpa_locks('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'pins TEXT DEFAULT "" NOT NULL, '
                'terminal_size REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'type_id INTEGER DEFAULT 0 NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (type_id) REFERENCES cpa_lock_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()





def cpa_lock_crossref(con, cur):
    cur.execute('CREATE TABLE cpa_lock_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'cpa_lock_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'cpa_lock_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (cpa_lock_id1) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cpa_lock_id2) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
