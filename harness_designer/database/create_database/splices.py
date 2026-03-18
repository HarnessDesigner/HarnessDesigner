import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import materials as _materials
from . import resources as _resources
from . import platings as _platings
from . import splice_types as _splice_types
from . import temperatures as _temperatures
from . import models3d as _models3d

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import circuits as _circuits

from .. import db_connectors as _con


def add_records(con, splash):
    con.execute('SELECT id FROM splices WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding splice to db [1 | 1]...')
    con.execute('INSERT INTO splices (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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

            for i, item in enumerate(data):
                splash.SetText(f'Adding splices to db [{i + 1} | {data_len}]')
                add_splice(con, **item)

        con.commit()


def add_splices(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_splice(con, **line)

'''
part_number, description, mfg_id, family_id, series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id, material_id, plating_id, type_id, min_dia, max_dia, resistance, length, weight

'''

def add_splice(con, part_number, description, mfg=None, family=None, series=None,
               color=None, image=None, datasheet=None, cad=None, min_temp=None,
               max_temp=None, model3d=None, material=None, plating=None,  type=None,  # NOQA
               min_dia=0.0, max_dia=0.0, resistance=0.0, length=0.0, weight=0.0):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    plating_id = _platings.get_plating_id(con, plating)
    type_id = _splice_types.get_splice_type_id(con, type)
    model3d_id = _models3d.add_model3d(con, model3d)

    con.execute('INSERT INTO splices (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, model3d_id, material_id, plating_id, type_id, min_dia, '
                'max_dia, resistance, length, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, model3d_id,
                 material_id, plating_id, type_id, min_dia, max_dia, resistance,
                 length, weight))
    con.commit()


def add_pjt_splice(con, project_id, part_id, start_point3d_id=None, stop_point3d_id=None,
                   branch_point3d_id=None, point2d_id=None, circuit_id=None, name='',
                   notes='', is_visible2d=0, is_visible3d=0):

    con.execute('INSERT INTO pjt_splices (project_id, part_id, start_point3d_id, '
                'stop_point3d_id, branch_point3d_id, point2d_id, circuit_id, name, '
                'notes, is_visible2d, is_visible3d) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, start_point3d_id, stop_point3d_id, branch_point3d_id,
                 point2d_id, circuit_id, name, notes, is_visible2d, is_visible3d))

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'splices',
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
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('plating_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_platings.table,
                                                    _platings.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('type_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_splice_types.table,
                                                    _splice_types.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('min_dia', default='"0.0"', no_null=True),
    _con.FloatField('max_dia', default='"0.0"', no_null=True),
    _con.FloatField('resistance', default='"0.0"', no_null=True),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_splices',
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

    _con.IntField('start_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('stop_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('branch_point3d_id', no_null=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('circuit_id', no_null=True,
                  references=_con.SQLFieldReference(_circuits.pjt_table,
                                                    _circuits.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_splices(con, cur):
#     cur.execute('CREATE TABLE pjt_splices('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'circuit_id INTEGER DEFAULT NULL, '
#                 'start_point3d_id INTEGER NOT NULL, '  # absolute
#                 'stop_point3d_id INTEGER NOT NULL, '  # absolute
#                 'branch_point3d_id INTEGER NOT NULL, '  # absolute
#                 'point2d_id INTEGER NOT NULL, '
#                 'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES splices(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (start_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (branch_point3d_id) REFERENCES pjt_circuits(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def splices(con, cur):
#     cur.execute('CREATE TABLE splices('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'plating_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'type_id INTEGER DEFAULT 0 NOT NULL, '
#                 'min_dia REAL DEFAULT "0.0" NOT NULL, '
#                 'max_dia REAL DEFAULT "0.0" NOT NULL, '
#                 'resistance REAL DEFAULT "0.0" NOT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (plating_id) REFERENCES platings(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (type_id) REFERENCES splice_types(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#
#     con.commit()
