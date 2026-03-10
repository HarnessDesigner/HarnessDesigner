


def _splices(con, cur):
    res = cur.execute('SELECT id FROM splices WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_families(con, cur)
    _add_series(con, cur)
    _add_materials(con, cur)
    _add_platings(con, cur)
    _add_splice_types(con, cur)
    _add_colors(con, cur)
    _add_temperatures(con, cur)

    splash.SetText(f'Adding core splice to db [1 | 1]...')

    cur.execute('INSERT INTO splices (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # os.path.join(DATA_PATH, 'splices.json')

    json_paths = []

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading splices file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding splices to db [0 | {data_len}]')

            for i, item in enumerate(data):
                splash.SetText(f'Adding splices to db [{i + 1} | {data_len}]')

                add_splice(con, cur, **item)

        con.commit()


def add_splices(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_splice(con, cur, **line)


def add_splice(con, cur, part_number, description, mfg, family, series, material,
               plating, color, image, datasheet, cad, type, min_dia, max_dia,  # NOQA
               resistance, length, weight, model3d):

    mfg_id = _get_mfg_id(con, cur, mfg)
    family_id = _get_family_id(con, cur, family, mfg_id)
    series_id = _get_series_id(con, cur, series, mfg_id)
    color_id = _get_color_id(con, cur, color)
    material_id = _get_material_id(con, cur, material)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    plating_id = _get_plating_id(con, cur, plating)
    type_id = _get_splice_type_id(con, cur, type)
    model3d_id = _add_model3d(con, cur, model3d)

    cur.execute('INSERT INTO bundle_covers (part_number, mfg_id, description, family_id, '
                'series_id, color_id, material_id, image_id, datasheet_id, cad_id, '
                'plating_id, type_id, model3d_id, resistance, length, min_dia, max_dia, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, mfg_id, description, family_id, series_id, color_id,
                 material_id, image_id, datasheet_id, cad_id, plating_id, type_id,
                 model3d_id, resistance, length, min_dia, max_dia, weight))
    con.commit()


def splices(con, cur):
    cur.execute('CREATE TABLE splices('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'plating_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'type_id INTEGER DEFAULT 0 NOT NULL, '
                'min_dia REAL DEFAULT "0.0" NOT NULL, '
                'max_dia REAL DEFAULT "0.0" NOT NULL, '
                'resistance REAL DEFAULT "0.0" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '  
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '   
                'FOREIGN KEY (type_id) REFERENCES splice_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')

    con.commit()
