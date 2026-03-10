


def add_seal(con, cur, part_number, description, mfg, series, type, length, o_dia,  # NOQA
             i_dia, color, hardness, lubricant, min_temp, max_temp, wire_dia_min,
             wire_dia_max, weight=0.0, image=None, datasheet=None, cad=None, model3d=None):

    res = cur.execute(f'SELECT id FROM seals WHERE part_number="{part_number}";').fetchall()
    if res:
        return

    mfg_id = _get_mfg_id(con, cur, mfg)
    series_id = _get_series_id(con, cur, series, mfg_id)
    color_id = _get_color_id(con, cur, color)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _add_model3d(con, cur, model3d)
    type_id = _get_seal_type_id(con, cur, type)

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

        if color:
            description += f' {color}'

        if wire_dia_min:
            description += f' {wire_dia_min}mm'

        if wire_dia_max:
            if wire_dia_min:
                description += f' -'

            description += f' {wire_dia_max}mm'

        if type:
            description += f' {type}'

        description += ' Seal'

    print(f'DATABASE: adding seal {part_number}, {description}')
    cur.execute('INSERT INTO seals (part_number, description, mfg_id, series_id, '
                'type_id, color_id, lubricant, min_temp_id, max_temp_id, length, '
                'o_dia, i_dia, hardness, wire_dia_min, wire_dia_max, image_id, '
                'datasheet_id, cad_id, model3d_id, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, type_id, color_id,
                 lubricant, min_temp_id, max_temp_id, length, o_dia, i_dia, hardness,
                 wire_dia_min, wire_dia_max, image_id, datasheet_id, cad_id, model3d_id, weight))

    con.commit()
    db_id = cur.lastrowid

    print(f'DATABASE: seal added "{part_number}" = {db_id}')



def add_seals(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_seal(con, cur, **line)


def _seals(con, cur):
    res = cur.execute('SELECT id FROM seals WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_series(con, cur)
    _add_colors(con, cur)
    _add_temperatures(con, cur)
    _add_seal_types(con, cur)

    splash.SetText(f'Adding core seal to db [1 | 1]...')

    cur.execute('INSERT INTO seals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # os.path.join(DATA_PATH, 'seals.json'),
    json_paths = [os.path.join(DATA_PATH, 'aptiv_seals.json')]

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading seals file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding seals to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding seals to db [{i} | {data_len}]...')
                add_seal(con, cur, **item)

            con.commit()


def seals(con, cur):
    cur.execute('CREATE TABLE seals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 999999 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, ' 
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '     
                'type_id INTEGER DEFAULT 0 NOT NULL, '
                'hardness INTEGER DEFAULT -1 NOT NULL, '
                'lubricant TEXT DEFAULT "" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'o_dia REAL DEFAULT "0.0" NOT NULL, '
                'i_dia REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '   
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '    
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (type_id) REFERENCES seal_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '    
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'                
                ');')
    con.commit()




def seal_crossref(con, cur):
    cur.execute('CREATE TABLE seal_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'seal_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'seal_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (seal_id1) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (seal_id2) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
