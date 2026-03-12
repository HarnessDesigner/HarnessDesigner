import os

from .. import db_connectors as _con


def get_setting(con, cur, name):  # NOQA
    res = cur.execute(f'SELECT value FROM settings WHERE name="{name}";').fetchall()
    return res[0][0]


def add_records(con, splash, appdata):
    con.execute('SELECT id FROM settings WHERE id=1;')
    if con.fetchall():
        return

    splash.SetText(f'Building settings...')

    model_path = os.path.join(appdata, "models")
    image_path = os.path.join(appdata, "images")

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    if not os.path.exists(image_path):
        os.makedirs(image_path)

    splash.SetText(f'Adding CPA lock to db [1 | 2]...')
    con.execute(f'INSERT INTO settings (id, name, value) VALUES(1, "model_path", "{model_path}");')

    splash.SetText(f'Adding CPA lock to db [2 | 2]...')
    con.execute(f'INSERT INTO settings (id, name, value) VALUES(2, "image_path", "{image_path}");')

    con.commit()


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'settings',
    id_field,
    _con.TextField('key', is_unique=True, no_null=True),
    _con.TextField('value', no_null=True)
)


# def settings(con, cur):
#     cur.execute('CREATE TABLE settings('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'name TEXT UNIQUE NOT NULL, '
#                 'value BLOB NOT NULL'
#                 ');')
#     con.commit()
