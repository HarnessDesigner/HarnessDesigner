import requests
import time
import uuid
import os
import io
import shutil
import zipfile
from PIL import Image

from . import logger as _logger


def _download_model(con, url, model_path):
    time.sleep(0.01)
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
                        ext = '.stp'
                        break
                else:
                    zf.close()
                    buf.close()
                    return None

                data = zf.read(file_name)

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
                    return None

                data = zf.read(file_name)
            else:
                con.execute('SELECT extension, mimetype FROM file_types WHERE is_model=1;')
                res = con.fetchall()
                for row in res:
                    ext = row[0]
                    mimetype = row[1]
                    if mimetype == content_type:
                        break
                    if '.' + ext in url:
                        break
                else:
                    return None

                data = response.content

            break
    else:
        con.execute('SELECT extension FROM file_types WHERE is_model=1;')
        res = con.fetchall()
        for row in res:
            ext = row[0]
            if '.' + ext in url:
                ext = '.' + ext
                break
        else:
            return None

        data = response.content

    uuid_ = str(uuid.uuid4())

    model_path = os.path.join(model_path, uuid_ + ext)

    with open(model_path, 'wb') as f:
        f.write(data)

    return model_path


def _download_image(con, url, image_path):
    # Downloading an image is not a trivial thing to do. This is because of
    # manufacturers handling images differently. Some there is a single imageand
    # the link contains the extension of the image and that is used to determine
    # the type of image it is. Other times there is no extension and the mime type
    # that gets passed back in the header file is what is used to determine
    # what needs to be added for an extension. They also encapsulate more than
    # one image into a zip file and in those cases the file extension is available
    # and that is what gets used.
    time.sleep(0.01)
    try:
        response = requests.get(url, timeout=1000)
    except Exception as err:  # NOQA
        _logger.logger.traceback(err, 'REQUESTS ERROR')
        return None

    headers = response.headers

    con.execute('SELECT mimetype FROM file_types WHERE is_model=0;')
    rows = con.fetchall()

    content_types = [row[0] for row in rows]

    con.execute('SELECT extension FROM file_types WHERE is_model=0;')
    rows = con.fetchall()

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
                con.execute(f'SELECT extension FROM file_types WHERE is_model=0 AND mimetype="{content_type}";')
                ext = con.fetchall()[0][0]
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

    image_path = os.path.join(image_path, uuid_ + '.' + ext)

    with open(image_path, 'wb') as f:
        f.write(data)

    return image_path


image_cache = {}


IMAGE_TYPE_IMAGE = 1
IMAGE_TYPE_DATASHEET = 2
IMAGE_TYPE_CAD = 3
IMAGE_TYPE_MODEL = 4


def collect_resource(con, image_type, in_path):
    if not in_path:
        return None

    if in_path in image_cache:
        return image_cache[in_path]

    if image_type == IMAGE_TYPE_IMAGE:
        path_name = 'image_path'
    elif image_type == IMAGE_TYPE_DATASHEET:
        path_name = 'datasheet_path'
    elif image_type == IMAGE_TYPE_CAD:
        path_name = 'cad_path'
    elif image_type == IMAGE_TYPE_MODEL:
        path_name = 'model_path'
    else:
        return None

    con.execute(f'SELECT value FROM settings WHERE name="{path_name}";')
    image_path = con.fetchall()[0][0]

    if in_path.startswith('http'):
        if image_type == IMAGE_TYPE_MODEL:
            image_path = _download_model(con, in_path, image_path)

        else:
            image_path = _download_image(con, in_path, image_path)

        if image_path is None:
            return None
    else:
        con.execute(f'SELECT extension FROM file_types WHERE is_model={int(image_type == IMAGE_TYPE_MODEL)};')
        rows = con.fetchall()
        for row in rows:
            ext = row[0]
            if in_path.endswith('.' + ext):
                uuid_ = str(uuid.uuid4())

                image_path = os.path.join(image_path, uuid_ + '.' + ext)

                if not os.path.exists(in_path):
                    raise RuntimeError(in_path)

                shutil.copyfile(in_path, image_path)
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

        try:
            img = Image.open(image_path)
        except:  # NOQA
            return None

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

    con.execute(f'SELECT id FROM file_types WHERE is_model={int(image_type == IMAGE_TYPE_MODEL)} AND extension="{ext}";')
    file_type_id = con.fetchall()[0][0]

    image_cache[in_path] = (uuid_, file_type_id)

    return uuid_, file_type_id
