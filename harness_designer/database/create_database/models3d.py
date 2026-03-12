import time
import requests
import io
import zipfile
import uuid
import os


from .. import db_connectors as _con
from . import file_types as _file_types
from . import settings as _settings


def download_model(con, url):
    time.sleep(0.05)
    response = requests.get(url)

    headers = response.headers

    for key, value in headers.items():
        if key.lower() == 'content-type':
            if ';' in value:
                value = value.split(';', 1)[0]
            content_type = value.strip()

            if content_type == 'model/step+zip':
                buf = io.BytesIO(response.content)
                zf = zipfile.ZipFile(buf)
                names = zf.namelist()
                for file_name in names:
                    if file_name.endswith('.step') or file_name.endswith('.stp'):
                        break
                else:
                    zf.close()
                    buf.close()
                    return None, None
                db_id = _file_types.get_file_type(con, cur, os.path.splitext(file_name)[-1][1:])
                data = zf.read(file_name)

                return db_id, data

            elif content_type in ('application/zip', 'application/x-zip-compressed'):
                res = con.execute('SELECT extension FROM file_types WHERE is_model=1;')
                res = res.fetchall()

                extensions = ['.' + row[0] for row in res]

                buf = io.BytesIO(response.content)
                zf = zipfile.ZipFile(buf)
                names = zf.namelist()
                for file_name in names:
                    ext = os.path.splitext(file_name)[-1]
                    if ext in extensions:
                        break
                else:
                    zf.close()
                    buf.close()
                    return None, None

                db_id = _file_types.get_file_type(con, os.path.splitext(file_name)[-1][1:])
                data = zf.read(file_name)

                return db_id, data

            else:
                db_id = _file_types.get_file_type(con, mimetype=content_type)
                if db_id is None:
                    con.execute('SELECT extension FROM file_types WHERE is_model=1;')
                    res = con.fetchall()
                    for row in res:
                        ext = row[0]
                        if '.' + ext in url:
                            break
                    else:
                        return None, None

                    db_id = _file_types.get_file_type(con, ext, content_type)

                data = response.content

                return db_id, data
    else:
        con.execute('SELECT extension FROM file_types WHERE is_model=1;')
        res = con.fetchall()
        for row in res:
            ext = row[0]
            if '.' + ext in url:
                break
        else:
            return None, None

        db_id = _file_types.get_file_type(con, ext)
        data = response.content
        return db_id, data


model_cache = {}


def add_model3d(con, path):
    if not path:
        return None

    if path in model_cache:
        return model_cache[path]

    if path.startswith('http'):
        file_type_id, data = download_model(con, path)
        if file_type_id is None:
            return None

    else:
        con.execute('SELECT extension FROM file_types WHERE is_model=1;')
        res = con.fetchall()
        for row in res:
            ext = row[0]
            if path.endswith('.' + ext):
                break
        else:
            return None

        con.execute(f'SELECT id FROM file_types WHERE extension={ext};')
        file_type_id = con.fetchall()[0][0]

        try:
            with open(path, 'rb') as f:
                data = f.read()
        except OSError:
            return None

    con.execute(f'SELECT extension FROM file_types WHERE id={file_type_id};')
    ext = con.fetchall()[0][0]

    uuid_ = str(uuid.uuid4())

    save_path = _settings.get_setting(con, 'model_path')
    save_path = os.path.join(save_path, uuid_ + '.' + ext)

    with open(save_path, 'wb') as f:
        f.write(data)

    con.execute('INSERT INTO models3d (uuid, file_type_id, path) VALUES(?, ?, ?);', (uuid_, file_type_id, path))
    con.commit()
    db_id = con.lastrowid

    model_cache[path] = db_id
    return db_id


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'models3d',
    id_field,
    _con.TextField('uuid', is_unique=True, no_null=True),
    _con.IntField('file_type_id', no_null=True,
                  references=_con.SQLFieldReference(_file_types.table,
                                                    _file_types.id_field)),
    _con.IntField('target_count', default='25000', no_null=True),
    _con.FloatField('aggressiveness', default='"5.0"', no_null=True),
    _con.IntField('update_rate', default='150', no_null=True),
    _con.IntField('iterations', default='1', no_null=True),
    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('point3d', default='"[0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('scale', default='"[1.0, 1.0, 1.0]"', no_null=True),
    _con.IntField('simplify', default='0', no_null=True),
    _con.TextField('path', no_null=True)
)


# def models3d(con, cur):
#     cur.execute('CREATE TABLE models3d('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'uuid TEXT NOT NULL, '
#                 'file_type_id INTEGER NOT NULL, '
#                 'target_count INTEGER DEFAULT 25000 NOT NULL, '
#                 'aggressiveness REAL DEFAULT "5.0" NOT NULL, '
#                 'update_rate INTEGER DEFAULT 150 NOT NULL, '
#                 'iterations INTEGER DEFAULT 1 NOT NULL, '
#                 'quat3d TEXT DEFAULT "[1.0, 0.0, 0.0, 0.0]" NOT NULL, '
#                 'angle3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'point3d TEXT DEFAULT "[0.0, 0.0, 0.0]" NOT NULL, '
#                 'scale TEXT DEFAULT "[1.0, 1.0, 1.0]" NOT NULL, '
#                 'simplify INTEGER DEFAULT 0 NOT NULL, '
#                 'path TEXT NOT NULL, '
#                 'FOREIGN KEY (file_type_id) REFERENCES file_types(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#
#     con.commit()
