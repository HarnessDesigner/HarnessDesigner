


def _add_transition_branch(con, cur, idx, transition_id, **kwargs):
    kwargs['min_dia'] = kwargs.pop('min')
    kwargs['max_dia'] = kwargs.pop('max')

    keys = sorted(list(kwargs.keys()))
    values = []

    for key in keys:
        values.append(kwargs[key])

    keys = ', '.join(keys)

    questions = ['?'] * len(values)
    questions = ', '.join(questions)

    cur.execute(f'INSERT INTO transition_branches (transition_id, idx, {keys}) VALUES (?, ?, {questions});',
                [transition_id, idx] + values)

    con.commit()


def add_transition(con, cur, part_number, description, series, material, shape,
                   max_temp, min_temp, resistances, adhesive, branch_count,
                   branches, cad=None, datasheet=None, image=None):

    mfg_id = 1

    series_id = _get_series_id(con, cur, 'DR-25', mfg_id)
    transition_series_id = _get_transition_series_id(con, cur, series)
    family_id = _get_family_id(con, cur, 'RayChem', mfg_id)
    color_id = _get_color_id(con, cur, 'Black')
    material_id = _get_material_id(con, cur, material)
    shape_id = _get_shape_id(con, cur, shape)
    min_temp_id = _get_temperature_id(con, cur, min_temp)
    max_temp_id = _get_temperature_id(con, cur, max_temp)

    if cad is not None:
        cad = cad['path']

    if datasheet is not None:
        datasheet = datasheet['path']

    if image is not None:
        image = image['path']

    protections = '\n'.join(resistances)
    protection_id = _get_protection_id(con, cur, protections)
    image_id = _add_resource(con, cur, IMAGE_TYPE_IMAGE, image)
    cad_id = _add_resource(con, cur, IMAGE_TYPE_CAD, cad)
    datasheet_id = _add_resource(con, cur, IMAGE_TYPE_DATASHEET, datasheet)

    adhesive_ids = str(adhesive)

    try:
        cur.execute('INSERT INTO transitions (part_number, mfg_id, description, '
                    'family_id, series_id, color_id, material_id, branch_count, '
                    'shape_id, protection_id, adhesive_ids, min_temp_id, max_temp_id, '
                    'transition_series_id, image_id, datasheet_id, cad_id) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    (part_number, mfg_id, description, family_id, series_id, color_id,
                     material_id, branch_count, shape_id, protection_id, adhesive_ids,
                     min_temp_id, max_temp_id, transition_series_id, image_id,
                     datasheet_id, cad_id))
    except:  # NOQA
        print('ERROR:', part_number)
        raise

    con.commit()

    transition_id = cur.lastrowid

    for i, branch in enumerate(branches):
        try:
            _add_transition_branch(con, cur, i, transition_id, **branch)
        except:  # NOQA
            print('BRANCH ERROR:', part_number)
            continue



def add_transitions(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_transition(con, cur, **line)


def _transitions(con, cur):
    res = cur.execute('SELECT id FROM transitions WHERE id=0;')

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
    _add_materials(con, cur)
    _add_transition_series(con, cur)
    _add_shapes(con, cur)

    splash.SetText(f'Adding core transition to db [1 | 1]...')

    cur.execute('INSERT INTO transitions (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
    con.commit()

    json_path = os.path.join(DATA_PATH, 'transitions.json')
    if os.path.exists(json_path):
        splash.SetText(f'Loading trasitions file...')

        with open(json_path, 'r') as f:
            data = json.loads(f.read())

        data_len = len(data)

        splash.SetText(f'Adding transitions to db [0 | {data_len}]...')

        for i, item in enumerate(data):
            splash.SetText(f'Adding transitions to db [{i} | {data_len}]...')
            add_transition(con, cur, **item)

        con.commit()


def transitions(con, cur):
    cur.execute('CREATE TABLE transitions('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT 0 NOT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'transition_series_id INTEGER DEFAULT 0 NOT NULL, '
                'cad_id INTEGER DEFAULT NULL, '
                'datasheet_id INTEGER DEFAULT NULL, '
                'image_id INTEGER DEFAULT NULL, '
                'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
                'branch_count INTEGER DEFAULT 0 NOT NULL, '
                'shape_id INTEGER DEFAULT 0 NOT NULL, '
                'protection_id INTEGER DEFAULT 0 NOT NULL, '
                'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (transition_series_id) REFERENCES transition_series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '                
                'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, ' 
                'FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (protection_id) REFERENCES protections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()
