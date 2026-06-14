# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Helpers for downloading and normalising external resource files."""
import tempfile

import requests
import time
import uuid
import os
import io
import shutil
import zipfile
from PIL import Image
import requests.exceptions
from urllib.parse import urlsplit
import http.cookiejar

COOKIES = {}

header = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Priority": "u=0, i",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-GPC": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0"
}


class ResourceException(Exception):
    __msg__ = 'Resource Base Exception'

    def __init__(self):
        super().__init__(self.__msg__)


class RequestsError(ResourceException):
    __msg__ = ''

    def __init__(self, msg, code, url):
        self.__msg__ = msg
        self.code = code
        self.url = url
        super().__init__()


class ImageReadError(ResourceException):

    __msg__ = 'Image Read Error'

    def __init__(self, path):
        self.path = path
        self.code = -10
        super().__init__()


class SaveFileError(ResourceException):

    __msg__ = 'Save File Error'

    def __init__(self, path, code):
        self.path = path
        self.code = code
        super().__init__()


class RemoveFileError(ResourceException):

    __msg__ = 'Remove File Error'

    def __init__(self, path, code):
        self.path = path
        self.code = code
        super().__init__()


class FileTypeNotSupportedError(ResourceException):

    __msg__ = 'File Type Not Supported'

    def __init__(self, path):
        self.path = path
        self.code = -20
        super().__init__()


class ExistingFileNotFoundError(ResourceException):

    __msg__ = 'File Not Found'

    def __init__(self, path):
        self.path = path
        self.code = -30
        super().__init__()


def handle_cookie(response):
    """
    Extract cookie data from a requests response.

    :param response: HTTP response returned by :mod:`requests`.
    :type response: requests.Response
    """

    for cookie in response.cookies:
        if not cookie.domain_specified:
            continue

        domain = cookie.domain
        if domain:
            if cookie.domain.startswith('.'):
                domain = domain[1:]

            if domain not in COOKIES:
                COOKIES[domain] = {}

            COOKIES[domain][cookie.name] = cookie


def requests_get(url, is_retry=False, **kwargs):
    """
    Fetch a URL and normalise its content type.

    :param url: Resource URL to request.
    :type url: str
    :param is_retry: If this is a second attempt.
                     This is used internally for requests to TE
                     because of needing to set the cookie.
    :type is_retry: bool

    :param kwargs: Extra keyword arguments forwarded to :func:`requests.get`.
    :type kwargs: dict
    :returns: Response object and simplified content type.
    :rtype: tuple[requests.Response, str | None]
    """

    if 'api.te.com' in url or 'www.te.com' in url:
        url = url.replace('//content', '/content')

    split_url = urlsplit(url)

    cookies = http.cookiejar.CookieJar()
    domain = split_url.netloc
    path = split_url.path

    for cookie_domain in COOKIES.keys():
        if domain.endswith(cookie_domain):
            domain_cookies = COOKIES[cookie_domain]
            for cookie in domain_cookies.values():
                if cookie.path_specified:
                    if path.startswith(cookie.path):
                        cookies.set_cookie(cookie)
                else:
                    cookies.set_cookie(cookie)
    try:
        response = requests.get(url, headers=header, cookies=cookies, **kwargs)

        if response.status_code == 503:
            if 'api.te.com' in url:
                url = url.replace('api.te.com', 'www.te.com')
                return requests_get(url, is_retry=False, **kwargs)

    except requests.exceptions.RequestException as err:
        if err.response.status_code == 503:
            if 'api.te.com' in url:
                url = url.replace('api.te.com', 'www.te.com')
                return requests_get(url, is_retry=False, **kwargs)

        if is_retry:
            new_err = RequestsError(
                err.response.reason, err.response.status_code, url)

            raise new_err from err
        else:
            return requests_get(url, is_retry=True, **kwargs)

    handle_cookie(response)

    content_type = response.headers.get(
        'content-type', response.headers.get('Content-Type', ''))

    if content_type:
        content_type = content_type.split(';')[0]
    else:
        content_type = None

    return response, content_type, url


def _download_model(con, url, is_type):
    """
    Download a model resource and store it with a generated filename.

    :param con: Database cursor or cursor-like object.
    :type con: UNKNOWN
    :param url: Source URL.
    :type url: str
    :returns: Saved file path, or ``None`` when the download cannot be mapped to
        a supported model type.
    :rtype: str | None
    """

    con.execute(f'SELECT mimetype, extension FROM file_types WHERE {is_type};')
    rows = con.fetchall()
    mime_types = {k: '.' + v for k, v in rows}
    extensions = ['.' + row[1] for row in rows]

    response, content_type, used_url = requests_get(url)

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
                raise FileTypeNotSupportedError(used_url)

            data = zf.read(file_name)
            zf.close()
            buf.close()
        else:
            if content_type in mime_types:
                ext = mime_types[content_type]
            else:
                ext = [e for e in extensions if e in used_url]
                if ext:
                    ext = ext[0]
                else:
                    raise FileTypeNotSupportedError(used_url)

            data = response.content
    else:
        ext = [e for e in extensions if e in used_url]
        if ext:
            ext = ext[0]
        else:
            raise FileTypeNotSupportedError(used_url)

        data = response.content

    uuid_ = str(uuid.uuid4())
    model_path = os.path.join(tempfile.gettempdir(), uuid_ + ext)

    try:
        with open(model_path, 'wb') as f:
            f.write(data)
    except OSError as err:
        raise SaveFileError(model_path, err.errno)

    return model_path


def _reformat_image(img: Image.Image):
    """
    Resize and pad an image into a 256x256 RGBA preview.

    :param img: Source image.
    :type img: PIL.Image.Image
    :returns: Reformatted preview image.
    :rtype: PIL.Image.Image
    """

    img = img.convert('RGBA')
    o_w, o_h = img.size

    if o_w > o_h:
        aspect_ratio = o_w / o_h

        w = 250
        h = int(w / aspect_ratio)
    else:
        aspect_ratio = o_h / o_w

        h = 250
        w = int(h / aspect_ratio)

    img = img.resize((w, h), Image.Resampling.LANCZOS)

    r, g, b, a = img.getpixel((0, 0))

    new_img = Image.new('RGBA', (256, 256), (r, g, b, a))

    offset_x = int((256 - w) / 2)
    offset_y = int((256 - h) / 2)

    new_img.paste(img, (offset_x, offset_y))
    return new_img


def _download_image(con, url, image_path, is_type):
    """
    Download an image-like resource and save it locally.

    :param con: Database cursor or cursor-like object.
    :type con: UNKNOWN
    :param url: Source URL.
    :type url: str
    :param image_path: Destination directory.
    :type image_path: str
    :returns: Saved file path, or ``None`` when the resource type is unsupported
        or the request fails.
    :rtype: str | None
    """

    # Downloading an image is not a trivial thing to do. This is because of
    # manufacturers handling images differently. Some there is a single image and
    # the link contains the extension of the image and that is used to determine
    # the type of image it is. Other times there is no extension and the mime type
    # that gets passed back in the header file is what is used to determine
    # what needs to be added for an extension. They also encapsulate more than
    # one image into a zip file and in those cases the file extension is available
    # and that is what gets used.

    con.execute(f'SELECT mimetype, extension FROM file_types WHERE {is_type};')
    rows = con.fetchall()
    mime_types = {k: '.' + v for k, v in rows}
    extensions = ['.' + row[1] for row in rows]

    response, content_type, used_url = requests_get(url, timeout=1000)

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
                raise FileTypeNotSupportedError(used_url)

            data = zf.read(file_name)

        elif content_type in mime_types:
            ext = mime_types[content_type]
            data = response.content
        else:
            raise FileTypeNotSupportedError(used_url)
    else:
        ext = [e for e in extensions if e in used_url]
        if ext:
            ext = ext[0]
            data = response.content
        else:
            raise FileTypeNotSupportedError(used_url)

    uuid_ = str(uuid.uuid4())
    image_path = os.path.join(image_path, uuid_[:2], uuid_ + ext)

    try:
        with open(image_path, 'wb') as f:
            f.write(data)
    except OSError as err:
        raise SaveFileError(image_path, err.errno)

    return image_path


RESOURCE_TYPE_IMAGE = 1
RESOURCE_TYPE_DATASHEET = 2
RESOURCE_TYPE_CAD = 3
RESOURCE_TYPE_MODEL = 4


def collect_resource(con, image_type, in_path):
    """
    Collect a local or remote resource into managed storage.

    :param con: Database cursor or cursor-like object.
    :type con: UNKNOWN
    :param image_type: Resource category constant such as :data:`RESOURCE_TYPE_IMAGE`.
    :type image_type: int
    :param in_path: Local path or URL for the resource.
    :type in_path: str | None
    :returns: Resource UUID and file-type identifier, or ``None`` when the input
        cannot be collected.
    :rtype: tuple[str, int] | None
    :raises RuntimeError: If a referenced local file does not exist.
    """

    if not in_path:
        return None

    if image_type == RESOURCE_TYPE_IMAGE:
        path_name = 'image_path'
        is_type = 'is_image=1'
    elif image_type == RESOURCE_TYPE_DATASHEET:
        path_name = 'datasheet_path'
        is_type = 'is_datasheet=1'
    elif image_type == RESOURCE_TYPE_CAD:
        path_name = 'cad_path'
        is_type = 'is_cad=1'
    elif image_type == RESOURCE_TYPE_MODEL:
        path_name = 'model_path'
        is_type = 'is_model=1'
    else:
        return None

    con.execute(f'SELECT value FROM settings WHERE name="{path_name}";')
    image_path = con.fetchall()[0][0]

    if in_path.startswith('http'):
        if image_type == RESOURCE_TYPE_MODEL:
            image_path = _download_model(con, in_path, is_type)
        else:
            image_path = _download_image(con, in_path, image_path, is_type)

        if image_path is None:
            return None
    else:
        con.execute(f'SELECT extension FROM file_types WHERE {is_type};')
        rows = con.fetchall()
        for row in rows:
            ext = row[0]
            if in_path.endswith('.' + ext):
                uuid_ = str(uuid.uuid4())

                if image_type == RESOURCE_TYPE_MODEL:
                    image_path = tempfile.gettempdir()

                image_path = os.path.join(image_path, uuid_ + '.' + ext)

                if not os.path.exists(in_path):
                    raise ExistingFileNotFoundError(in_path)

                shutil.copyfile(in_path, image_path)
                break
        else:
            raise FileTypeNotSupportedError(in_path)

    if image_type == RESOURCE_TYPE_IMAGE:
        # we want to resize the image to fit into a 256, 256 preview so to do that
        # the aspect ratio needs to be calculate. we have to first determine
        # the long "side" and then set that one to 256 and using the aspect ratio
        # set the smaller size to 256 * aspect. We also want the image to be
        # properly centered in that 256 x 256 because one side might be smaller
        # so we create a new empty image and paste the resized image

        try:
            img = Image.open(image_path)
        except Exception as err:  # NOQA
            raise ImageReadError(image_path) from err

        img = _reformat_image(img)

        new_image_path = os.path.splitext(image_path)[0] + '.png'

        try:
            img.save(new_image_path)
        except Exception as err:  # NOQA
            raise SaveFileError(new_image_path, -50)

        if image_path != new_image_path:
            try:
                os.remove(image_path)
            except OSError as err:
                raise RemoveFileError(image_path, err.errno) from err

        image_path = new_image_path

    filename = os.path.split(image_path)[-1]
    uuid_, ext = os.path.splitext(filename)

    con.execute(f'SELECT id FROM file_types WHERE {is_type} AND extension="{ext[1:]}";')
    file_type_id = con.fetchall()[0][0]

    if image_type == RESOURCE_TYPE_MODEL:
        return image_path, file_type_id

    return uuid_, file_type_id
