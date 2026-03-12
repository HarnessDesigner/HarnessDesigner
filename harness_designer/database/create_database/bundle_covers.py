import os
import json

from . import manufacturers as _manufacturers
from . import series as _series
from . import families as _families
from . import colors as _colors
from . import materials as _materials
from . import resources as _resources
from . import adhesives as _adhesives
from . import protections as _protections
from . import temperatures as _temperatures

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')


def add_bundle_covers(con, data: tuple[dict] | list[dict]):
    for line in data:
        add_bundle_cover(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM bundle_covers WHERE id=0;')

    if con.fetchall():
        return

    splash.SetText(f'Adding bundle cover to db [1 | 1]...')
    con.execute('INSERT INTO bundle_covers (id, part_number, description) VALUES(0, "N/A", "Internal Use DO NOT DELETE");')
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

            for i, item in enumerate(data):
                splash.SetText(f'Adding bundle covers to db [{i + 1} | {data_len}]')
                add_bundle_cover(con, **item)

        con.commit()


def add_bundle_cover(con, part_number, description, mfg, family, series, color,
                     material, image, datasheet, cad, shrink_temp, min_temp, max_temp,
                     rigidity, shrink_ratio, wall, min_dia, max_dia, protection,
                     adhesive, weight):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    family_id = _families.get_family_id(con, family, mfg_id)
    series_id = _series.get_series_id(con, series, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)
    shrink_temp_id = _temperatures.get_temperature_id(con, shrink_temp)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    adhesive_id = _adhesives.get_adhesive_id(con, adhesive)
    protection_id = _protections.get_protection_id(con, protection)

    con.execute('INSERT INTO bundle_covers (part_number, mfg_id, description, family_id, '
                'series_id, color_id, material_id, image_id, datasheet_id, '
                'cad_id, shrink_temp_id, min_temp_id, max_temp_id, adhesive_id, '
                'protection_id, rigidity, shrink_ratio, wall, min_dia, max_dia, weight) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, mfg_id, description, family_id, series_id, color_id,
                 material_id, image_id, datasheet_id, cad_id, shrink_temp_id, min_temp_id,
                 max_temp_id, adhesive_id, protection_id, rigidity, shrink_ratio, wall,
                 min_dia, max_dia, weight))
    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'bundle_covers',
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
    _con.IntField('shrink_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),

    _con.IntField('min_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('max_temp_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_temperatures.table,
                                                    _temperatures.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('protection_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_protections.table,
                                                    _protections.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('rigidity', default='""', no_null=True),
    _con.IntField('shrink_ratio', default='""', no_null=True),
    _con.IntField('wall', default='""', no_null=True),
    _con.FloatField('min_dia', default='"0.0"', no_null=True),
    _con.FloatField('max_dia', default='"0.0"', no_null=True),
    _con.IntField('adhesive_ids', default='"[]"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_bundles',
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
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)


# def pjt_bundles(con, cur):
#     cur.execute('CREATE TABLE pjt_bundles('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'part_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'start_point3d_id INTEGER NOT NULL, '  # absolute, can be shared with a bundle layout or transition
#                 'stop_point3d_id INTEGER NOT NULL, '  # absolute, can be shared with a bundle layout or transition
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES bundle_covers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (start_point3d_id) REFERENCES pjt_points3d(id), '
#                 'FOREIGN KEY (stop_point3d_id) REFERENCES pjt_points3d(id)'
#                 ');')
#     con.commit()

# def bundle_covers(con, cur):
#     cur.execute('CREATE TABLE bundle_covers('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'shrink_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'min_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'max_temp_id INTEGER DEFAULT 0 NOT NULL, '
#                 'rigidity TEXT DEFAULT "NOT SET" NOT NULL, '
#                 'shrink_ratio TEXT DEFAULT "" NOT NULL, '
#                 'wall TEXT DEFAULT "Single" NOT NULL, '
#                 'min_dia INTEGER DEFAULT 0 NOT NULL, '
#                 'max_dia INTEGER DEFAULT 0 NOT NULL, '
#                 'protection_id TEXT DEFAULT 0 NOT NULL, '
#                 'adhesive_ids TEXT DEFAULT "[]" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (min_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (max_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (protection_id) REFERENCES potections(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (shrink_temp_id) REFERENCES temperatures(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
