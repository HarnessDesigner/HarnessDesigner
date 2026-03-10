
from . import manufacturers as _manufacturers
from . import families as _families
from . import series as _series
from . import colors as _colors
from . import materials as _materials
from . import model3d as _model3d
from . import resources as _resources

from ... import db_connectors as _con


def add_accessories(con, cur, splash):
    res = cur.execute('SELECT id FROM accessories WHERE id=0;')
    if res.fetchall():
        return

    data = (
        (0, 'None', 'No Accessories', 0),
        (1, 'S1017-1.0X50', '1" x 50\' Polyamide Adhesive, -20 – 60 °C [-4 – 140 °F], Hot Melt Tape', 1),
        (2, 'S1030', 'Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (3, 'S1030-TAPE-3/4X33FT', '3/4" x 33\' Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (4, 'S1048-TAPE-1X100-FT', '1" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (5, 'S1048-TAPE-3/4X100-FT', '3/4" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (6, 'S1125-KIT-1', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (7, 'S1125-KIT-4', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (8, 'S1125-KIT-5', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (9, 'S1125-KIT-8', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (10, 'S1125-APPLICATOR', 'Epoxy Adhesives Dispensing Gun', 1)
    )
    splash.SetText(f'Adding accessories to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO accessories (id, part_number, description, mfg_id) VALUES(?, ?, ?, ?);', data)
    splash.SetText(f'Adding accessories to db [{len(data)} | {len(data)}]...')
    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'accessories',
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
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_model3d.table,
                                                    _model3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),


    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)


# def accessories(con, cur):
#     cur.execute('CREATE TABLE accessories('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'part_number TEXT UNIQUE NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'family_id INTEGER DEFAULT 0 NOT NULL, '
#                 'series_id INTEGER DEFAULT 0 NOT NULL, '
#                 'color_id INTEGER DEFAULT NULL, '
#                 'material_id INTEGER DEFAULT 0 NOT NULL, '
#                 'model3d_id INTEGER DEFAULT NULL,'
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (color_id) REFERENCES colors(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (series_id) REFERENCES series(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (model3d_id) REFERENCES models3d(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
