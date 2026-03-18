
from . import manufacturers as _manufacturers
from . import colors as _colors
from . import resources as _resources
from . import series as _series
from . import families as _families
from . import temperatures as _temperatures


from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import wires as _wires

from .. import db_connectors as _con


def add_wire_markers(con, data: tuple[dict] | list[dict]):

    for line in data:
        add_wire_marker(con, **line)


def add_records(con, splash):
    con.execute('SELECT id FROM wire_markers WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding wire marker to db [1 | 1]...')
    con.execute('INSERT INTO wire_markers (id, part_number, description, mfg_id, '
                'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                'min_temp_id, max_temp_id, min_diameter, max_diameter, min_awg, '
                'max_awg, length, weight, has_label) '
                'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (0, 'N/A', 'Internal Use DO NOT DELETE', 0, 0, 0, 999999, None, None,
                 None, 0, 0, 0.0, 0.0, -1, -1, 0.0, 0.0, 0))
    con.commit()

    splash.SetText(f'Building wire markers...')
    data = _build_wire_markers(con)

    data_len = len(data)
    splash.SetText(f'Adding wire markers to db [{data_len} | {data_len}]')
    for line in data:
        print(line)

    con.executemany('INSERT INTO wire_markers (part_number, description, mfg_id, '
                    'family_id, series_id, color_id, image_id, datasheet_id, cad_id, '
                    'min_temp_id, max_temp_id, min_diameter, max_diameter, min_awg, '
                    'max_awg, length, weight, has_label) '
                    'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    data)

    con.commit()


def add_wire_marker(con, part_number, description, mfg=None, family=None, series=None,
                    color=None, image=None, datasheet=None, cad=None, min_temp=None,
                    max_temp=None, min_diameter=0.0, max_diameter=0.0, min_awg=-1,
                    max_awg=-1, length=0.0, weight=0.0, has_label=0):

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    min_temp_id = _temperatures.get_temperature_id(con, min_temp)
    max_temp_id = _temperatures.get_temperature_id(con, max_temp)
    image_id = _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image)
    datasheet_id = _resources.add_resource(con, _resources.IMAGE_TYPE_DATASHEET, datasheet)
    cad_id = _resources.add_resource(con, _resources.IMAGE_TYPE_CAD, cad)

    con.execute('INSERT INTO wire_markers (part_number, description, mfg_id, family_id, '
                'series_id, color_id, image_id, datasheet_id, cad_id, min_temp_id, '
                'max_temp_id, min_diameter, max_diameter, min_awg, max_awg, length, '
                'weight, has_label) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 image_id, datasheet_id, cad_id, min_temp_id, max_temp_id, min_diameter,
                 max_diameter, min_awg, max_awg, length, weight, has_label))

    con.commit()


def add_pjt_wire_marker(con, project_id, part_id, point3d_id=None, point2d_id=None,
                        wire_id=None, name='', notes='', label='', is_visible2d=1,
                        is_visible3d=1):

    con.execute('INSERT INTO pjt_wire_markers (project_id, part_id, point3d_id, '
                'point2d_id, wire_id, name, notes, label, is_visible2d, is_visible3d) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (project_id, part_id, point3d_id, point2d_id, wire_id, name, notes,
                 label, is_visible2d, is_visible3d))

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'wire_markers',
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
    _con.FloatField('min_diameter', default='"0.0"', no_null=True),
    _con.FloatField('max_diameter', default='"0.0"', no_null=True),
    _con.IntField('min_awg', default='NULL'),
    _con.IntField('max_awg', default='NULL'),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True),
    _con.IntField('has_label', default='0', no_null=True)
)


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_wire_marker',
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
    _con.IntField('point2d_id', no_null=True,
                  references=_con.SQLFieldReference(_points2d.pjt_table,
                                                    _points2d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('wire_id', no_null=True,
                  references=_con.SQLFieldReference(_wires.pjt_table,
                                                    _wires.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.TextField('label', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True)
)

# def pjt_wire_markers(con, cur):
#     cur.execute('CREATE TABLE pjt_wire_markers('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'project_id INTEGER NOT NULL, '
#                 'name TEXT DEFAULT "" NOT NULL, '
#                 'notes TEXT DEFAULT "" NOT NULL, '
#                 'point2d_id INTEGER DEFAULT NULL, '
#                 'point3d_id INTEGER DEFAULT NULL, '  # absolute but must be on a wire
#                 'part_id INTEGER NOT NULL, '
#                 'wire_id INTEGER NOT NULL, '
#                 'label TEXT DEFAULT "" NOT NULL, '
#                 'is_visible2d INTEGER DEFAULT 1 NOT NULL, '
#                 'is_visible3d INTEGER DEFAULT 1 NOT NULL, '
#                 'FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point2d_id) REFERENCES pjt_points2d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (point3d_id) REFERENCES pjt_points3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (part_id) REFERENCES wire_markers(id) ON DELETE CASCADE ON UPDATE CASCADE, '
#                 'FOREIGN KEY (wire_id) REFERENCES pjt_wires(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()

# def wire_markers(con, cur):
#     cur.execute('CREATE TABLE wire_markers('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT 0 NOT NULL, '
#                 'min_diameter REAL DEFAULT "0.0" NOT NULL, '
#                 'max_diameter REAL DEFAULT "0.0" NOT NULL, '
#                 'min_awg INTEGER DEFAULT NULL, '
#                 'max_awg INTEGER DEFAULT NULL, '
#                 'image_id INTEGER DEFAULT NULL, '
#                 'datasheet_id INTEGER DEFAULT NULL, '
#                 'cad_id INTEGER DEFAULT NULL, '
#                 'length REAL DEFAULT "0.0" NOT NULL, '
#                 'weight REAL DEFAULT "0.0" NOT NULL, '
#                 'has_label INTEGER DEFAULT 0 NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (image_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (datasheet_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (cad_id) REFERENCES resources(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()


def _build_wire_markers(con):
    data = {
        'SH RNF-3000-3/1-{color_id}': {
            'min_awg': 18,
            'max_awg': 10,
            'description': 'Shrink Markers ({color}/Standard)',
            'min_diameter': 1.0,
            'max_diameter': 3.0,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20RNF-3000-3%201-{color_id}_thumbnail.jpg'
        },
        'SH RNF-3000-0-{color_id}': {
            'min_awg': 26,
            'max_awg': 18,
            'description': 'Shrink Markers ({color}/Mini)',
            'min_diameter': 0.5,
            'max_diameter': 1.5,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20RNF-3000-{color_id}_thumbnail.jpg'
        }
    }

    color_mapping = {
        0: 'Black',
        1: 'Brown',
        2: 'Red',
        3: 'Orange',
        4: 'Yellow',
        5: 'Green',
        6: 'Blue',
        7: 'Violet',
        8: 'Gray',
        9: 'White'
    }

    mfg_id = _manufacturers.get_mfg_id(con, 'Milspecwiring.com')
    res = []

    for color_id, color_name in color_mapping.items():
        for pn, item_data in data.items():
            part_number = pn.format(color_id=color_id)
            description = item_data['description'].format(color=color_name)
            min_awg = item_data['min_awg']
            max_awg = item_data['max_awg']
            min_diameter = item_data['min_diameter']
            max_diameter = item_data['max_diameter']
            image_url = item_data['image_url'].format(color_id=color_id)
            length = 5.0
            weight = 0.0
            datasheet_id = None
            cad_id = None
            has_label = 0

            family_id = 0
            series_id = 0

            min_temp_id = 0
            max_temp_id = 0

            image_id = None  # _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image_url)
            # image_id = get_resource_id(con, cur, image_url, type='jpg')

            res.append((part_number, description, mfg_id, family_id, series_id,
                        color_id, image_id, datasheet_id, cad_id, min_temp_id,
                        max_temp_id, min_diameter, max_diameter, min_awg, max_awg,
                        length, weight, has_label))

    data = {
        'SH CT 3/32K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/32" Shrink Label',
            'min_diameter': 0.79,
            'max_diameter': 2.36,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/8K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/8" Shrink Label',
            'min_diameter': 1.07,
            'max_diameter': 3.18,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 3/16K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/16" Shrink Label',
            'min_diameter': 1.57,
            'max_diameter': 4.75,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/4K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/4" Shrink Label',
            'min_diameter': 6.35,
            'max_diameter': 2.11,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 3/8K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/8" Shrink Label',
            'min_diameter': 3.18,
            'max_diameter': 9.53,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20quarter%20inch%20fixed_thumbnail.jpg'

        },
        'SH CT 1/2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1/2" Shrink Label',
            'min_diameter': 4.22,
            'max_diameter': 12.7,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20half%20inch_thumbnail.jpg'

        },
        'SH CT 3/4K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 3/4" Shrink Label',
            'min_diameter': 6.35,
            'max_diameter': 19.05,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%20half%20inch_thumbnail.jpg'

        },
        'SH CT 1K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1" Shrink Label',
            'min_diameter': 8.46,
            'max_diameter': 25.4,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        },
        'SH CT 1-1/2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 1-1/2" Shrink Label',
            'min_diameter': 19.05,
            'max_diameter': 38.1,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        },
        'SH CT 2K': {
            'min_awg': None,
            'max_awg': None,
            'description': 'Custom 2" Shrink Label',
            'min_diameter': 25.4,
            'max_diameter': 50.8,
            'image_url': 'https://www.milspecwiring.com/assets/images/thumbnails/SH%20TRAC%201K%20updated_thumbnail.jpg'

        }
    }

    for part_number, item_data in data.items():
        description = item_data['description']
        min_awg = item_data['min_awg']
        max_awg = item_data['max_awg']
        has_label = 1
        min_diameter = item_data['min_diameter']
        max_diameter = item_data['max_diameter']
        image_url = item_data['image_url']
        length = -1.0
        weight = 0.0
        datasheet_id = None
        cad_id = None
        color_id = 1020

        image_id = None  # _resources.add_resource(con, _resources.IMAGE_TYPE_IMAGE, image_url)

        family_id = 0
        series_id = 0

        min_temp_id = 0
        max_temp_id = 0

        res.append((part_number, description, mfg_id, family_id, series_id, color_id, image_id,
                    datasheet_id, cad_id, min_temp_id, max_temp_id, min_diameter, max_diameter,
                    min_awg, max_awg, length, weight, has_label))

    return res
