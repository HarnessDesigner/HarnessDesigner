import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import resources as _resources
from . import model3d as _model3d
from . import directions as _directions
from . import temperatures as _temperatures
from . import cavity_locks as _cavity_locks
from . import genders as _genders
from . import ip_ratings as _ip_ratings
from . import cpa_lock_types as _cpa_lock_types
from . import seal_types as _seal_types

from ... import db_connectors as _con


def add_housing(con, cur, part_number, description, mfg, family, series, num_pins,
                gender, direction, color, sealed, min_temp, max_temp, length,
                width, height, cavity_lock, seal_type, cpa_lock_type, terminal_sizes,
                compat_terminals, mates_to, compat_seals, compat_covers, compat_cpas,
                compat_tpas, weight=0.0, ip_rating='IP00', centerline=0.0, rows=1,
                cad=None, image=None, datasheet=None, model3d=None, terminal_size_counts=[]):

    mfg_id = _manufacturers.get_mfg_id(con, cur, mfg)
    family_id = _families.get_family_id(con, cur, family, mfg_id)
    series_id = _series.get_series_id(con, cur, series, mfg_id)
    direction_id = _directions.get_direction_id(con, cur, direction)
    color_id = _colors.get_color_id(con, cur, color)

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

    min_temp_id = _temperatures.get_temperature_id(con, cur, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, cur, max_temp)

    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cur, cavity_lock)
    gender_id = _genders.get_gender_id(con, cur, gender)
    image_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, cur, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _model3d.add_model3d(con, cur, model3d)
    ip_rating_id = _ip_ratings.get_ip_rating_id(con, cur, ip_rating)
    seal_type_id = _seal_types.get_seal_type_id(con, cur, seal_type)
    cpa_lock_type_id = _cpa_lock_types.get_cpa_lock_type_id(con, cur, cpa_lock_type)

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
                'cad_id, model3d_id, ip_rating_id, terminal_size_counts, seal_type_id, '
                'cpa_lock_type_id) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 min_temp_id, max_temp_id, gender_id, direction_id, length, width,
                 height, weight, cavity_lock_id, sealed, rows, num_pins,
                 str(terminal_sizes), centerline, str(compat_cpas), str(compat_tpas),
                 str(compat_covers), str(compat_terminals), str(compat_seals),
                 str(mates_to), image_id, datasheet_id, cad_id, model3d_id,
                 ip_rating_id, str(terminal_size_counts), seal_type_id, cpa_lock_type_id))

    con.commit()


def add_housings(con, cur, data: tuple[dict] | list[dict]):

    for line in data:
        add_housing(con, cur, **line)


def housings(con, cur, splash):
    res = cur.execute('SELECT id FROM housings WHERE id=0;')

    if res.fetchall():
        return

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


id_field = _con.PrimaryKeyField('id')

housings_table = _con.SQLTable(
    'housings',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.manufacturers_table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_families.families_table,
                                                    _families.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.series_table,
                                                    _series.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_colors.colors_table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('gender_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_genders.genders_table,
                                                    _genders.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('direction_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_directions.directions_table,
                                                    _directions.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datacheet_idmfg_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.resources_table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.temperatures_table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.temperatures_table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cavity_lock_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cavity_locks.cavity_locks_table,
                                                    _cavity_locks.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('ip_rating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_ip_ratings.ip_ratings_table,
                                                    _ip_ratings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('seal_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_seal_types.seal_types_table,
                                                    _seal_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cpa_lock_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cpa_lock_types.cpa_lock_types_table,
                                                    _cpa_lock_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_model3d.models3d_table,
                                                    _model3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('sealing', default='0', no_null=True),
    _con.IntField('rows', default='0', no_null=True),
    _con.IntField('num_pins', default='0', no_null=True),
    _con.TextField('terminal_sizes', default='"[]"', no_null=True),
    _con.TextField('terminal_size_counts', default='"[]"', no_null=True),
    _con.FloatField('centerline', default='"0.0"', no_null=True),
    _con.TextField('compat_cpas', default='"[]"', no_null=True),
    _con.TextField('compat_tpas', default='"[]"', no_null=True),
    _con.TextField('compat_covers', default='"[]"', no_null=True),
    _con.TextField('compat_terminals', default='"[]"', no_null=True),
    _con.TextField('compat_seals', default='"[]"', no_null=True),
    _con.TextField('compat_housings', default='"[]"', no_null=True),
    _con.TextField('compat_boots', default='"[]"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('cover_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('seal_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('boot_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('tpa_lock_1_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('tpa_lock_2_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('cpa_lock_point3d', default='"[0.0, 0.0, 0.0]"', no_null=True)
)


# def housings(con, cur):
#     cur.execute('CREATE TABLE housings('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'gender_id INTEGER DEFAULT 0 NOT NULL, '
#                 'direction_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '
#                 'sealing INTEGER DEFAULT 0 NOT NULL, '
#                 'rows INTEGER DEFAULT 0 NOT NULL, '
#                 'num_pins INTEGER DEFAULT 0 NOT NULL, '
#                 'terminal_sizes TEXT DEFAULT "[]" NOT NULL, '
#                 'terminal_size_counts TEXT DEFAULT "[]" NOT NULL,'
#                 'centerline REAL DEFAULT "0.0" NOT NULL, '
#                 'compat_cpas TEXT DEFAULT "[]" NOT NULL, '
#                 'compat_tpas TEXT DEFAULT "[]" NOT NULL, '
#                 'compat_covers TEXT DEFAULT "[]" NOT NULL, '
#                 'compat_terminals TEXT DEFAULT "[]" NOT NULL, '
#                 'compat_seals TEXT DEFAULT "[]" NOT NULL, '
#                 'compat_housings TEXT DEFAULT "[]" NOT NULL, '
#                 'ip_rating_id INTEGER DEFAULT 0 NOT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'width REAL DEFAULT "0.0" NOT NULL, '
#                 'height REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'seal_type_id INTEGER DEFAULT 0 NOT NULL, '
#                 'cpa_lock_type_id INTEGER DEFAULT 0 NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL, '
#                 'cover_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'seal_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'boot_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'tpa_lock_1_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'tpa_lock_2_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'cpa_lock_point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (ip_rating_id) REFERENCES ip_ratings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cavity_lock_id) REFERENCES terminal_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (direction_id) REFERENCES directions(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (seal_type_id) REFERENCES seal_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cpa_lock_type_id) REFERENCES cpa_lock_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
#
#
# def housing_crossref(con, cur):
#     cur.execute('CREATE TABLE housing_crossref('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number1 TEXT NOT NULL, '
#                 'housing_id1 INTEGER DEFAULT NULL, '
#                 'mfg_id1 INTEGER DEFAULT NULL, '
#                 'part_number2 TEXT NOT NULL, '
#                 'housing_id2 INTEGER DEFAULT NULL, '
#                 'mfg_id2 INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (housing_id1) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (housing_id2) REFERENCES housings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
