# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Layered preview images of multi-conductor and coax cables.

One :class:`~harness_designer.image.Image` subclass per kind of cable, each of which knows how to assemble its own
picture from the PNG layers in ``image/images``:

* :class:`TwistedWireImage`: a twisted pair or triple, bare or in a jacket and / or braid shield;
* :class:`CableImage`: one to three straight conductors in a jacket and / or braid shield;
* :class:`CoaxImage`: a stripped coax end (jacket, braid, dielectric, centre conductor).

Everything else in this module is private. The layer files are made by ``diagnostics/make_wire_layers.py`` and the
layout numbers below must stay in step with it. Every colour layer is a white mask that is recoloured here, every
shadow layer is black with alpha only; all are 400 x 100 with the left edge a flat cut and the insulation ending at
x = 300, like ``wire_base`` / ``wire_stripe`` / ``wire_conductor`` / ``wire_shadow``.

Layers are combined with true alpha compositing (``Image.alpha_composite``), not ``Image.__add__`` (a masked paste), so
the soft edges where two twisted wires cross do not pick up the colour of the layer underneath.

The layers are read straight from the ``images`` folder next to this file (and kept), not through the lazy image
loader. The classes cache themselves: the same colours give the same image (``_CableImageMeta``, the metaclass pattern
of ``ColorMeta``), and the cache keeps its images, so scrolling a list of wires never draws one twice; callers just
create one.

This module is imported on demand (``from ...image import wire_images``), not by ``image/__init__.py``: the classes
subclass ``Image``, which only exists once ``__init__`` has run.
"""

import functools
import os
import threading
from typing import TYPE_CHECKING, Any, NamedTuple, Union as _Union

import numpy as np
from PIL import Image as _PilImage

from . import Image
from . import utils
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.global_db import color as _color


_Rgb = tuple[int, int, int]

_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')

_WIDTH = 400
_HEIGHT = 100

# x of the end of the insulation in every layer image
_INSULATION_END = 300

# Layout of a jacketed cable (straight conductors, or a twisted group): jacket 0..170, exposed braid 155..235, the
# conductors come out of the braid and end at x = 350 / 360 with their bare ends running to the edge.
_TWISTED_GROUP_SCALE = 0.84  # a twisted pair / triple image is 100 px across, scaled down to the braid's 84 px
_TWISTED_GROUP_END = 350
_STRAIGHT_GROUP_END = 360
# a straight conductor is stretched to the left, under the jacket, from here
_STRAIGHT_GROUP_START = 140

# Coax: jacket 0..140, braid 125..215, dielectric and the centre conductor are the plain wire image scaled down
_COAX_INNER_SCALE = 0.52
_COAX_INNER_END = 335

# (scale, vertical offsets from the centre) of 1, 2 and 3 straight conductors inside a jacket. Three: two behind and
# one in front, drawn last.
_STRAIGHT_LAYOUT = {
    1: (0.5, (0.0,)),
    2: (0.42, (-21.0, 21.0)),
    3: (0.39, (-19.5, 19.5, 0.0)),
}

# at most this many conductors are drawn
_MAX_CONDUCTORS = 3


class _Look(NamedTuple):
    """The colours of one conductor: its insulation, an optional stripe and its bare core."""

    base: _Rgb
    stripe: _Rgb | None
    core: _Rgb


@functools.lru_cache(maxsize=None)
@_check_types.do
def _layer(name: str) -> _PilImage.Image:
    """Return the RGBA image of the layer file ``name`` (no extension) in ``image/images``, read once and kept.

    The returned image is shared: never draw on it.

    :param name: File name without the extension.
    :type name: str
    :returns: RGBA image.
    :rtype: PIL.Image.Image
    """
    with _PilImage.open(os.path.join(_IMAGES_DIR, name + '.png')) as f:
        return f.convert('RGBA')


@_check_types.do
def _rgb(color: "_color.Color") -> _Rgb:
    """Return a :class:`Color` as a plain ``(r, g, b)`` tuple.

    :param color: Colour to convert.
    :type color: :class:`Color`
    :returns: Red, green and blue, 0 to 255 each.
    :rtype: tuple[int, int, int]
    """
    ui = color.ui
    return ui.GetRed(), ui.GetGreen(), ui.GetBlue()


@_check_types.do
def _rgb_or_none(color: _Union["_color.Color", None]) -> _Rgb | None:
    """Return :func:`_rgb` of ``color``, or ``None`` for ``None``.

    :param color: Colour or ``None``.
    :type color: :class:`Color` | None
    :returns: ``(r, g, b)`` or ``None``.
    :rtype: tuple[int, int, int] | None
    """
    return None if color is None else _rgb(color)


@_check_types.do
def _looks(conductors: list[tuple]) -> list[_Look]:
    """Turn ``(base, stripe or None, core)`` colour tuples into looks; only the first three are kept.

    :param conductors: One tuple of :class:`Color` per conductor: insulation, stripe (or ``None``), bare core.
    :type conductors: list[tuple]
    :returns: The same colours as RGB tuples.
    :rtype: list[_Look]
    """
    return [_Look(_rgb(base), _rgb_or_none(stripe), _rgb(core)) for base, stripe, core in conductors[:_MAX_CONDUCTORS]]


@_check_types.do
def _recolor(layer: _PilImage.Image, rgb: _Rgb) -> _PilImage.Image:
    """Return ``layer`` with its RGB replaced and its alpha kept.

    :param layer: RGBA mask.
    :type layer: PIL.Image.Image
    :param rgb: Colour to paint the mask.
    :type rgb: tuple[int, int, int]
    :returns: Recoloured copy.
    :rtype: PIL.Image.Image
    """
    arr = np.array(layer)
    arr[..., 0] = rgb[0]
    arr[..., 1] = rgb[1]
    arr[..., 2] = rgb[2]
    return _PilImage.fromarray(arr, 'RGBA')


@_check_types.do
def _over(*layers: _PilImage.Image) -> _PilImage.Image:
    """Alpha-composite the layers in order, the first one at the bottom.

    :param layers: RGBA images of the same size.
    :type layers: PIL.Image.Image
    :returns: The composite.
    :rtype: PIL.Image.Image
    """
    result = layers[0].copy()
    for layer in layers[1:]:
        result = _PilImage.alpha_composite(result, layer)
    return result


@_check_types.do
def _single_wire(look: _Look) -> _PilImage.Image:
    """Return the plain single-wire image (base, stripe, bare core, shadow) for one conductor.

    :param look: Colours of the conductor.
    :type look: _Look
    :returns: 400 x 100 image.
    :rtype: PIL.Image.Image
    """
    layers = [_recolor(_layer('wire_base'), look.base)]

    if look.stripe is not None:
        layers.append(_recolor(_layer('wire_stripe'), look.stripe))

    layers.append(_recolor(_layer('wire_conductor'), look.core))
    layers.append(_layer('wire_shadow'))
    return _over(*layers)


@_check_types.do
def _twisted_wires(looks: list[_Look]) -> _PilImage.Image:
    """Return a twisted pair (2 looks) or triple (3 looks).

    Each conductor has its own base, stripe and bare-core layer, so any wire can be striped or not, in any colour. The
    layers are already cut where the wires cross, so their order does not matter.

    :param looks: Colours of the conductors, in order.
    :type looks: list[_Look]
    :returns: 400 x 100 image.
    :rtype: PIL.Image.Image
    :raises ValueError: Fewer than two conductors.
    """
    if len(looks) < 2:
        raise ValueError('a twisted cable needs at least two conductors')

    prefix = f'twisted{len(looks)}'

    layers = [_recolor(_layer(f'{prefix}_base_{i + 1}'), look.base) for i, look in enumerate(looks)]
    layers += [_recolor(_layer(f'{prefix}_stripe_{i + 1}'), look.stripe)
               for i, look in enumerate(looks) if look.stripe is not None]
    layers += [_recolor(_layer(f'{prefix}_conductor_{i + 1}'), look.core) for i, look in enumerate(looks)]
    layers.append(_layer(f'{prefix}_shadow'))
    return _over(*layers)


@_check_types.do
def _place(image: _PilImage.Image, scale: float, insulation_end: float, y_center: float = 50.0) -> _PilImage.Image:
    """Scale a 400 x 100 wire image and put the end of its insulation at ``insulation_end``.

    The result is a transparent 400 x 100 canvas; whatever falls outside it is cropped.

    :param image: Wire image.
    :type image: PIL.Image.Image
    :param scale: Uniform scale factor.
    :type scale: float
    :param insulation_end: x on the canvas where the insulation (x = 300 in ``image``) should end.
    :type insulation_end: float
    :param y_center: y on the canvas where the wire's centre line goes.
    :type y_center: float
    :returns: 400 x 100 image.
    :rtype: PIL.Image.Image
    """
    w = max(1, round(_WIDTH * scale))
    h = max(1, round(_HEIGHT * scale))
    small = image.resize((w, h), _PilImage.Resampling.LANCZOS)

    left = round(insulation_end - _INSULATION_END * scale)
    top = round(y_center - h / 2)

    if left < 0:
        small = small.crop((-left, 0, w, h))
        left = 0

    canvas = _PilImage.new('RGBA', (_WIDTH, _HEIGHT), (0, 0, 0, 0))
    canvas.alpha_composite(small, (left, max(top, 0)), (0, max(-top, 0)))
    return canvas


@_check_types.do
def _straight_group(looks: list[_Look]) -> _PilImage.Image:
    """Return one to three plain conductors side by side, scaled to fit a jacket, running in from under the jacket.

    Each conductor is the ordinary single-wire image scaled down. Its insulation is lengthened to the left by
    repeating its first column (taken from a copy without the stripe, so the stripe is not smeared).

    :param looks: Colours of the conductors.
    :type looks: list[_Look]
    :returns: 400 x 100 image.
    :rtype: PIL.Image.Image
    """
    scale, offsets = _STRAIGHT_LAYOUT[len(looks)]
    end = _STRAIGHT_GROUP_END
    left = round(end - _INSULATION_END * scale)

    result = _PilImage.new('RGBA', (_WIDTH, _HEIGHT), (0, 0, 0, 0))
    for look, offset in zip(looks, offsets):
        y = 50.0 + offset
        plain = _place(_single_wire(_Look(look.base, None, look.core)), scale, end, y)
        full = _place(_single_wire(look), scale, end, y)

        arr = np.array(plain)
        filler = np.zeros_like(arr)
        filler[:, _STRAIGHT_GROUP_START:left + 1, :] = arr[:, left + 1:left + 2, :]

        result = _over(result, _PilImage.fromarray(filler, 'RGBA'), full)

    return result


@_check_types.do
def _jacketed(group: _PilImage.Image, jacket: _Rgb | None, shield: _Rgb | None) -> _PilImage.Image:
    """Lay a braid shield and an outer jacket over the conductor group.

    A shield with no jacket is the braid alone, running to the left edge. A jacket with no shield stops at x = 170
    and the conductors come straight out of it.

    :param group: The conductors (from :func:`_straight_group` or a scaled :func:`_twisted_wires`).
    :type group: PIL.Image.Image
    :param jacket: Jacket colour, or ``None`` for no jacket.
    :type jacket: tuple[int, int, int] | None
    :param shield: Colour of the shield braid, or ``None`` for no shield.
    :type shield: tuple[int, int, int] | None
    :returns: 400 x 100 image.
    :rtype: PIL.Image.Image
    """
    layers = [group]

    if shield is not None:
        name = 'cable_shield' if jacket is not None else 'cable_shield_bare'
        layers += [_recolor(_layer(name), shield), _layer(name + '_shadow')]

    if jacket is not None:
        layers += [_recolor(_layer('cable_jacket'), jacket), _layer('cable_jacket_shadow')]

    return _over(*layers)


@_check_types.do
def _color_name(color: _Union["_color.Color", None]) -> str | None:
    """Return the name of ``color``, or ``None`` for ``None`` (what a cache key is made of).

    :param color: Colour or ``None``.
    :type color: :class:`Color` | None
    :returns: The colour's name, or ``None``.
    :rtype: str | None
    """
    return None if color is None else color.name


@_check_types.do
def _conductor_names(conductors: list[tuple]) -> tuple:
    """Return the colour names of the first three ``(base, stripe or None, core)`` tuples, for a cache key.

    :param conductors: One tuple of :class:`Color` (or ``None``) per conductor.
    :type conductors: list[tuple]
    :returns: The same tuples with every colour replaced by its name.
    :rtype: tuple
    """
    return tuple(tuple(_color_name(color) for color in conductor) for conductor in conductors[:_MAX_CONDUCTORS])


class _CableImageMeta(type):
    """Metaclass that caches the cable images by the colours they are made of, like ``ColorMeta`` and ``_EntrySingleton``.

    Asking for a cable image with the same colours as one already made returns that image instead of drawing it again.
    The cache holds the images themselves (strong references, not weak ones like ``ColorMeta``'s), and it is not
    emptied: an image is a few KB of PNG data, and an image freed while the user scrolls a list of wires would have
    to be drawn again as the row comes back into view. Each class has its own cache and lock. The class says what makes
    two images the same by defining ``_cache_key`` with the signature of its ``__init__``.
    """

    @_check_types.do
    def __init__(cls, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        super().__init__(name, bases, dct)
        # the images are made from the GUI thread and from worker threads, so a lock guards the dict
        cls._instances = {}
        cls._instances_lock = threading.RLock()

    @_check_types.do
    def __call__(cls, *args: Any, **kwargs: Any) -> "_CableImage":
        """Return the image made from the same colours, or make and keep one.

        :param args: The arguments of the class's ``__init__``.
        :param kwargs: The keyword arguments of the class's ``__init__``.
        :returns: A new or cached image.
        :rtype: :class:`_CableImage`
        """
        key = cls._cache_key(*args, **kwargs)

        with cls._instances_lock:
            instance = cls._instances.get(key)

            if instance is None:
                instance = type.__call__(cls, *args, **kwargs)
                cls._instances[key] = instance

        return instance


class _CableImage(Image, metaclass=_CableImageMeta):
    """Base of the cable images: an :class:`Image` whose PNG is made from a finished PIL image.

    A subclass defines ``_cache_key`` (a classmethod taking the arguments of its ``__init__`` and returning a hashable
    key made from colour NAMES), which :class:`_CableImageMeta` uses to share images.
    """

    @classmethod
    def _cache_key(cls, *args: Any, **kwargs: Any) -> tuple:
        raise NotImplementedError

    @_check_types.do
    def __init__(self, name: str, pil: _PilImage.Image):
        """Create the image.

        :param name: Logical asset name.
        :type name: str
        :param pil: The finished picture; it is converted to PNG data and closed.
        :type pil: PIL.Image.Image
        """
        super().__init__(name, png_data=utils.pil_image_2_png_bytes(pil))
        pil.close()


class TwistedWireImage(_CableImage):
    """A twisted pair or triple of wires, bare or inside a jacket and / or a braid shield.

    Each conductor can be striped or not, in its own colour. A wire with no jacket (the "no color" row) gets
    ``jacket_color=None``. More than three conductors draw the first three. The same colours give the same image (see
    :class:`_CableImageMeta`).
    """

    @classmethod
    @_check_types.do
    def _cache_key(cls, conductors: list[tuple], jacket_color: _Union["_color.Color", None] = None,
                   shield_color: _Union["_color.Color", None] = None) -> tuple:
        return _conductor_names(conductors), _color_name(jacket_color), _color_name(shield_color)

    @_check_types.do
    def __init__(self, conductors: list[tuple], jacket_color: _Union["_color.Color", None] = None,
                 shield_color: _Union["_color.Color", None] = None):
        """Assemble the picture.

        :param conductors: One ``(base, stripe or None, core)`` tuple of :class:`Color` per conductor, in order; at
            least two.
        :type conductors: list[tuple]
        :param jacket_color: Jacket colour, or ``None`` for no jacket.
        :type jacket_color: :class:`Color` | None
        :param shield_color: Colour of the braid shield, or ``None`` for no shield.
        :type shield_color: :class:`Color` | None
        :raises ValueError: Fewer than two conductors.
        """
        jacket = _rgb_or_none(jacket_color)
        shield = _rgb_or_none(shield_color)

        twisted = _twisted_wires(_looks(conductors))

        if jacket is None and shield is None:
            pil = twisted
        else:
            pil = _jacketed(_place(twisted, _TWISTED_GROUP_SCALE, _TWISTED_GROUP_END), jacket, shield)

        super().__init__('twisted', pil)


class CableImage(_CableImage):
    """One to three straight (untwisted) conductors inside a jacket and / or a braid shield.

    More than three conductors draw the first three. The same colours give the same image (see
    :class:`_CableImageMeta`).
    """

    @classmethod
    @_check_types.do
    def _cache_key(cls, conductors: list[tuple], jacket_color: _Union["_color.Color", None],
                   shield_color: _Union["_color.Color", None] = None) -> tuple:
        return _conductor_names(conductors), _color_name(jacket_color), _color_name(shield_color)

    @_check_types.do
    def __init__(self, conductors: list[tuple], jacket_color: _Union["_color.Color", None],
                 shield_color: _Union["_color.Color", None] = None):
        """Assemble the picture.

        :param conductors: One ``(base, stripe or None, core)`` tuple of :class:`Color` per conductor, in order; at
            least one.
        :type conductors: list[tuple]
        :param jacket_color: Jacket colour, or ``None`` for no jacket.
        :type jacket_color: :class:`Color` | None
        :param shield_color: Colour of the braid shield, or ``None`` for no shield.
        :type shield_color: :class:`Color` | None
        :raises ValueError: No conductors.
        """
        looks = _looks(conductors)

        if not looks:
            raise ValueError('a cable needs at least one conductor')

        super().__init__('cable', _jacketed(_straight_group(looks), _rgb_or_none(jacket_color),
                                            _rgb_or_none(shield_color)))


class CoaxImage(_CableImage):
    """A stripped coax end: jacket, exposed braid, dielectric and the centre conductor. The same colours give the same
    image (see :class:`_CableImageMeta`)."""

    @classmethod
    @_check_types.do
    def _cache_key(cls, jacket_color: "_color.Color", shield_color: "_color.Color", dielectric_color: "_color.Color",
                   core_color: "_color.Color") -> tuple:
        return (_color_name(jacket_color), _color_name(shield_color), _color_name(dielectric_color),
                _color_name(core_color))

    @_check_types.do
    def __init__(self, jacket_color: "_color.Color", shield_color: "_color.Color", dielectric_color: "_color.Color",
                 core_color: "_color.Color"):
        """Assemble the picture.

        :param jacket_color: Jacket colour.
        :type jacket_color: :class:`Color`
        :param shield_color: Colour of the braid.
        :type shield_color: :class:`Color`
        :param dielectric_color: Colour of the insulation around the centre conductor.
        :type dielectric_color: :class:`Color`
        :param core_color: Colour of the centre conductor.
        :type core_color: :class:`Color`
        """
        inner = _place(_single_wire(_Look(_rgb(dielectric_color), None, _rgb(core_color))),
                       _COAX_INNER_SCALE, _COAX_INNER_END)

        super().__init__('coax', _over(
            inner,
            _recolor(_layer('coax_shield'), _rgb(shield_color)), _layer('coax_shield_shadow'),
            _recolor(_layer('coax_jacket'), _rgb(jacket_color)), _layer('coax_jacket_shadow')))
