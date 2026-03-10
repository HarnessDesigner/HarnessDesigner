


def add_bundle_covers(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_bundle_cover(con, cur, **line)


def _bundle_covers(con, cur):
    res = cur.execute('SELECT id FROM bundle_covers WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_families(con, cur)
    _add_series(con, cur)
    _add_materials(con, cur)
    _add_colors(con, cur)
    _add_temperatures(con, cur)
    _add_protections(con, cur)

    splash.SetText(f'Adding core bundle cover to db [1 | 1]...')

    cur.execute('INSERT INTO bundle_covers (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    os.path.join(DATA_PATH, 'bundle_covers.json')
    json_paths = []

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading bundle covers file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding bundle covers to db [0 | {data_len}]')

            for i, item in enumerate(data):
                splash.SetText(f'Adding bundle covers to db [{i + 1} | {data_len}]')
                add_bundle_cover(con, cur, **item)

        con.commit()


def add_bundle_cover(con, cur, part_number, description, mfg, family, series, color,
                     material, image, datasheet, cad, shrink_temp, min_temp, max_temp,
                     rigidity, shrink_ratio, wall, min_dia, max_dia, protection,
                     adhesive, weight):

    mfg_id = _get_mfg_id(con, cur, mfg)
    family_id = _get_family_id(con, cur, family, mfg_id)
    series_id = _get_series_id(con, cur, series, mfg_id)
    color_id = _get_color_id(con, cur, color)
    material_id = _get_material_id(con, cur, material)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    shrink_temp_id = _get_temperature_id(con, cur, shrink_temp)
    min_temp_id = _get_temperature_id(con, cur, min_temp)
    max_temp_id = _get_temperature_id(con, cur, max_temp)
    adhesive_id = _get_adhesive_id(con, cur, adhesive)
    protection_id = _get_protection_id(con, cur, protection)

    cur.execute('INSERT INTO bundle_covers (part_number, mfg_id, description, family_id, '
                'series_id, color_id, material_id, image_id, datasheet_id, '
                'cad_id, shrink_temp_id, min_temp_id, max_temp_id, adhesive_id, '
                'protection_id, rigidity, shrink_ratio, wall, min_dia, max_dia, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, mfg_id, description, family_id, series_id, color_id,
                 material_id, image_id, datasheet_id, cad_id, shrink_temp_id, min_temp_id,
                 max_temp_id, adhesive_id, protection_id, rigidity, shrink_ratio, wall,
                 min_dia, max_dia, weight))
    con.commit()




def bundle_covers(con, cur):
    cur.execute('CREATE TABLE bundle_covers('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'shrink_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'rigidity TEXT DEFAULT "NOT SET" NOT NULL, '
                'shrink_ratio TEXT DEFAULT "" NOT NULL, '
                'wall TEXT DEFAULT "Single" NOT NULL, '
                'min_dia INTEGER DEFAULT 0 NOT NULL, '
                'max_dia INTEGER DEFAULT 0 NOT NULL, '
                'protection_id TEXT DEFAULT 0 NOT NULL, '
                'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (protection_id) REFERENCES potections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (shrink_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
