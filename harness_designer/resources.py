import requests
import time
import uuid
import os
import io
import shutil
import zipfile
from PIL import Image

from . import logger as _logger


# TE specific handling to be able to download the models and images..

te_header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Cookie": "AMCV_A638776A5245AFE50A490D44%40AdobeOrg=-432600572%7CMCIDTS%7C20535%7CMCMID%7C37036414041189707455185991421694069091%7CMCAID%7CNONE%7CMCOPTOUT-1774225132s%7CNONE%7CvVersion%7C4.5.2; mbox=PC#beb9df17c300479ca08ccf13ef8a58b2.35_0#1833504047|session#f1a88b24f80e4eac984ed4c8d2b1ab12#1770261107; ak_bmsc=EDE5568E0F944C7D10F5E9D3BB81A486~000000000000000000000000000000~YAAQ0QbSF0nv4hGdAQAAmPWOFx/QxbuHgmvOTSkZeF2WgI5DgMnePuKWJkLWu96ednjORM+KGCQuxWt/VfdAKVyUb7jhrKfk/ysmIoPLS73kSKjt03p6vhxjoIXts/xe4HI9XNeKQYYaxA8Gke3fXpWQktCj3eXk734nt0tY8EPujA+H0PLCtzoJBDfTrUX4HZ9P7G6c5Vgby7TCiYWFmlsJoiiQQblLv0maa+yYdsSbEI8OPY+tXCaMDRjFV4cuziaJ3qANqqw4w5QEODFPbCp4+M9zuG8PhNxa68KjzE9knJOfynWUZRS5Tk1tlbTUML+A1oblhsGxc/PJqUxJBwMe0IPBMf9R2V8laytGwHIx8VyCpvnirDAGRynqGVn0ZdDxiwWNmsc=; bm_sv=39302999CCFF0E2A80E2D5C20F724A28~YAAQkBLfF6XbEPycAQAASeuoFx/0WDxPsXYsTvEb+DseTSMVAjTBISB2WvxdMzdl0oqOd29IAeomR6rxRZWtBL7uUNP6jHaKGlRyGAflfQb7/5jkoBLnjqTtuoSUKzOw7ZiUpb+u6fzpNR9QueNVPGuTaqXU/d0SgJkhNHnG7MYBHLT0YGQfNGNW/9K/FY9eqPL6ZygEcr1YLZbL3hQo/49BNgUyEoQUD8iF5FLN1zKtf/Esi0MFBXLlbtYU~1; AKA_A2=A; PIM-SESSION-ID=NMR1iHrXLmHDeDi4; SSO=guestusr@te.com; SMIDENTITY=InRxrBAYZz8g7rTGTOYCnIoLgg3gV4I0i/kiE813fMLg3oNT4xuFEng+DWhlVp3kfeunacUQWugx9g61BCwuWIenxjPqdwIAyBe4Pn2onUkx9VGkTpnvaHLGLb+FkBWGKgVILK8yaNx2W86nIJ1cdoGjeVjfo+p+2ralcv2kWKM1OYjBLZq5RetbpQ8uebkRCfYGJCqc4M6U71Fm6n4TfynF+KGaaBZBZP4GxoUgPZqqegiYcyHcxnJN2/fB3w+JvmvhFTUOlpbMOVkBG+n29PemJV3zxVuOUvIrfQpGPHbWKWVluvmQM4FE0RTkHpFZTHTya6+AZ976Nfyq2DWNKS2W+zSg9bwyAM85xAGAN5mqoFKmI1adSTxVmZOl9rShPr+XtOACeL9fbBdkCaxRp0uS7oIo4PQUXPhq0CJQssMQ+K8asroHOkwbfPm6++ObanVIpmuIB4gzns6jGUFeDQqLdOnvpyq6KE1ZLtqXRh2PtZBoEGNDcEzLh5Ep+HG2KnnL/4t0IoSSjxNabCla9LFUNjmLhJ3JVahuPmNf8jYX2eUvDmN6C0GFkGCjDRMA; AMCVS_A638776A5245AFE50A490D44%40AdobeOrg=1; dtCookie=v_4_srv_1_sn_57988F6CE361C9761D87B0C01E4EE007_perc_100000_ol_0_mul_1_app-3A619a1bcb124cd83e_1",
    "Host": "api.te.com",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Sec-GPC": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0"
}


def handle_te_cookie(response):
    if 'Set-Cookie' in response.headers:
        cur_cookie = te_header['Cookie']

        cur_cookie = [item.strip() for item in cur_cookie.split(';')]
        cookie = {item.split('=', 1)[0]: item.split('=', 1)[1] for item in cur_cookie}

        new_cookie = [item.strip() for item in response.headers['Set-Cookie'].split(';')]
        new_cookie = {item.split('=', 1)[0]: item.split('=', 1)[1] for item in new_cookie if '=' in item}

        for key, value in new_cookie.items():
            if key in cookie:
                cookie[key] = value

        cookie = [key + '=' + value for key, value in cookie.items()]
        cookie = '; '.join(cookie)
        te_header['Cookie'] = cookie


def requests_get(url, **kwargs):
    if 'www.te.com' in url:
        response = requests.get(url, headers=te_header, **kwargs)
        handle_te_cookie(response)
    else:
        response = requests.get(url, **kwargs)

    content_type = response.headers.get(
        'content-type', response.headers.get('Content-Type', ''))

    if content_type:
        content_type = content_type.split(';')[0]
    else:
        content_type = None

    return response, content_type


def _download_model(con, url, model_path):
    con.execute('SELECT mimetype, extension FROM file_types WHERE is_model=1;')
    rows = con.fetchall()
    mime_types = {k: '.' + v for k, v in rows}
    extensions = ['.' + row[1] for row in rows]

    time.sleep(0.01)
    response, content_type = requests_get(url)
    if content_type is not None:
        if content_type in (
            'application/zip',
            'application/x-zip-compressed',
            'model/step+zip'
        ):
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
            zf.close()
            buf.close()
        else:

            if content_type in mime_types:
                ext = mime_types[content_type]
            else:
                ext = [e for e in extensions if e in url]
                if ext:
                    ext = ext[0]
                else:
                    return None

            data = response.content
    else:
        ext = [e for e in extensions if e in url]
        if ext:
            ext = ext[0]
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

    con.execute('SELECT mimetype, extension FROM file_types WHERE is_model=0;')
    rows = con.fetchall()
    mime_types = {k: '.' + v for k, v in rows}
    extensions = ['.' + row[1] for row in rows]

    time.sleep(0.01)
    try:
        response, content_type = requests_get(url, timeout=1000)
    except Exception as err:  # NOQA
        _logger.logger.traceback(err, 'REQUESTS ERROR')
        return None

    if content_type is not None:
        if content_type in ('application/zip', 'application/x-zip-compressed'):
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

        elif content_type in mime_types:
            ext = mime_types[content_type]
            data = response.content
        else:
            return None
    else:
        ext = [e for e in extensions if e in url]
        if ext:
            ext = ext[0]
            data = response.content
        else:
            return None

    uuid_ = str(uuid.uuid4())
    image_path = os.path.join(image_path, uuid_ + ext)

    with open(image_path, 'wb') as f:
        f.write(data)

    return image_path


_image_cache = {}


IMAGE_TYPE_IMAGE = 1
IMAGE_TYPE_DATASHEET = 2
IMAGE_TYPE_CAD = 3
IMAGE_TYPE_MODEL = 4


def collect_resource(con, image_type, in_path):
    if not in_path:
        return None

    if in_path in _image_cache:
        return _image_cache[in_path]

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
            h = int(w * aspect_ratio)
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

        if image_path != new_image_path:
            os.remove(image_path)

        image_path = new_image_path

    filename = os.path.split(image_path)[-1]
    uuid_, ext = os.path.splitext(filename)

    con.execute(f'SELECT id FROM file_types WHERE is_model={int(image_type == IMAGE_TYPE_MODEL)} AND extension="{ext[1:]}";')
    file_type_id = con.fetchall()[0][0]

    _image_cache[in_path] = (uuid_, file_type_id)

    return uuid_, file_type_id
