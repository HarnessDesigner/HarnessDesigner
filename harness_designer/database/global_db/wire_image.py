# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The list icon of a wire's preview picture.

The picture itself is made by ``images.build_wire(row)`` (``harness_designer/image``), the one entry point for wire
images: pass a catalog ``Wire``, a project ``PJTWire`` or a project ``PJTWireServiceLoop`` and it picks the image class
(``WireImage``, ``TwistedWireImage``, ``CableImage``, ``CoaxImage`` or ``WireLoopImage`` of ``image/wire_images.py``).
Those classes cache by how a wire LOOKS (its colours, jacket, shield), never by part number or size, so thousands of
parts share a few hundred pictures. This module only adds :func:`build_wire_icon`, the ``QIcon`` of a picture that lists
share.
"""

from typing import TYPE_CHECKING, Union as _Union

from PySide6 import QtGui

from ... import image as _image
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import wire as _wire
    from ..project_db import pjt_wire as _pjt_wire
    from ..project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from ...image import wire_images as _wire_images


# The icons made from the pictures, by (picture, size). A picture is shared by every wire that LOOKS the same (its
# colours, jacket and shield; the size, series and part number play no part), so an icon is shared the same way:
# thousands of rows of a list show the same few QIcon objects (a QIcon is implicitly shared) instead of one pixmap per
# part. The pictures are held by the image classes' caches for good, so keying by the picture keeps nothing alive that
# was not alive already. GUI thread only: a QPixmap cannot be made anywhere else.
_ICONS: dict[tuple, QtGui.QIcon] = {}


@_check_types.do
def build_wire_icon(
    row: _Union["_wire.Wire", "_pjt_wire.PJTWire", "_pjt_wire_service_loop.PJTWireServiceLoop",
                "_wire_images.WireImageRow"],
    size: int = 64
) -> QtGui.QIcon | None:
    """Return the list icon of a wire (its picture fitted into a ``size`` x ``size`` box), or ``None`` when
    ``images.build_wire(row)`` cannot draw it.

    Wires that look the same get the SAME ``QIcon`` object: it is made once per picture and size, not once per wire.
    Call it from the GUI thread only.

    :param row: The catalog wire, project wire, project wire service loop or, from the parts editor's list, a
        :class:`WireImageRow`.
    :type row: :class:`Wire` | :class:`PJTWire` | :class:`PJTWireServiceLoop` | :class:`WireImageRow`
    :param size: Width and height of the icon in pixels.
    :type size: int
    :returns: The shared icon, or ``None``.
    :rtype: :class:`PySide6.QtGui.QIcon` | None
    """
    image = _image.images.build_wire(row)

    if image is None:
        return None

    key = (image, size)
    icon = _ICONS.get(key)

    if icon is None:
        icon = QtGui.QIcon(image.resize_keep_aspect(size, size).pixmap)
        _ICONS[key] = icon

    return icon
