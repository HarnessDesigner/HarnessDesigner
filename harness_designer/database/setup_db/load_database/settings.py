import os

from ... import db_connectors as _con


def get_setting(con, cur, name):  # NOQA
    res = cur.execute(f'SELECT value FROM settings WHERE name="{name}";').fetchall()
    return res[0][0]


def add_settings(con, cur, splash, appdata):

    res = cur.execute('SELECT id FROM settings WHERE id=1;')

    if res.fetchall():
        return

    model_path = os.path.join(appdata, "models")
    image_path = os.path.join(appdata, "images")

    if not os.path.exists(model_path):
        os.makedirs(model_path)

    if not os.path.exists(image_path):
        os.makedirs(image_path)

    cur.execute(f'INSERT INTO settings (id, name, value) VALUES(1, "model_path", "{model_path}");')
    cur.execute(f'INSERT INTO settings (id, name, value) VALUES(2, "image_path", "{image_path}");')

    con.commit()


id_field = _con.PrimaryKeyField('id')

settings_table = _con.SQLTable(
    'settings',
    id_field,
    _con.TextField('key', is_unique=True, no_null=True),
    _con.TextField('value', no_null=True)
)


def settings(con, cur):
    cur.execute('CREATE TABLE settings('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'name TEXT UNIQUE NOT NULL, '
                'value BLOB NOT NULL'
                ');')
    con.commit()
