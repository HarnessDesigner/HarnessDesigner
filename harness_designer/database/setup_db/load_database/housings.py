

def add_housing(con, cur, part_number, description, mfg, family, series, num_pins,
                gender, direction, color, sealed, min_temp, max_temp, length,
                width, height, cavity_lock, terminal_sizes, compat_terminals,
                mates_to, compat_seals, compat_covers, compat_cpas, compat_tpas,
                weight=0.0, ip_rating='IP00', centerline=0.0, rows=1, cad=None,
                image=None, datasheet=None, model3d=None, terminal_size_counts=[]):

    mfg_id = _get_mfg_id(con, cur, mfg)
    family_id = _get_family_id(con, cur, family, mfg_id)
    series_id = _get_series_id(con, cur, series, mfg_id)
    direction_id = _get_direction_id(con, cur, direction)
    color_id = _get_color_id(con, cur, color)

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

    cavity_lock_id = _get_cavity_lock_id(con, cur, cavity_lock)
    gender_id = _get_gender_id(con, cur, gender)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _add_model3d(con, cur, model3d)
    ip_rating_id = _get_ip_rating_id(con, cur, ip_rating)

    if not description:
        description = mfg

        if family:
            description += f' {family}'

        if series:
            description += f' {series}'

        if num_pins:
            description += f' {num_pins} cavity'

        if gender:
            description += f' {gender}'

        if terminal_sizes:
            t_sizes = eval(terminal_sizes)
            for t_size in t_sizes:
                description += f' {t_size}mm'

        description += ' Housing'

    cur.execute('INSERT INTO housings (part_number, description, mfg_id, family_id, '
                'series_id, color_id, min_temp_id, max_temp_id, gender_id, direction_id, '
                'length, width, height, weight, cavity_lock_id, sealing, rows, num_pins, '
                'terminal_sizes, centerline, compat_cpas, compat_tpas, compat_covers, '
                'compat_terminals, compat_seals, compat_housings, image_id, datasheet_id, '
                'cad_id, model3d_id, ip_rating_id, terminal_size_counts) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 min_temp_id, max_temp_id, gender_id, direction_id, length, width,
                 height, weight, cavity_lock_id, sealed, rows, num_pins,
                 str(terminal_sizes), centerline, str(compat_cpas), str(compat_tpas),
                 str(compat_covers), str(compat_terminals), str(compat_seals),
                 str(mates_to), image_id, datasheet_id, cad_id, model3d_id,
                 ip_rating_id, str(terminal_size_counts)
                 ))

    con.commit()




def add_housings(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_housing(con, cur, **line)


def _housings(con, cur):
    res = cur.execute('SELECT id FROM housings WHERE id=0;')

    if res.fetchall():
        return

    _add_manufacturers(con, cur)
    _add_file_types(con, cur)
    _add_families(con, cur)
    _add_series(con, cur)
    _add_colors(con, cur)
    _add_temperatures(con, cur)
    _add_genders(con, cur)
    _add_directions(con, cur)
    _add_cavity_locks(con, cur)
    _add_ip_ratings(con, cur)
    _add_cpa_lock_types(con, cur)

    splash.SetText(f'Adding core housing to db [1 | 1]...')

    cur.execute('INSERT INTO housings (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    # os.path.join(DATA_PATH, 'housings.json'),
    json_paths = [os.path.join(DATA_PATH, 'aptiv_housings.json')]

    for json_path in json_paths:
        if os.path.exists(json_path):
            splash.SetText(f'Loading housings file...')
            print(json_path)

            with open(json_path, 'r') as f:
                data = json.loads(f.read())

            if isinstance(data, dict):
                data = [value for value in data.values()]

            data_len = len(data)

            splash.SetText(f'Adding housings to db [0 | {data_len}]')
            for i, item in enumerate(data):
                splash.SetText(f'Adding housings to db [{i + 1} | {data_len}]')
                add_housing(con, cur, **item)

            con.commit()


def housings(con, cur):
    cur.execute('CREATE TABLE housings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '                    
                'gender_id INTEGER DEFAULT 0 NOT NULL, '
                'direction_id INTEGER DEFAULT 0 NOT NULL, '    
                'image_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '                   
                'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '
                'sealing INTEGER DEFAULT 0 NOT NULL, '
                'rows INTEGER DEFAULT 0 NOT NULL, '    
                'num_pins INTEGER DEFAULT 0 NOT NULL, '
                'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
                'terminal_size_counts TEXT DEFAULT "[]" NOT NULL,'
                'centerline REAL DEFAULT "0.0" NOT NULL, '
                'compat_cpas TEXT DEFAULT "[]" NOT NULL, '    
                'compat_tpas TEXT DEFAULT "[]" NOT NULL, '    
                'compat_covers TEXT DEFAULT "[]" NOT NULL, '    
                'compat_terminals TEXT DEFAULT "[]" NOT NULL, '    
                'compat_seals TEXT DEFAULT "[]" NOT NULL, '
                'compat_housings TEXT DEFAULT "[]" NOT NULL, '
                'ip_rating_id INTEGER DEFAULT 0 NOT NULL, '                
                'length REAL DEFAULT "0.0" NOT NULL, '
                'width REAL DEFAULT "0.0" NOT NULL, '
                'height REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'seal_type_id INTEGER DEFAULT 0 NOT NULL, '
                'cpa_lock_type_id INTEGER DEFAULT 0 NOT NULL, '
                'footprint_id INTEGER DEFAULT 0 NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '
                'cover_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'seal_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'boot_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'tpa_lock_1_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'tpa_lock_2_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, ' 
                'cpa_lock_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, ' 
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (ip_rating_id) REFERENCES ip_ratings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (cavity_lock_id) REFERENCES terminal_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (seal_type_id) REFERENCES seal_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cpa_lock_type_id) REFERENCES cpa_lock_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'  
                ');')
    con.commit()





def housing_crossref(con, cur):
    cur.execute('CREATE TABLE housing_crossref('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number1 TEXT NOT NULL, '
                'housing_id1 INTEGER DEFAULT NULL, '
                'mfg_id1 INTEGER DEFAULT NULL, '
                'part_number2 TEXT NOT NULL, '
                'housing_id2 INTEGER DEFAULT NULL, '
                'mfg_id2 INTEGER DEFAULT NULL, '
                'FOREIGN KEY (housing_id1) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (housing_id2) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
