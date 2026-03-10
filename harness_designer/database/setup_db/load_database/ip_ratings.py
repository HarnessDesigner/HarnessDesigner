from ... import db_connectors as _con

from . import ip_supps as _ip_supps
from . import ip_fluids as _ip_fluids
from . import ip_solids as _ip_solids


def add_ip_ratings(con, cur, splash):
    res = cur.execute('SELECT id FROM ip_ratings WHERE id=0;')
    if res.fetchall():
        return

    data = (('IPOO', 0, 0), ('IPXX', 7, 12), ('IP01', 0, 1), ('IP02', 0, 2),
            ('IP03', 0, 3),
            ('IP04', 0, 4), ('IP05', 0, 5), ('IP06', 0, 6), ('IP07', 0, 7),
            ('IP08', 0, 8), ('IP09', 0, 9), ('IP06K', 0, 10), ('IP09K', 0, 11),
            ('IP0X', 0, 12), ('IP10', 1, 0), ('IP11', 1, 1), ('IP12', 1, 2),
            ('IP13', 1, 3), ('IP14', 1, 4), ('IP15', 1, 5), ('IP16', 1, 6),
            ('IP17', 1, 7), ('IP18', 1, 8), ('IP19', 1, 9), ('IP16K', 1, 10),
            ('IP19K', 1, 11), ('IP1X', 1, 12), ('IP20', 2, 0), ('IP21', 2, 1),
            ('IP22', 2, 2), ('IP23', 2, 3), ('IP24', 2, 4), ('IP25', 2, 5),
            ('IP26', 2, 6), ('IP27', 2, 7), ('IP28', 2, 8), ('IP29', 2, 9),
            ('IP26K', 2, 10), ('IP29K', 2, 11), ('IP2X', 2, 12), ('IP30', 3, 0),
            ('IP31', 3, 1), ('IP32', 3, 2), ('IP33', 3, 3), ('IP34', 3, 4),
            ('IP35', 3, 5), ('IP36', 3, 6), ('IP37', 3, 7), ('IP38', 3, 8),
            ('IP39', 3, 9), ('IP36K', 3, 10), ('IP39K', 3, 11), ('IP3X', 3, 12),
            ('IP40', 4, 0), ('IP41', 4, 1), ('IP42', 4, 2), ('IP43', 4, 3),
            ('IP44', 4, 4), ('IP45', 4, 5), ('IP46', 4, 6), ('IP47', 4, 7),
            ('IP48', 4, 8), ('IP49', 4, 9), ('IP46K', 4, 10), ('IP49K', 4, 11),
            ('IP4X', 4, 12), ('IP50', 5, 0), ('IP51', 5, 1), ('IP52', 5, 2),
            ('IP53', 5, 3), ('IP54', 5, 4), ('IP55', 5, 5), ('IP56', 5, 6),
            ('IP57', 5, 7), ('IP58', 5, 8), ('IP59', 5, 9), ('IP56K', 5, 10),
            ('IP59K', 5, 11), ('IP5X', 5, 12), ('IP60', 6, 0), ('IP61', 6, 1),
            ('IP62', 6, 2), ('IP63', 6, 3), ('IP64', 6, 4), ('IP65', 6, 5),
            ('IP66', 6, 6), ('IP67', 6, 7), ('IP68', 6, 8), ('IP69', 6, 9),
            ('IP66K', 6, 10), ('IP69K', 6, 11), ('IP6X', 6, 12), ('IPX0', 7, 0),
            ('IPX1', 7, 1), ('IPX2', 7, 2), ('IPX3', 7, 3), ('IPX4', 7, 4),
            ('IPX5', 7, 5), ('IPX6', 7, 6), ('IPX7', 7, 7), ('IPX8', 7, 8),
            ('IPX9', 7, 9), ('IPX6K', 7, 10), ('IPX9K', 7, 11))

    data = [(i,) + item for i, item in enumerate(data)]

    splash.SetText(f'Adding IP ratings to db [0 | {len(data)}]...')
    cur.executemany('INSERT INTO ip_ratings (id, name, solid_id, fluid_id) VALUES (?, ?, ?, ?);', data)
    splash.SetText(f'Adding IP ratings to db [{len(data)} | {len(data)}]...')

    con.commit()


def get_ip_rating_id(con, cur, ip_rating):  # NOQA
    return 0


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'ip_ratings',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.IntField('solid_id', default='7', no_null=True,
                  references=_con.SQLFieldReference(_ip_solids.table, _ip_solids.id_field)),
    _con.IntField('fluid_id', default='7', no_null=True,
                  references=_con.SQLFieldReference(_ip_fluids.table, _ip_fluids.id_field)),
    _con.IntField('solid_id', default='7', no_null=True,
                  references=_con.SQLFieldReference(_ip_supps.table, _ip_supps.id_field))
)


# def ip_ratings(con, cur):
#     cur.execute('CREATE TABLE ip_ratings('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT NOT NULL, '
#                 'solid_id INTEGER DEFAULT 7 NOT NULL, '
#                 'fluid_id INTEGER DEFAULT 12 NOT NULL, '
#                 'supp_id INTEGER DEFAULT NULL, '
#                 'FOREIGN KEY (solid_id) REFERENCES ip_solids(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (fluid_id) REFERENCES ip_fluids(id) ON DELETE SET DEFAULT ON UPDATE CASCADE, '
#                 'FOREIGN KEY (supp_id) REFERENCES ip_supps(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
