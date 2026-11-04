# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The preview picture of a catalog wire: one function that decides which image builder a wire needs.

The wire editor, the peg-board wire table, the BOM and the circuit editor all draw a wire's picture; they call
:func:`build_wire_image` (or :func:`build_wire_icon`, the shared list icon) so a wire looks the same everywhere. The
images are keyed by how a wire LOOKS (its colours, jacket, shield), never by part number or size, so thousands of parts
share a few hundred pictures. The images themselves come from
``harness_designer/image``: ``images.build_wire`` for a single wire and the ``TwistedWireImage``, ``CableImage`` and
``CoaxImage`` classes of ``image/wire_images.py`` for everything else (they cache themselves by colour).
"""

from typing import TYPE_CHECKING

from PySide6 import QtGui

from .. import id_generator as _id_generator
from ... import image as _image
from ...image import wire_images as _wire_images
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import wire as _wire
    from . import color as _color


# The catalog has no colour for a coax / cable shield braid or for a coax dielectric, so these are used (the first one
# the colours table has).
_SHIELD_COLOR_NAMES = ('Silver', 'Gray')
_DIELECTRIC_COLOR_NAMES = ('White',)

# at most this many conductors are drawn in a cable
_MAX_DRAWN_CONDUCTORS = 3

# The icons made from the pictures, by (picture, size). A picture is shared by every wire that LOOKS the same (its
# colours, jacket and shield; the size, series and part number play no part), so an icon is shared the same way:
# thousands of rows of a list show the same few QIcon objects (a QIcon is implicitly shared) instead of one pixmap per
# part. The pictures are held by the image classes' caches (and the image loader's) for good, so keying by the picture
# keeps nothing alive that was not alive already. GUI thread only: a QPixmap cannot be made anywhere else.
_ICONS: dict[tuple, QtGui.QIcon] = {}


@_check_types.do
def _named_color(colors_table: object, names: tuple[str, ...]) -> "_color.Color | None":
    """Return the first colour of ``names`` that the colours table has, or ``None``.

    :param colors_table: The ``colors`` table class.
    :type colors_table: object
    :param names: Colour names in order of preference.
    :type names: tuple[str, ...]
    :returns: The colour, or ``None`` when the table has none of them.
    :rtype: :class:`Color` | None
    """
    for name in names:
        try:
            return colors_table[name]
        except (KeyError, IndexError):
            continue

    return None


@_check_types.do
def build_wire_image(wire: "_wire.Wire") -> "_image.Image | None":
    """Return the preview picture of a catalog wire, or ``None`` when it cannot be drawn (the caller then shows
    ``images.no_image``).

    * a single unshielded conductor: the plain wire image (insulation, stripe, bare core);
    * a coax cable (wire type "Coaxial"): jacket, braid, dielectric and centre conductor;
    * a multi-conductor cable: its conductors from the ``wire_conductors`` table, TWISTED (a pair or triple) when the
      wire's ``tpi`` is above 0 and straight otherwise, inside the jacket (``color_id``; the "no color" id means no
      jacket) and, when the wire is shielded, a braid.

    A cable with no ``wire_conductors`` rows cannot be drawn, because its conductors' colours are not known, and the
    "Ribbon" wire type is not drawn yet. At most three conductors are drawn.

    :param wire: The catalog wire.
    :type wire: :class:`Wire`
    :returns: A 400 x 100 image, or ``None``.
    :rtype: :class:`Image` | None
    """
    images = _image.images
    db = wire._table.db  # NOQA

    colors_table = db.colors_table
    platings_table = db.platings_table

    no_color = _id_generator.NO_COLOR_UUID.bytes  # a wire with no jacket / a conductor with no stripe
    nil = _id_generator.NIL_UUID.bytes  # an unset plating; as a colour the nil id is Black, a real colour

    def color_of(color_id: bytes | None) -> "_color.Color | None":
        if color_id is None or color_id == no_color:
            return None

        return colors_table[color_id]

    def core_of(core_id: bytes | None) -> "_color.Color | None":
        if core_id is None or core_id == nil:
            return None

        return platings_table[core_id].color

    wire_type_name = wire.wire_type.name

    if wire_type_name == 'Ribbon':
        return None

    count = wire.num_conductors or 1
    jacket = color_of(wire.color_id)

    if wire_type_name == 'Coaxial':
        core = core_of(wire.core_material_id)
        shield = _named_color(colors_table, _SHIELD_COLOR_NAMES)
        dielectric = _named_color(colors_table, _DIELECTRIC_COLOR_NAMES)

        if jacket is None or core is None or shield is None or dielectric is None:
            return None

        return _wire_images.CoaxImage(jacket, shield, dielectric, core)

    if count == 1 and not wire.shielded:
        core = core_of(wire.core_material_id)

        if jacket is None or core is None:
            return None

        return images.build_wire(jacket, color_of(wire.stripe_color_id), core)

    # everything else needs the individual conductors
    wire_core = core_of(wire.core_material_id)
    conductors = []

    for conductor in wire.conductors[:_MAX_DRAWN_CONDUCTORS]:
        base = color_of(conductor.color_id)
        core = core_of(conductor.core_material_id)

        if core is None:
            core = wire_core

        if base is None or core is None:
            return None

        conductors.append((base, color_of(conductor.stripe_color_id), core))

    if not conductors:
        return None

    shield = None
    if wire.shielded:
        shield = _named_color(colors_table, _SHIELD_COLOR_NAMES)
        if shield is None:
            return None

    if len(conductors) >= 2 and wire.tpi > 0:
        return _wire_images.TwistedWireImage(conductors, jacket, shield)

    return _wire_images.CableImage(conductors, jacket, shield)


@_check_types.do
def build_wire_icon(wire: "_wire.Wire", size: int = 64) -> QtGui.QIcon | None:
    """Return the list icon of a catalog wire (its picture fitted into a ``size`` x ``size`` box), or ``None`` when
    :func:`build_wire_image` cannot draw it.

    Wires that look the same get the SAME ``QIcon`` object: it is made once per picture and size, not once per wire.
    Call it from the GUI thread only.

    :param wire: The catalog wire.
    :type wire: :class:`Wire`
    :param size: Width and height of the icon in pixels.
    :type size: int
    :returns: The shared icon, or ``None``.
    :rtype: :class:`PySide6.QtGui.QIcon` | None
    """
    image = build_wire_image(wire)

    if image is None:
        return None

    key = (image, size)
    icon = _ICONS.get(key)

    if icon is None:
        icon = QtGui.QIcon(image.resize_keep_aspect(size, size).pixmap)
        _ICONS[key] = icon

    return icon
