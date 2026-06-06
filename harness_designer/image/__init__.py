# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Lazy image and cursor loading helpers for :mod:`harness_designer.image`."""

from typing import TYPE_CHECKING

import sys
import os
from PIL import Image as _Image

from . import utils

from PySide6.QtGui import QPixmap, QCursor


BASE_PATH = os.path.dirname(__file__)


class Image:
    """Represent a PNG-backed asset that can be converted on demand.

    :param name: Logical asset name.
    :type name: str
    :param path: Optional filesystem path to a PNG asset.
    :type path: str | None
    :param png_data: Optional in-memory PNG bytes.
    :type png_data: bytes | None
    """

    def __init__(self, name, path=None, png_data=None):
        """Initialize an image wrapper.

        :param name: Logical asset name.
        :type name: str
        :param path: Optional filesystem path to a PNG asset.
        :type path: str | None
        :param png_data: Optional in-memory PNG bytes.
        :type png_data: bytes | None
        """
        self._path = path
        self._png_data = png_data
        self.name = name

    @property
    def png_data(self):
        """Return the PNG bytes for the image.

        :returns: Cached PNG data or bytes read from :attr:`_path`.
        :rtype: bytes
        :raises OSError: Raised when the backing file cannot be read.
        """
        if self._png_data is not None:
            return self._png_data

        with open(self._path, 'rb') as f:
            return f.read()

    @property
    def pil(self) -> _Image.Image:
        """Return the image as a PIL ``RGBA`` image.

        :returns: PIL image decoded from :attr:`png_data`.
        :rtype: PIL.Image.Image
        """
        return utils.bytes_data_2_pil_image(self.png_data)

    # Kept for any callers that still use .pil_image (alias)
    @property
    def pil_image(self) -> _Image.Image:
        """Return the image as a PIL image alias.

        :returns: Same value as :attr:`pil`.
        :rtype: PIL.Image.Image
        """
        return self.pil

    @property
    def pixmap(self) -> QPixmap:
        """Return the image as a Qt pixmap.

        :returns: Pixmap created from :attr:`png_data`.
        :rtype: :class:`PySide6.QtGui.QPixmap`
        """
        return utils.bytes_data_2_qpixmap(self.png_data)

    @property
    def disabled_pixmap(self) -> QPixmap:
        """Return a greyscale, lower-opacity pixmap for disabled UI states.

        :returns: Disabled-state pixmap.
        :rtype: :class:`PySide6.QtGui.QPixmap`
        """
        pil = self.pil.convert('RGBA')
        r, g, b, a = pil.split()

        # Convert to greyscale and halve opacity to simulate a disabled icon
        grey = _Image.merge('RGBA', [r, g, b, a])
        grey = grey.convert('LA').convert('RGBA')
        r2, g2, b2, a2 = grey.split()

        a2 = a2.point(lambda p: p // 2)
        disabled = _Image.merge('RGBA', [r2, g2, b2, a2])
        return utils.pil_image_2_qpixmap(disabled)

    @property
    def cursor(self) -> QCursor:
        """Return the image as a centered Qt cursor.

        :returns: Cursor created from :attr:`pil`.
        :rtype: :class:`PySide6.QtGui.QCursor`
        """
        return utils.pil_image_2_qcursor(self.pil)

    def crop(self, x1, y1, x2, y2):
        """Return a cropped copy of the image.

        :param x1: Left crop coordinate.
        :type x1: int
        :param y1: Top crop coordinate.
        :type y1: int
        :param x2: Right crop coordinate.
        :type x2: int
        :param y2: Bottom crop coordinate.
        :type y2: int
        :returns: New image containing the cropped region.
        :rtype: :class:`Image`
        """
        pil = self.pil.convert('RGBA')
        pil = pil.crop((x1, y1, x2, y2))
        return Image(self.name, png_data=utils.pil_image_2_png_bytes(pil))

    def resize(self, w: int, h: int) -> "Image":
        """Return a resized copy of the image.

        :param w: Target width in pixels.
        :type w: int
        :param h: Target height in pixels.
        :type h: int
        :returns: New resized image.
        :rtype: :class:`Image`
        """
        pil = utils.resize_pil_image(self.pil, w, h)
        return Image(self.name, png_data=utils.pil_image_2_png_bytes(pil))

    def rotate(self, angle: int | float) -> "Image":
        """Return a rotated copy of the image.

        :param angle: Rotation angle in degrees.
        :type angle: int | float
        :returns: New rotated image.
        :rtype: :class:`Image`
        """
        pil = utils.rotate_pil_image(self.pil, angle)
        return Image(self.name, png_data=utils.pil_image_2_png_bytes(pil))

    def recolor(self, r, g, b):
        """Return a copy of the image with RGB channels replaced.

        The alpha channel of each pixel is preserved.

        :param r: Red channel value.
        :type r: int
        :param g: Green channel value.
        :type g: int
        :param b: Blue channel value.
        :type b: int
        :returns: Recolored image.
        :rtype: :class:`Image`
        """
        img = utils.bytes_data_2_pil_image(self.png_data)

        w, h = img.size
        for y in range(h):
            for x in range(w):
                a = img.getpixel((x, y))[-1]
                img.putpixel((x, y), (r, g, b, a))

        res = Image(self.name, png_data=utils.pil_image_2_png_bytes(img))
        img.close()
        return res

    def __or__(self, other: "Image"):
        """Combine two images using the current ``|`` composition logic.

        A new transparent canvas is created and both images are pasted using the
        method's existing offset calculations. The exact intended layout is
        UNKNOWN beyond the operations implemented here.

        :param other: Image to combine with this image.
        :type other: :class:`Image`
        :returns: Combined image.
        :rtype: :class:`Image`
        """
        img1 = self.pil
        img2 = other.pil

        w1, h1 = img1.size
        w2, h2 = img2.size

        w = w1 + w2

        if h1 > h2:
            h = h1
            img = _Image.new('RGBA', (w, h), (0, 0, 0, 0))
            x_offset = int((h1 - h2) / 2)
            y_offset = w1
            img.paste(img1)
            img.paste(img2, (x_offset, y_offset))
        else:
            h = h2
            img = _Image.new('RGBA', (w, h), (0, 0, 0, 0))
            x_offset = int((h2 - h1) / 2)
            y_offset = w1
            img.paste(img1, (0, y_offset))
            img.paste(img2, (x_offset, 0))

        data = utils.pil_image_2_png_bytes(img)
        img1.close()
        img2.close()
        img.close()

        return Image(f'{self.name}|{other.name}', png_data=data)

    def __add__(self, other: "Image") -> "Image":
        """Composite other on top of self (centred), both as PIL images."""
        img1 = self.pil
        img2 = other.pil

        w1, h1 = img1.size
        w2, h2 = img2.size

        x_offset = (w1 - w2) // 2 if w1 != w2 else 0
        y_offset = (h1 - h2) // 2 if h1 != h2 else 0

        result = img1.copy()
        result.paste(img2, (x_offset, y_offset), mask=img2)

        data = utils.pil_image_2_png_bytes(result)
        img1.close()
        img2.close()
        result.close()

        return Image(f'{self.name}+{other.name}', png_data=data)


# This is a dynamic loader that acts like a module.
# Done to save memory by only loading icons/images that are actually used.
class ImageLoader:
    """Lazily expose subdirectories and PNG assets as attributes.

    :param path: Base directory to expose.
    :type path: str
    """

    def __init__(self, path):
        """Initialize the lazy image loader.

        When ``path`` matches :data:`BASE_PATH`, the loader replaces the module
        object in :data:`sys.modules` so package attributes resolve lazily.

        :param path: Base directory to expose.
        :type path: str
        """
        mod = sys.modules[__name__]

        if path == BASE_PATH:
            self.__dict__['__name__'] = __name__
            self.__dict__['__file__'] = mod.__file__
            self.__dict__['__package__'] = mod.__package__
            self.__dict__['__doc__'] = mod.__doc__
            self.__dict__['__loader__'] = mod.__loader__
            self.__dict__['__spec__'] = mod.__spec__
            self.__dict__['__path__'] = mod.__path__
            self.__dict__['___cached__'] = mod.__cached__

            sys.modules[__name__] = self
        else:
            self.__name__ = os.path.split(path)[-1]

        self.__dict__['__original_module__'] = mod

        self.__base_path__ = path

    def __getattr__(self, item):
        """Load a sub-loader or :class:`Image` on first attribute access.

        :param item: Attribute name to resolve.
        :type item: str
        :returns: Existing module attribute, nested :class:`ImageLoader`, or :class:`Image`.
        :rtype: object
        :raises AttributeError: Raised when no matching directory or PNG exists.
        """
        if item in self.__dict__:
            return self.__dict__[item]

        if hasattr(self.__original_module__, item):
            return getattr(self.__original_module__, item)

        path_ = os.path.join(self.__base_path__, item)

        if os.path.isdir(path_):
            attr = ImageLoader(path_)
            setattr(self, item, attr)
            return attr

        path_ += '.png'

        if os.path.exists(path_):
            attr = Image(item, path_)
            setattr(self, item, attr)
            return attr

        raise AttributeError(item)


__base = ImageLoader(BASE_PATH)


if TYPE_CHECKING:

    class ip:
        """Type-checking namespace for IP rating images."""
        IP1X: Image = ...
        IP2X: Image = ...
        IP3X: Image = ...
        IP4X: Image = ...
        IP5X: Image = ...
        IP6X: Image = ...
        IPX1: Image = ...
        IPX2: Image = ...
        IPX3: Image = ...
        IPX4: Image = ...
        IPX5: Image = ...
        IPX6: Image = ...
        IPX6K: Image = ...
        IPX7: Image = ...
        IPX8: Image = ...
        IPX9: Image = ...
        IPX9K: Image = ...

    class cursors(ImageLoader):
        """Type-checking namespace for cursor images."""
        back_angle: Image = ...
        forward_angle: Image = ...
        left_bottom_corner_rotate: Image = ...
        left_right: Image = ...
        left_top_corner_rotate: Image = ...
        move: Image = ...
        pointer: Image = ...
        right_bottom_corner_rotate: Image = ...
        right_top_corner_rotate: Image = ...
        rotate: Image = ...
        up_down: Image = ...

    class icons(ImageLoader):
        """Type-checking namespace for icon assets."""
        align_horizontal_center: Image = ...
        align_left_edge: Image = ...
        align_right_edge: Image = ...
        align_top_edge: Image = ...
        align_vertical_center: Image = ...
        aling_bottom_edge: Image = ...
        aspect_ratio: Image = ...
        bom: Image = ...
        bundle_cover: Image = ...
        camera: Image = ...
        checkbox: Image = ...
        circle: Image = ...
        connect: Image = ...
        connector: Image = ...
        cpa_lock: Image = ...
        cover: Image = ...
        crop: Image = ...
        cut: Image = ...
        duplicate: Image = ...
        eraser: Image = ...
        file_3ds: Image = ...
        file_import_3d: Image = ...
        flashlight: Image = ...
        flip: Image = ...
        flip_horizontal: Image = ...
        flip_vertical: Image = ...
        flip_x: Image = ...
        flip_y: Image = ...
        flip_z: Image = ...
        hor_vert: Image = ...
        hor_vert_ang: Image = ...
        internet: Image = ...
        layers: Image = ...
        lighting: Image = ...
        light_bulb: Image = ...
        lock: Image = ...
        mip_mapping: Image = ...
        move: Image = ...
        move_x: Image = ...
        move_y: Image = ...
        move_z: Image = ...
        normals: Image = ...
        notes: Image = ...
        note_pen: Image = ...
        rotate: Image = ...
        rotate_camera: Image = ...
        rotate_x: Image = ...
        rotate_y: Image = ...
        rotate_z: Image = ...
        run_script: Image = ...
        scale: Image = ...
        scale_x: Image = ...
        scale_y: Image = ...
        scale_z: Image = ...
        seal: Image = ...
        select_object: Image = ...
        settings: Image = ...
        show_wireframe: Image = ...
        splice: Image = ...
        spot_light: Image = ...
        square: Image = ...
        stop_script: Image = ...
        subdivide_mesh: Image = ...
        terminal: Image = ...
        tool: Image = ...
        tpa_lock: Image = ...
        transition: Image = ...
        uncheckbox: Image = ...
        unlock: Image = ...
        windows: Image = ...
        wire: Image = ...
        zoom_in: Image = ...
        zoom_out: Image = ...

    class images(ImageLoader):
        """Type-checking namespace for general image assets."""
        header_600x80: Image = ...
        no_image: Image = ...
