from .. import db_connectors as _con
from . import manufacturers as _manufacturers


def add_records(con, splash):
    con.execute('SELECT id FROM families WHERE id=0;')
    if con.fetchall():
        return

    data = (0, 'No Family', 0)

    splash.SetText(f'Adding families to db [{len(data)} | {len(data)}]...')
    con.execute('INSERT INTO families (id, name, mfg_id) VALUES(?, ?, ?);', data)
    con.commit()


def get_family_id(con, name, mfg_id):
    if not name:
        return 0

    con.execute(f'SELECT id FROM families WHERE name="{name}" AND mfg_id={mfg_id};')
    res = con.fetchall()

    if not res:
        print(f'DATABASE: adding family ("{name}")')

        con.execute('INSERT INTO families (name, mfg_id) VALUES (?, ?);', (name, mfg_id))

        con.commit()
        db_id = con.lastrowid

        print(f'DATABASE: family added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'families',
    id_field,
    _con.TextField('name', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE))
)

# def families(con, cur):
#     cur.execute('CREATE TABLE families('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT NOT NULL, '
#                 'description TEXT DEFAULT "" NOT NULL, '
#                 'mfg_id INTEGER DEFAULT 0 NOT NULL, '
#                 'FOREIGN KEY (mfg_id) REFERENCES manufacturers(id) ON DELETE SET DEFAULT ON UPDATE CASCADE'
#                 ');')
#     con.commit()
