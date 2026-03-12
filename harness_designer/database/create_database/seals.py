import os
import json

from . import temperatures as _temperatures
from . import manufacturers as _manufacturers
from . import series as _series
from . import colors as _colors
from . import resources as _resources
from . import models3d as _models3d
from . import seal_types as _seal_types

from . import projects as _projects
from . import points3d as _points3d
from . import housings as _housings
from . import cavities as _cavities
from . import terminals as _terminals

from harness_designer.database import db_connectors as _con


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_seal(con, part_number, description, mfg, series, type, length, o_dia,  # NOQA
             i_dia, color, hardness, lubricant, min_temp, max_temp, wire_dia_min,
             wire_dia_max, weight=0.0, image=None, datasheet=None, cad=None, model3d=None):

    con.execute(f'SELECT id FROM seals WHERE part_number="{part_number}";')
    if con.fetchall():
        return

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    color_id = _colors.get_color_id(con, color)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    model3d_id = _models3d.add_model3d(con, model3d)
    type_id = _seal_types.get_seal_type_id(con, type)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

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
    con.execute('INSERT INTO seals (part_number, description, mfg_id, series_id, '
                'type_id, color_id, lubricant, min_temp_id, max_temp_id, length, '
                'o_dia, i_dia, hardness, wire_dia_min, wire_dia_max, image_id, '
                'datasheet_id, cad_id, model3d_id, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, series_id, type_id, color_id,
                 lubricant, min_temp_id, max_temp_id, length, o_dia, i_dia, hardness,
                 wire_dia_min, wire_dia_max, image_id, datasheet_id, cad_id, model3d_id, weight))

    con.commit()
    db_id = con.lastrowid

    print(f'DATABASE: seal added "{part_number}" = {db_id}')


def add_seals(con, data: tuple[dict] | list[dict]):
    for line in data:
        add_seal(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM seals WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding seal to db [1 | 1]...')

    con.execute('INSERT INTO seals (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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

            for i, item in enumerate(data):
                splash.SetText(f'Adding seals to db [{i} | {data_len}]...')
                add_seal(con, **item)

            con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'seals',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
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
    _con.IntField('type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_seal_types.table,
                                                    _seal_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('hardness', default='-1', no_null=True),
    _con.TextField('lubricant', default='""', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('o_dia', default='"0.0"', no_null=True),
    _con.FloatField('i_dia', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_min', default='"0.0"', no_null=True),
    _con.FloatField('wire_dia_max', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_seals',
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
    _con.IntField('terminal_id', no_null=True,
                  references=_con.SQLFieldReference(_terminals.pjt_table,
                                                    _terminals.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_seals(con, cur):
#     cur.execute('CREATE TABLE pjt_seals('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # absolute, calculated using housing relative point or terminal relative point
#                 'housing_id INTEGER DEFAULT NULL, '
#                 'terminal_id INTEGER DEFAULT NULL, '
#                 'cavity_id INTEGER DEFAULT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES seals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (housing_id) REFERENCES pjt_housings(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cavity_id) REFERENCES pjt_cavities(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (terminal_id) REFERENCES pjt_terminals(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def seals(con, cur):
#     cur.execute('CREATE TABLE seals('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 999999 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'type_id INTEGER DEFAULT 0 NOT NULL, '
#                 'hardness INTEGER DEFAULT -1 NOT NULL, '
#                 'lubricant TEXT DEFAULT "" NOT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'o_dia REAL DEFAULT "0.0" NOT NULL, '
#                 'i_dia REAL DEFAULT "0.0" NOT NULL, '
#                 'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
#                 'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (type_id) REFERENCES seal_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
#
#
# def seal_crossref(con, cur):
#     cur.execute('CREATE TABLE seal_crossref('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number1 TEXT NOT NULL, '
#                 'seal_id1 INTEGER DEFAULT NULL, '
#                 'mfg_id1 INTEGER DEFAULT NULL, '
#                 'part_number2 TEXT NOT NULL, '
#                 'seal_id2 INTEGER DEFAULT NULL, '
#                 'mfg_id2 INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (seal_id1) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id1) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (seal_id2) REFERENCES seals(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (mfg_id2) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
