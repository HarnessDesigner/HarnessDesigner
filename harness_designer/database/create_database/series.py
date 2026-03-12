from .. import db_connectors as _con
from . import manufacturers as _manufacturers


def add_records(con, splash):
    con.execute('SELECT id FROM series WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding series to db [0 | 1]...')
    con.execute('INSERT INTO series (id, name) VALUES(0, "No Series");')
    splash.SetText(f'Adding series to db [1 | 1]...')
    con.commit()


def get_series_id(con, name, mfg_id):
    if not name:
        return 0

    con.execute(f'SELECT id FROM series WHERE name="{name}" AND mfg_id={mfg_id};')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding series ("{name}")')

        con.execute('INSERT INTO series (name, mfg_id) VALUES (?, ?);', (name, mfg_id))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'series',
    id_field,
    _con.TextField('name', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE))
)


# def series(con, cur):
#     cur.execute('CREATE TABLE series('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 1 NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()

