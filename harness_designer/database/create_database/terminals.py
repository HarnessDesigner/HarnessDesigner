import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import resources as _resources
from . import genders as _genders
from . import platings as _platings
from . import cavity_locks as _cavity_locks
from . import models3d as _models3d

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import circuits as _circuits
from . import cavities as _cavities

from .. import db_connectors as _con


def add_terminal(con, part_number, description, mfg, series, cavity_lock,
                 wire_dia_min, wire_dia_max, min_wire_cross, max_wire_cross,
                 gender, blade_size, sealing, plating, image=None, cad=None,
                 datasheet=None, model3d=None, length=0.0, width=0.0, height=0.0,
                 weight=0.0, family=''):

    print('adding terminal:', part_number)
    res = con.execute(f'SELECT id FROM terminals WHERE part_number="{part_number}";').fetchall()
    if res:
        return

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    cavity_lock_id = _cavity_locks.get_cavity_lock_id(con, cavity_lock)
    plating_id = _platings.get_plating_id(con, plating)
    gender_id = _genders.get_gender_id(con, gender)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _models3d.add_model3d(con, model3d)

    if not width and blade_size:
        width = blade_size

    if not height and blade_size:
        height = blade_size

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

    con.execute('INSERT INTO terminals (part_number, description, mfg_id, series_id, '
                'plating_id, gender_id, sealing, cavity_lock_id, blade_size, wire_dia_min, '
                'wire_dia_max, min_wire_cross, max_wire_cross, image_id, datasheet_id, '
                'cad_id, model3d_id, family_id, length, width, height, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, plating_id, gender_id,
                 sealing, cavity_lock_id, blade_size, wire_dia_min, wire_dia_max,
                 min_wire_cross, max_wire_cross, image_id, datasheet_id, cad_id,
                 model3d_id, family_id, length, width, height, weight))

    con.commit()
    db_id = con.lastrowid

    print(f'DATABASE: terminal added "{part_number}" = {db_id}')
    print()


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_terminals(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_terminal(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM terminals WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding core terminal to db [1 | 1]...')

    con.execute('INSERT INTO terminals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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
                add_terminal(con, **item)

            con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'terminals',
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
    _con.IntField('plating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
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
    _con.IntField('gender_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_genders.table,
                                                    _genders.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cavity_lock_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_cavity_locks.table,
                                                    _cavity_locks.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('sealing', default='0', no_null=True),
    _con.FloatField('blade_size', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.IntField('mating_cycles', default='0', no_null=True),
    _con.IntField('max_vibration_g', default='0', no_null=True),
    _con.IntField('max_current_ma', default='0', no_null=True),
    _con.IntField('wire_size_min_awg', default='-1', no_null=True),
    _con.IntField('wire_size_max_awg', default='-1', no_null=True),
    _con.FloatField('wire_dia_min', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_max', default='"0.0"', no_null=True),
    _con.FloatField('min_wire_cross', default='"0.0"', no_null=True),
    _con.FloatField('max_wire_cross', default='"0.0"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_terminals',
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
    _con.IntField('cavity_id', no_null=True,
                  references=_con.SQLFieldReference(_cavities.pjt_table,
                                                    _cavities.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', no_null=True,
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('wire_point3d_id', no_null=True,
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
    _con.IntField('wire_point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_start', default='1', no_null=True),
    _con.FloatField('volts', default='"0.0"', no_null=True),
    _con.FloatField('load', default='"0.0"', no_null=True),
    _con.FloatField('voltage_drop', default='"0.0"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True)

)


def pjt_terminals(con, cur):
    cur.execute('CREATE TABLE pjt_terminals('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'project_id INTEGER NOT NULL, '
                'part_id INTEGER NOT NULL, '
                'name TEXT DEFAULT "" NOT NULL, '
                'notes TEXT DEFAULT "" NOT NULL, '
                'cavity_id INTEGER NOT NULL, '
                'circuit_id INTEGER DEFAULT NULL, '
                'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point3d_id INTEGER NOT NULL, '  # will snap to a cavity point
                'wire_point3d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'quat2d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
                'angle2d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
                'point2d_id INTEGER NOT NULL, '
                'wire_point2d_id INTEGER NOT NULL, '  # calculated point for where a wire or seal will snap onto
                'is_start INTEGER DEFAULT 0 NOT NULL, '
                'volts REAL DEFAULT "0.0" NOT NULL, '
                'load REAL DEFAULT "0.0" NOT NULL, '
                'voltage_drop REAL DEFAULT "0.0" NOT NULL, '
                'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
                'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
                'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (part_id) REFERENCES terminals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (cavity_id) REFERENCES pjt_cavities(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (circuit_id) REFERENCES pjt_circuits(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
                'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (wire_point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
                'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
                ');')
    con.commit()


# def terminals(con, cur):
#     cur.execute('CREATE TABLE terminals('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'plating_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'gender_id INTEGER DEFAULT 0 NOT NULL, '
#                 'sealing INTEGER DEFAULT 0 NOT NULL, '
#                 'cavity_lock_id INTEGER DEFAULT 0 NOT NULL, '
#                 'blade_size REAL DEFAULT "0.0" NOT NULL, '
#                 'resistance REAL DEFAULT "0.0" NOT NULL, '
#                 'mating_cycles INTEGER DEFAULT 0 NOT NULL, '
#                 'max_vibration_g INTEGER DEFAULT 0 NOT NULL, '
#                 'max_current_ma INTEGER DEFAULT 0 NOT NULL, '
#                 'wire_size_min_awg INTEGER DEFAULT 20 NOT NULL, '
#                 'wire_size_max_awg INTEGER DEFAULT 20 NOT NULL, '
#                 'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
#                 'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '
#                 'min_wire_cross REAL DEFAULT "0.0" NOT NULL, '
#                 'max_wire_cross REAL DEFAULT "0.0" NOT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'width REAL DEFAULT "0.0" NOT NULL, '
#                 'height REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (gender_id) REFERENCES genders(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cavity_lock_id) REFERENCES cavity_locks(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
#
#
# def terminal_crossref(con, cur):
#     cur.execute('CREATE TABLE terminal_crossref('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number1 TEXT NOT NULL, '
#                 'terminal_id1 INTEGER DEFAULT NULL, '
#                 'mfg_id1 INTEGER DEFAULT NULL, '
#                 'part_number2 TEXT NOT NULL, '
#                 'terminal_id2 INTEGER DEFAULT NULL, '
#                 'mfg_id2 INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (terminal_id1) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (terminal_id2) REFERENCES terminals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
