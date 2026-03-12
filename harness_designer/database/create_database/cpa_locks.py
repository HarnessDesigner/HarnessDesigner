import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import resources as _resources
from . import models3d as _models3d
from . import temperatures as _temperatures

from . import projects as _projects
from . import points3d as _points3d
from . import housings as _housings

from .. import db_connectors as _con


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_cpa_lock(con, part_number, description, mfg, series, family, length,
                 width, height, color, min_temp, max_temp, pins='', weight=0.0,
                 terminal_size=0.0, image=None, datasheet=None, cad=None, model3d=None, lock_type=''):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)

    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _models3d.add_model3d(con, model3d)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

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

    con.execute('INSERT INTO cpa_locks (part_number, description, mfg_id, series_id, '
                'family_id, color_id, terminal_size, min_temp_id, max_temp_id, length, '
                'width, height, pins, image_id, datasheet_id, cad_id, model3d_id, weight, lock_type) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, family_id, color_id,
                 terminal_size, min_temp_id, max_temp_id, length, width, height,
                 pins, image_id, datasheet_id, cad_id, model3d_id, weight, lock_type))

    con.commit()
    db_id = con.lastrowid

    print(f'DATABASE: cpa lock added "{part_number}" = {db_id}')


def add_cpa_locks(con, data: tuple[dict] | list[dict]):
    for line in data:
        add_cpa_lock(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM cpa_locks WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding CPA lock to db [1 | 1]...')
    con.execute('INSERT INTO cpa_locks (id, part_number, description) VALUES(0, "None", "No CPA Lock");')

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

            for i, item in enumerate(data):
                splash.SetText(f'Adding CPA locks to db [{i} | {data_len}]...')
                add_cpa_lock(con, **item)

            con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'cpa_locks',
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
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.IntField('pins', default='0', no_null=True),
    _con.FloatField('terminal_size', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.TextField('lock_type', default='""', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_cpa_locks',
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
    _con.IntField('point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('housing_id', no_null=True,
                  references=_con.SQLFieldReference(_housings.pjt_table,
                                                    _housings.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_cpa_locks(con, cur):
#     cur.execute('CREATE TABLE pjt_cpa_locks('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point
#                 'housing_id INTEGER NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES cpa_locks(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def cpa_locks(con, cur):
#     cur.execute('CREATE TABLE cpa_locks('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'width REAL DEFAULT "0.0" NOT NULL, '
#                 'height REAL DEFAULT "0.0" NOT NULL, '
#                 'pins TEXT DEFAULT "" NOT NULL, '
#                 'terminal_size REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL, '
#                 'type_id INTEGER DEFAULT 0 NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (type_id) REFERENCES cpa_lock_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
#
#
# def cpa_lock_crossref(con, cur):
#     cur.execute('CREATE TABLE cpa_lock_crossref('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number1 TEXT NOT NULL, '
#                 'cpa_lock_id1 INTEGER DEFAULT NULL, '
#                 'mfg_id1 INTEGER DEFAULT NULL, '
#                 'part_number2 TEXT NOT NULL, '
#                 'cpa_lock_id2 INTEGER DEFAULT NULL, '
#                 'mfg_id2 INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (cpa_lock_id1) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cpa_lock_id2) REFERENCES cpa_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
