import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import transition_series as _transition_series
from . import colors as _colors
from . import materials as _materials
from . import shapes as _shapes
from . import temperatures as _temperatures
from . import protections as _protections
from . import resources as _resources
from . import transition_branches as _transition_branches

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_transition(con, part_number, description, mfg, series, transition_series,
                   family, color, material, shape, max_temp, min_temp, resistances,
                   adhesive, branch_count, branches, cad=None, datasheet=None, image=None):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    transition_series_id = _transition_series.get_transition_series_id(con, transition_series)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    shape_id = _shapes.get_shape_id(con, shape)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)

    if cad is not None:
        cad = cad['path']

    if datasheet is not None:
        datasheet = datasheet['path']

    if image is not None:
        image = image['path']

    protections = '\n'.join(resistances)
    protection_id = _protections.get_protection_id(con, protections)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)

    adhesive_ids = str(adhesive)

    try:
        con.execute('INSERT INTO transitions (part_number, mfg_id, description, '
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

    transition_id = con.lastrowid

    for i, branch in enumerate(branches):
        try:
            _transition_branches.add_transition_branch(con, i, transition_id, **branch)
        except:  # NOQA
            print('BRANCH ERROR:', part_number)
            continue


def add_transitions(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_transition(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM transitions WHERE id=0;')

    if con.fetchall():
        return

    splash.SetText(f'Adding core transition to db [1 | 1]...')

    con.execute('INSERT INTO transitions (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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
            add_transition(con, **item)

        con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'transitions',
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
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('transition_series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_transition_series.table,
                                                    _transition_series.id_field,
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

    _con.IntField('shape_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_shapes.table,
                                                    _shapes.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('protection_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_protections.table,
                                                    _protections.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('branch_count', default='0', no_null=True),
    _con.TextField('adhesive_ids', default='"[]"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_transitions',
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
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)


# def pjt_transitions(con, cur):
#     cur.execute('CREATE TABLE pjt_transitions('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'point3d_id INTEGER NOT NULL, '  # absolute
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES terminals(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def transitions(con, cur):
#     cur.execute('CREATE TABLE transitions('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'transition_series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#
#                 'branch_count INTEGER DEFAULT 0 NOT NULL, '
#                 'shape_id INTEGER DEFAULT 0 NOT NULL, '
#                 'protection_id INTEGER DEFAULT 0 NOT NULL, '
#                 'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (transition_series_id) REFERENCES transition_series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (protection_id) REFERENCES protections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
