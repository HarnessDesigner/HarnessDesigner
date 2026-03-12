import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import resources as _resources
from . import models3d as _models3d
from . import directions as _directions
from . import temperatures as _temperatures
from . import cavity_locks as _cavity_locks
from . import genders as _genders
from . import ip_ratings as _ip_ratings
from . import cpa_lock_types as _cpa_lock_types
from . import seal_types as _seal_types

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d

from .. import db_connectors as _con


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_housing(con, part_number, description, mfg, family, series, num_pins,
                gender, direction, color, sealed, min_temp, max_temp, length,
                width, height, cavity_lock, seal_type, cpa_lock_type, terminal_sizes,
                compat_terminals, mates_to, compat_seals, compat_covers, compat_cpas,
                compat_tpas, weight=0.0, ip_rating='IP00', centerline=0.0, rows=1,
                cad=None, image=None, datasheet=None, model3d=None, terminal_size_counts=[]):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    direction_id = _directions.get_direction_id(con, direction)
    color_id = _colors.get_color_id(con, color)

    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cavity_lock)
    gender_id = _genders.get_gender_id(con, gender)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _models3d.add_model3d(con, model3d)
    ip_rating_id = _ip_ratings.get_ip_rating_id(con, ip_rating)
    seal_type_id = _seal_types.get_seal_type_id(con, seal_type)
    cpa_lock_type_id = _cpa_lock_types.get_cpa_lock_type_id(con, cpa_lock_type)

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

    con.execute('INSERT INTO housings (part_number, description, mfg_id, family_id, '
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


def add_housings(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_housing(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM housings WHERE id=0;')

    if con.fetchall():
        return

    splash.SetText(f'Adding core housing to db [1 | 1]...')

    con.execute('INSERT INTO housings (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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
                add_housing(con, **item)

            con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'housings',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_families.table,
                                                    _families.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.table,
                                                    _series.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('gender_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_genders.table,
                                                    _genders.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('direction_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_directions.table,
                                                    _directions.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datasheet_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_resources.table,
                                                    _resources.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cavity_lock_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cavity_locks.table,
                                                    _cavity_locks.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('ip_rating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_ip_ratings.table,
                                                    _ip_ratings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('seal_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_seal_types.table,
                                                    _seal_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cpa_lock_type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cpa_lock_types.table,
                                                    _cpa_lock_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
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


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_housings',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('part_id', no_null=True,
                  references=_con.SQLFieldReference(table,
                                                    id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('cover_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('seal_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('boot_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('tpa_lock_1_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('tpa_lock_2_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cpa_lock_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),


    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_housings(con, cur):
#     cur.execute('CREATE TABLE pjt_housings('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'cover_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for cover to snap onto
#                 'seal_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for seal to snap onto
#                 'boot_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for boot to snap onto
#                 'tpa_lock_1_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for the first tpa lock to snap onto
#                 'tpa_lock_2_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for a second tpa lock to snap onto
#                 'cpa_lock_point3d_id INTEGER DEFAULT NULL, '  # relative to housing, for cpa lock to snap onto
#                 'point3d_id INTEGER DEFAULT NULL, '  # absolute
#                 'point2d_id INTEGER DEFAULT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cover_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (seal_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (boot_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (tpa_lock_1_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (tpa_lock_2_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cpa_lock_point3d_id) REFERENCES pjt_points3d(id)  ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

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
