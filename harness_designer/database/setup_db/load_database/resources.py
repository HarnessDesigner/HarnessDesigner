import uuid
import os
import time
import requests
import io
from PIL import Image
import zipfile


from ... import db_connectors as _con
from . import settings as _settings
from . import file_types as _file_types


def _download_image(con, cur, url):
    # Downloading an image is not a trivial thing to do. This is because of
    # manufacturers handling images differently. Some there is a single imageand
    # the link contains the extension of the image and that is used to determine
    # the type of image it is. Other times there is no extension and the mime type
    # that gets passed back in the header file is what is used to determine
    # what needs to be added for an extension. They also encapsulate more than
    # one image into a zip file and in those cases the file extension is available
    # and that is what gets used.
    time.sleep(0.05)
    print('requests.get')
    try:
        response = requests.get(url, timeout=1000)
    except:  # NOQA
        import traceback
        traceback.print_exc()
        return None

    print('response gotten')

    headers = response.headers

    rows = cur.execute('SELECT mimetype FROM file_types WHERE is_model=0;')
    rows = rows.fetchall()

    content_types = [row[0] for row in rows]

    rows = cur.execute('SELECT extension FROM file_types WHERE is_model=0;')
    rows = rows.fetchall()

    exts = ['.' + row[0] for row in rows]

    for key, value in headers.items():
        if key.lower() == 'content-type':
            if ';' in value:
                value = value.split(';', 1)[0]
            content_type = value.strip()

            if content_type in ('application/zip', 'application/x-zip-compressed'):

                buf = io.BytesIO(response.content)
                zf = zipfile.ZipFile(buf)
                names = zf.namelist()
                for file_name in names:
                    ext = os.path.splitext(file_name)[-1]
                    if ext in exts:
                        break
                else:
                    zf.close()
                    buf.close()
                    return None

                ext = ext[1:]
                data = zf.read(file_name)
                break

            elif content_type in content_types:
                rows = cur.execute(f'SELECT extension FROM file_types WHERE is_model=0 AND mimetype="{content_type}";')

                ext = rows.fetchall()[0][0]
                data = response.content
                break

    else:
        for ext in exts:
            if ext in url:
                ext = ext[1:]
                data = response.content
                break
        else:
            return None

    uuid_ = str(uuid.uuid4())

    image_path = _settings.get_setting(con, cur, 'image_path')
    image_path = os.path.join(image_path, uuid_ + '.' + ext)

    with open(image_path, 'wb') as f:
        f.write(data)

    return image_path


image_cache = {}


IMAGE_TYPE_IMAGE = 1
IMAGE_TYPE_DATASHEET = 2
IMAGE_TYPE_CAD = 3


def add_resource(con, cur, image_type, path):
    if not path:
        return None

    if path in image_cache:
        return image_cache[path]

    if path.startswith('http'):
        image_path = _download_image(con, cur, path)

        if image_path is None:
            return None

    else:
        rows = cur.execute('SELECT extension FROM file_types WHERE is_model=0;').fetchall()
        for row in rows:
            ext = row[0]
            if path.endswith('.' + ext):
                uuid_ = str(uuid.uuid4())

                image_path = _settings.get_setting(con, cur, 'image_path')
                image_path = os.path.join(image_path, uuid_ + '.' + ext)

                try:
                    with open(image_path, 'wb') as wf:
                        with open(path, 'rb') as rf:
                            wf.write(rf.read())
                except OSError:
                    return None

                break
        else:
            return None

    if image_type == IMAGE_TYPE_IMAGE:
        # we want to resize the image to fit into a 256, 256 preview so to do that
        # the aspect ratio needs to be calculate. we have to first determine
        # the long "side" and then set that one to 256 and using the aspect ratio
        # set the smaller size to 256 * aspect. We also want the image to be
        # properly centered in that 256 x 256 because one side might be smaller
        # so we create a new empty image and paste the resized image

        img = Image.open(image_path)

        w, h = img.size

        if w > h:
            aspect_ratio = h / w

            w = 256
            h = int(480 * aspect_ratio)
        else:
            aspect_ratio = w / h

            h = 256
            w = int(h * aspect_ratio)

        img = img.resize((w, h), Image.Resampling.LANCZOS)

        new_img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))

        offset_x = 256 - w
        offset_y = 256 - h

        new_image_path = os.path.splitext(image_path)[0] + '.png'

        new_img.paste(img, (offset_x, offset_y))
        new_img.save(new_image_path)

        os.remove(image_path)
        image_path = new_image_path

    uuid_ = os.path.split(image_path)[-1]
    uuid_, ext = os.path.splitext(uuid_)
    ext = ext[1:]

    rows = cur.execute(f'SELECT extension FROM file_types WHERE is_model=0 AND extension="{ext[1:]}";')
    file_type_id = rows.fetchall()[0][0]

    cur.execute('INSERT INTO resources (uuid, file_type_id, path) VALUES(?, ?, ?);', (uuid_, file_type_id, path))
    con.commit()
    db_id = cur.lastrowid

    image_cache[path] = db_id
    return db_id


def get_resource_id(con, cur, path, type="UNKNOWN"):  # NOQA
    if not path:
        return None

    res = cur.execute(f'SELECT id FROM resources WHERE path="{path}";').fetchall()

    if not res:
        if type == 'UNKNOWN':
            if '.jpg' in path:
                type = 'jpg'  # NOQA
            elif '.pdf' in path:
                type = 'pdf'  # NOQA
            elif '.tif' in path:
                type = 'tif'  # NOQA
            elif '.png' in path:
                type = 'png'  # NOQA

        print(f'DATABASE: adding resource ("{path}", "{type}")')

        cur.execute('INSERT INTO resources (path, file_type_id) VALUES (?, ?);', (path, type))

        con.commit()
        db_id = cur.lastrowid

        print(f'DATABASE: resource added "{path}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

resources_table = _con.SQLTable(
    'resources',
    id_field,
    _con.TextField('uuid', is_unique=True, no_null=True),
    _con.IntField('file_type_id', no_null=True,
                  references=_con.SQLFieldReference(_file_types.file_types_table, _file_types.id_field)),
    _con.BlobField('data', default='NULL'),
    _con.TextField('path', no_null=True)
)


# def resources(con, cur):
#     cur.execute('CREATE TABLE resources('
#                 'id INTEGER PRIMARY KEY AUTOINCREMENT, '
#                 'uuid TEXT NOT NULL, '
#                 'file_type_id INTEGER NOT NULL, '
#                 'data BLOB DEFAULT NULL, '
#                 'path TEXT NOT NULL, '
#                 'FOREIGN KEY (file_type_id) REFERENCES file_types(id) ON DELETE CASCADE ON UPDATE CASCADE'
#                 ');')
#     con.commit()
