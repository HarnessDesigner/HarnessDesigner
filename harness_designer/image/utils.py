# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Image conversion helpers used by :mod:`harness_designer.image`."""

import io
from PIL import Image

from PySide6.QtGui import QPixmap, QImage, QCursor


def bytes_data_2_pil_image(data: bytes) -> Image.Image:
    """Decode PNG bytes into a PIL image.

    :param data: PNG-encoded image bytes.
    :type data: bytes
    :returns: Image converted to ``RGBA``.
    :rtype: PIL.Image.Image
    :raises OSError: Raised when the bytes cannot be decoded as an image.
    """
    buf = io.BytesIO(data)
    buf.seek(0)
    img = Image.open(buf).convert('RGBA')
    buf.close()
    return img


def pil_image_2_png_bytes(img: Image.Image) -> bytes:
    """Encode a PIL image as PNG bytes.

    :param img: Image to encode.
    :type img: PIL.Image.Image
    :returns: PNG-encoded image bytes.
    :rtype: bytes
    """
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    data = buf.getvalue()
    buf.close()
    return data


def bytes_data_2_qpixmap(data: bytes) -> QPixmap:
    """Decode PNG bytes into a Qt pixmap.

    :param data: PNG-encoded image bytes.
    :type data: bytes
    :returns: Pixmap loaded from the provided bytes.
    :rtype: :class:`PySide6.QtGui.QPixmap`
    """
    pm = QPixmap()
    pm.loadFromData(data, 'PNG')
    return pm


def pil_image_2_qpixmap(img: Image.Image) -> QPixmap:
    """Convert a PIL image into a Qt pixmap.

    :param img: Image to convert.
    :type img: PIL.Image.Image
    :returns: Pixmap created from the converted image.
    :rtype: :class:`PySide6.QtGui.QPixmap`
    """
    img_rgba = img.convert('RGBA')
    data = img_rgba.tobytes('raw', 'RGBA')
    qimg = QImage(data, img_rgba.width, img_rgba.height, QImage.Format_RGBA8888)
    pm = QPixmap.fromImage(qimg)
    return pm


def pil_image_2_qimage(img: Image.Image) -> QImage:
    """Convert a PIL image into a detached Qt image.

    :param img: Image to convert.
    :type img: PIL.Image.Image
    :returns: Copy of the converted Qt image.
    :rtype: :class:`PySide6.QtGui.QImage`
    """
    img_rgba = img.convert('RGBA')
    data = img_rgba.tobytes('raw', 'RGBA')
    qimg = QImage(data, img_rgba.width, img_rgba.height, QImage.Format_RGBA8888)
    return qimg.copy()


def resize_pil_image(img: Image.Image, width: int, height: int = None) -> Image.Image:
    """Resize a PIL image, preserving aspect ratio when height is omitted.

    :param img: Image to resize.
    :type img: PIL.Image.Image
    :param width: Target width in pixels.
    :type width: int
    :param height: Optional target height in pixels.
    :type height: int | None
    :returns: Resized image.
    :rtype: PIL.Image.Image
    """
    if height is None:
        height = int(width * (img.size[1] / img.size[0]))
    return img.resize((width, height), resample=Image.Resampling.LANCZOS)


def rotate_pil_image(img: Image.Image, angle: float) -> Image.Image:
    """Rotate a PIL image with transparency preserved.

    :param img: Image to rotate.
    :type img: PIL.Image.Image
    :param angle: Rotation angle in degrees.
    :type angle: float
    :returns: Rotated image.
    :rtype: PIL.Image.Image
    """
    return img.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                      fillcolor=(0, 0, 0, 0))


def pil_image_2_qcursor(img: Image.Image,
                         hotspot_x: int | None = None,
                         hotspot_y: int | None = None) -> QCursor:
    """Convert a PIL image into a Qt cursor.

    :param img: Image to convert.
    :type img: PIL.Image.Image
    :param hotspot_x: Optional cursor hotspot X coordinate.
    :type hotspot_x: int | None
    :param hotspot_y: Optional cursor hotspot Y coordinate.
    :type hotspot_y: int | None
    :returns: Cursor created from the image.
    :rtype: :class:`PySide6.QtGui.QCursor`
    """
    if hotspot_x is None:
        hotspot_x = img.width // 2
    if hotspot_y is None:
        hotspot_y = img.height // 2
    pm = pil_image_2_qpixmap(img)
    return QCursor(pm, hotspot_x, hotspot_y)
