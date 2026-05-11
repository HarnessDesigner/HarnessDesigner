# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import io
from PIL import Image

from PySide6.QtGui import QPixmap, QImage, QCursor


def bytes_data_2_pil_image(data: bytes) -> Image.Image:
    buf = io.BytesIO(data)
    buf.seek(0)
    img = Image.open(buf).convert('RGBA')
    buf.close()
    return img


def pil_image_2_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    data = buf.getvalue()
    buf.close()
    return data


def bytes_data_2_qpixmap(data: bytes) -> QPixmap:
    pm = QPixmap()
    pm.loadFromData(data, 'PNG')
    return pm


def pil_image_2_qpixmap(img: Image.Image) -> QPixmap:
    img_rgba = img.convert('RGBA')
    data = img_rgba.tobytes('raw', 'RGBA')
    qimg = QImage(data, img_rgba.width, img_rgba.height, QImage.Format_RGBA8888)
    pm = QPixmap.fromImage(qimg)
    return pm


def pil_image_2_qimage(img: Image.Image) -> QImage:
    img_rgba = img.convert('RGBA')
    data = img_rgba.tobytes('raw', 'RGBA')
    qimg = QImage(data, img_rgba.width, img_rgba.height, QImage.Format_RGBA8888)
    return qimg.copy()


def resize_pil_image(img: Image.Image, width: int, height: int = None) -> Image.Image:
    if height is None:
        height = int(width * (img.size[1] / img.size[0]))
    return img.resize((width, height), resample=Image.Resampling.LANCZOS)


def rotate_pil_image(img: Image.Image, angle: float) -> Image.Image:
    return img.rotate(angle, Image.Resampling.BICUBIC, expand=True,
                      fillcolor=(0, 0, 0, 0))


def pil_image_2_qcursor(img: Image.Image,
                         hotspot_x: int | None = None,
                         hotspot_y: int | None = None) -> QCursor:
    if hotspot_x is None:
        hotspot_x = img.width // 2
    if hotspot_y is None:
        hotspot_y = img.height // 2
    pm = pil_image_2_qpixmap(img)
    return QCursor(pm, hotspot_x, hotspot_y)
