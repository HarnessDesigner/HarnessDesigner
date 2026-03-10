



def add_terminal(con, cur, part_number, description, mfg, series, cavity_lock,
                 wire_dia_min, wire_dia_max, min_wire_cross, max_wire_cross,
                 gender, blade_size, sealing, plating, image=None, cad=None,
                 datasheet=None, model3d=None, length=0.0, width=0.0, height=0.0,
                 weight=0.0, family=''):

    print('adding terminal:', part_number)
    res = cur.execute(f'SELECT id FROM terminals WHERE part_number="{part_number}";').fetchall()
    if res:
        return

    mfg_id = _get_mfg_id(con, cur, mfg)
    series_id = _get_series_id(con, cur, series, mfg_id)
    family_id = _get_series_id(con, cur, family, mfg_id)
    cavity_lock_id = _get_cavity_lock_id(con, cur, cavity_lock)
    plating_id = _get_plating_id(con, cur, plating)
    gender_id = _get_gender_id(con, cur, gender)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _add_model3d(con, cur, model3d)

    if not width and blade_size:
        width = blade_size

    if not height and blade_size:
        height = blade_size

    print(repr(description))
    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if gender:
            description += f' {gender}'

        if blade_size:
            description += f' {blade_size}mm'

        if plating:
            description += f' {plating}'

        if min_wire_cross:
            description += f' {min_wire_cross}mm²'

        if max_wire_cross:
            if min_wire_cross:
                description += f' -'

            description += f' {max_wire_cross}mm²'

        description += ' Terminal'

    print(f'DATABASE: adding terminal {part_number}, {description}')

    cur.execute('INSERT INTO terminals (part_number, description, mfg_id, series_id, '
                'plating_id, gender_id, sealing, cavity_lock_id, blade_size, wire_dia_min, '
                'wire_dia_max, min_wire_cross, max_wire_cross, image_id, datasheet_id, '
                'cad_id, model3d_id, family_id, length, width, height, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, plating_id, gender_id,
                 sealing, cavity_lock_id, blade_size, wire_dia_min, wire_dia_max,
                 min_wire_cross, max_wire_cross, image_id, datasheet_id, cad_id,
                 model3d_id, family_id, length, width, height, weight))

    con.commit()
    db_id = cur.lastrowid

    print(f'DATABASE: terminal added "{part_number}" = {db_id}')
    print()




def add_terminals(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_terminal(con, cur, **line)


def _terminals(con, cur):
    res = cur.execute('SELECT id FROM terminals WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_series(con, cur)
    _add_families(con, cur)
    _add_colors(con, cur)
    _add_platings(con, cur)
    _add_genders(con, cur)
    _add_cavity_locks(con, cur)

    splash.SetText(f'Adding core terminal to db [1 | 1]...')

    cur.execute('INSERT INTO terminals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # [os.path.join(DATA_PATH, 'terminals.json')

    json_paths = [os.path.join(DATA_PATH, 'aptiv_terminals.json')]

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading terminals file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding terminals to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding terminals to db [{i} | {data_len}]...')
                add_terminal(con, cur, **item)

            con.commit()


def terminals(con, cur):
    cur.execute('CREATE TABLE terminals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'plating_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'gender_id INTEGER DEFAULT 0 NOT NULL, '
                'sealing INTEGER DEFAULT 0 NOT NULL, '
                'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '                
                'blade_size REAL DEFAULT "0.0" NOT NULL, '
                'resistance REAL DEFAULT "0.0" NOT NULL, '
                'mating_cycles INTEGER DEFAULT 0 NOT NULL, '
                'max_vibration_g INTEGER DEFAULT 0 NOT NULL, '
                'max_current_ma INTEGER DEFAULT 0 NOT NULL, '
                'wire_size_min_awg INTEGER DEFAULT 20 NOT NULL, '
                'wire_size_max_awg INTEGER DEFAULT 20 NOT NULL, '
                'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '
                'min_wire_cross REAL DEFAULT "0.0" NOT NULL, '
                'max_wire_cross REAL DEFAULT "0.0" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_lock_id) REFERENCES cavity_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'                               
                ');')
    con.commit()




def terminal_crossref(con, cur):
    cur.execute('CREATE TABLE terminal_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'terminal_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'terminal_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (terminal_id1) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (terminal_id2) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
