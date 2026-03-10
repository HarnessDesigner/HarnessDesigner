


def add_boots(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_boot(con, cur, **line)


def add_boot(con, cur, part_number, description, mfg, family, series, color, material,
             direction, image, datasheet, cad, min_temp, max_temp, length, width, height,
             weight, model3d):

    mfg_id = _get_mfg_id(con, cur, mfg)
    family_id = _get_family_id(con, cur, family, mfg_id)
    series_id = _get_series_id(con, cur, series, mfg_id)
    color_id = _get_color_id(con, cur, color)
    material_id = _get_material_id(con, cur, material)
    direction_id = _get_direction_id(con, cur, direction)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    min_temp_id = _get_temperature_id(con, cur, min_temp)
    max_temp_id = _get_temperature_id(con, cur, max_temp)
    model3d_id = _add_model3d(con, cur, model3d)

    cur.execute('INSERT INTO boots (part_number, description, mfg_id, family_id, '
                'series_id, color_id, material_id, min_temp_id, max_temp_id, direction_id, '
                'length, width, height, weight, image_id, datasheet_id, cad_id, model3d_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 material_id, min_temp_id, max_temp_id, direction_id, length, width,
                 height, weight, image_id, datasheet_id, cad_id, model3d_id
                 ))

    con.commit()


def _boots(con, cur):
    res = cur.execute('SELECT id FROM boots WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_series(con, cur)
    _add_families(con, cur)
    _add_colors(con, cur)

    splash.SetText(f'Adding core boot to db [1 | 1]...')

    cur.execute('INSERT INTO boots (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # os.path.join(DATA_PATH, 'boots.json')

    json_paths = []
    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading boots file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding boots to db [0 | {data_len}]...')

            for i, item in enumerate(data):
                splash.SetText(f'Adding boots to db [{i} | {data_len}]...')
                add_boot(con, cur, **item)

            con.commit()



def boots(con, cur):
    cur.execute('CREATE TABLE boots('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'direction_id INETGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()





def boot_crossref(con, cur):
    cur.execute('CREATE TABLE boot_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'boot_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'boot_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (boot_id1) REFERENCES booth(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (boot_id2) REFERENCES boots(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
