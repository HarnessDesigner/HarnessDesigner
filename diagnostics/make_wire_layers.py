# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generate the layered wire-preview PNGs for twisted pairs / triples, jackets, braid shields and coax.

Usage::

    python diagnostics/make_wire_layers.py [output_dir]

``output_dir`` defaults to ``harness_designer/image/images``. Only the new layers are written (``twisted2_*``,
``twisted3_*``, ``cable_*``, ``coax_*``); ``wire_base`` / ``wire_stripe`` / ``wire_conductor`` / ``wire_shadow`` are
never touched. The files are assembled by ``harness_designer/image/wire_images.py``, which holds the layout numbers
(where the jacket and braid end, where the conductors come out) that this script's geometry has to match.

Same conventions as the ``wire_*`` layers: 400 x 100 RGBA, colour layers are WHITE masks the app recolours, shadow
layers are BLACK with alpha only, the left edge is a flat cut, the insulation ends at x = 300 and the bare
conductors continue to the right edge. Everything is drawn at 4x and averaged down for smooth edges.

Twisted wires: each conductor is a swept sphere (an exact tube) drawn into a z-buffer, so the masks already have the
crossings cut out and the layers never overlap; their draw order does not matter. A stripe is pinned to its conductor's
own frame, which turns with the conductor's orbit (a rigid twist), so it shows as a helix and is visible about half
the time. There is one base, stripe and bare-core layer per conductor so any conductor can be striped or not.

Only needs numpy and Pillow, and imports nothing from the app (importing ``harness_designer`` opens the real config).
"""

import os
import sys

import numpy as np
from PIL import Image, ImageFilter

WIDTH, HEIGHT, SUPERSAMPLE = 400, 100, 4

_XS = (np.arange(WIDTH * SUPERSAMPLE) + 0.5) / SUPERSAMPLE
_YS = (np.arange(HEIGHT * SUPERSAMPLE) + 0.5) / SUPERSAMPLE

_out_dir = ''


def _down(a: np.ndarray) -> np.ndarray:
    """Average a (HEIGHT * SUPERSAMPLE, WIDTH * SUPERSAMPLE) array down to (HEIGHT, WIDTH)."""
    return a.reshape(HEIGHT, SUPERSAMPLE, WIDTH, SUPERSAMPLE).mean(axis=(1, 3))


def _save(name: str, alpha: np.ndarray, black: bool = False) -> None:
    """Write ``name``.png: white (or black) RGB with ``alpha`` (0..255) as its alpha channel."""
    arr = np.zeros((HEIGHT, WIDTH, 4), np.uint8)
    arr[..., 0:3] = 0 if black else 255
    arr[..., 3] = np.clip(np.rint(alpha), 0, 255).astype(np.uint8)
    Image.fromarray(arr, 'RGBA').save(os.path.join(_out_dir, name + '.png'))


def _wrap(a: np.ndarray) -> np.ndarray:
    """Wrap an angle (or an array of them) into -pi..pi."""
    return (a + np.pi) % (2 * np.pi) - np.pi


def make_twisted(count: int, prefix: str, diameter: float, orbit: float, lay: float, end_phases: list[float],
                 insulation_end: int = 300, stripe_half_width: float = 0.30) -> None:
    """Write the layer set for ``count`` twisted conductors.

    :param count: Number of conductors.
    :param prefix: File name prefix (``twisted2``).
    :param diameter: Diameter of one conductor in px.
    :param orbit: Distance of a conductor's centre from the cable axis in px.
    :param lay: Length of one full twist in px.
    :param end_phases: Orbital angle of each conductor at the end of the insulation; they set where the bare ends leave.
    :param insulation_end: x where the insulation is cut.
    :param stripe_half_width: Half the angular width of a stripe in radians.
    """
    r = diameter / 2.0
    shape = (HEIGHT * SUPERSAMPLE, WIDTH * SUPERSAMPLE)
    zbuf = np.full(shape, -1e9)
    ids = np.full(shape, -1, np.int8)
    dy_rel = np.zeros(shape, np.float32)
    azimuth = np.zeros(shape, np.float32)
    omega = np.zeros(shape, np.float32)

    for i in range(count):
        for x in np.arange(-r - 1.0, insulation_end + r + 1.0, 0.4):
            phi = end_phases[i] + 2 * np.pi * (x - insulation_end) / lay
            yc = 50.0 + orbit * np.sin(phi)
            zc = orbit * np.cos(phi)

            ix0 = max(int((x - r) * SUPERSAMPLE), 0)
            ix1 = min(int(np.ceil((x + r) * SUPERSAMPLE)), WIDTH * SUPERSAMPLE)
            iy0 = max(int((yc - r) * SUPERSAMPLE), 0)
            iy1 = min(int(np.ceil((yc + r) * SUPERSAMPLE)), HEIGHT * SUPERSAMPLE)
            if ix0 >= ix1 or iy0 >= iy1:
                continue

            dx = _XS[ix0:ix1][None, :] - x
            dy = _YS[iy0:iy1][:, None] - yc
            rr = r * r - dx * dx - dy * dy
            inside = rr > 0
            dz = np.sqrt(np.where(inside, rr, 0.0))
            z = zc + dz

            win = (slice(iy0, iy1), slice(ix0, ix1))
            upd = inside & (z > zbuf[win])
            zbuf[win] = np.where(upd, z, zbuf[win])
            ids[win] = np.where(upd, i, ids[win])
            dy_rel[win] = np.where(upd, dy / r, dy_rel[win])
            azimuth[win] = np.where(upd, np.arctan2(dz, dy), azimuth[win])
            omega[win] = np.where(upd, np.pi / 2 - phi, omega[win])

    cut = (_XS < insulation_end)[None, :]
    base_alpha = []
    for i in range(count):
        visible = (ids == i) & cut
        stripe = visible & (np.abs(_wrap(azimuth - omega)) < stripe_half_width)
        base_alpha.append(_down(visible.astype(float)))
        _save(f'{prefix}_base_{i + 1}', base_alpha[-1] * 255)
        _save(f'{prefix}_stripe_{i + 1}', _down(stripe.astype(float)) * 255)

    # shadow: linear edge darkening like wire_shadow.png, plus occlusion where one wire lies against another
    visible = (ids >= 0) & cut
    shadow = _down(np.where(visible, 150.0 * np.abs(dy_rel), 0.0))
    for j in range(count):
        others = np.zeros((HEIGHT, WIDTH))
        for k in range(count):
            if k != j:
                others = np.maximum(others, base_alpha[k])
        blurred = np.array(Image.fromarray((others * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5))) / 255.0
        shadow += base_alpha[j] * blurred * 120.0

    # bare conductors: a straight stub from each conductor's end position to the right edge
    core_half = diameter * 0.125
    for i in range(count):
        yc = 50.0 + orbit * np.sin(end_phases[i])
        stub = (_XS >= insulation_end)[None, :] & (np.abs(_YS - yc) < core_half)[:, None]
        _save(f'{prefix}_conductor_{i + 1}', _down(stub.astype(float)) * 255)
        shadow += _down(np.where(stub, 64.0 * np.abs((_YS - yc)[:, None] / core_half), 0.0))

    _save(f'{prefix}_shadow', shadow, black=True)


def make_jacket(name: str, x_end: int) -> None:
    """Write a plain outer jacket tube from x = 0 to ``x_end`` (full height) and its shadow layer."""
    sel = (_XS < x_end)[None, :] & np.ones((HEIGHT * SUPERSAMPLE, 1), bool)
    _save(name, _down(sel.astype(float)) * 255)

    u = np.abs(_YS - 50.0)[:, None] / 50.0
    a = 150.0 * u + np.where((_XS >= x_end - 3)[None, :], 90.0, 0.0)
    _save(name + '_shadow', _down(np.where(sel, a, 0.0)), black=True)


def make_shield(name: str, diameter: float, x0: float, x_end: float, jacket_end: float, spacing: float) -> None:
    """Write an exposed braid from ``x0`` to ``x_end`` as an opaque tube; the weave is drawn in its shadow layer.

    :param name: File name of the mask (the shadow is ``name`` + ``_shadow``).
    :param diameter: Diameter of the braid in px.
    :param x0: Left end of the braid (hidden under the jacket when there is one).
    :param x_end: Right end of the braid.
    :param jacket_end: Where the jacket ends; the braid is darkened just past it. Use a negative value for no jacket.
    :param spacing: Distance between strands in px.
    """
    radius = diameter / 2.0
    sel = (_XS >= x0)[None, :] & (_XS < x_end)[None, :] & (np.abs(_YS - 50.0) < radius)[:, None]
    _save(name, _down(sel.astype(float)) * 255)

    u = np.clip((_YS - 50.0)[:, None] / radius, -0.999, 0.999)
    arc = radius * np.arcsin(u)
    pa = (_XS[None, :] - arc) / spacing
    pb = (_XS[None, :] + arc) / spacing
    fa, fb = pa % 1.0, pb % 1.0
    a_on, b_on = fa < 0.62, fb < 0.62
    a_top = ((np.floor(pa) + np.floor(pb)) % 2) == 0

    weave = np.where(a_on & b_on, 40.0, np.where(a_on | b_on, 0.0, 135.0))
    under = (a_on & b_on) & ~((a_top & (fa > fb)) | (~a_top & (fb > fa)))
    weave = np.where(under, 75.0, weave)
    edge = np.where(a_on & ~b_on, 55.0 * (np.abs(fa / 0.62 - 0.5) * 2) ** 3, 0.0)
    edge += np.where(b_on & ~a_on, 55.0 * (np.abs(fb / 0.62 - 0.5) * 2) ** 3, 0.0)

    a = 150.0 * np.abs(u) + weave + edge
    lip = np.clip((jacket_end + 10 - _XS) / 10.0, 0.0, 1.0)[None, :] * (_XS >= jacket_end)[None, :]
    a = a + 110.0 * lip ** 2
    a = a + np.where((_XS >= x_end - 2)[None, :], 100.0, 0.0)
    _save(name + '_shadow', _down(np.where(sel, a, 0.0)), black=True)


def main(out_dir: str) -> None:
    """Write every layer into ``out_dir``."""
    global _out_dir
    _out_dir = out_dir
    os.makedirs(out_dir, exist_ok=True)

    # a pair's wires meet at +-orbit at the cut (side by side); a triple's three fan out at 0 and +-0.87 orbit
    make_twisted(2, 'twisted2', diameter=50, orbit=25, lay=170, end_phases=[np.pi / 2, 3 * np.pi / 2])

    # three touching conductors: the whole cable is 4.309 conductor radii across, and it is drawn 100 px across
    r3 = 100 / 4.309
    make_twisted(3, 'twisted3', diameter=2 * r3, orbit=1.1547 * r3, lay=230,
                 end_phases=[0.0, 2 * np.pi / 3, 4 * np.pi / 3])

    make_jacket('cable_jacket', 170)
    make_shield('cable_shield', 84, 155, 235, 170, 7.0)
    make_shield('cable_shield_bare', 84, 0, 235, -100, 7.0)  # a shielded cable with no jacket: braid to the left edge
    make_jacket('coax_jacket', 140)
    make_shield('coax_shield', 62, 125, 215, 140, 6.0)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'harness_designer', 'image', 'images'))
    print('done')
