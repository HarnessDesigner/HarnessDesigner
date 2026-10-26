# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Disk cache for a single expensive build123d/OCCT-tessellated mesh --
shared by every primitive shape module whose geometry is a fixed sweep/
sphere/helix built from scratch via build123d rather than plain numpy
math (shapes/cylinder_helix.py, shapes/arrow.py -- NOT shapes/helix.py,
whose mesh grows with the project's longest wire and so has no single
fixed result to cache). Measured cost building these from scratch:
~35ms (arrow) to ~1.8s (cylinder_helix's stripe) -- real time paid on
every single app launch, even though the result is identical every time
(fixed geometry/tessellation parameters). This caches a mesh's already-
tessellated (packed, count, aabb, obb) VBO-ready data to a single small
``.hdm`` file per cache name (see utils/hdm.py) -- written once, after a
cache miss; every
later launch loads it back and skips the OCCT work entirely (VBO
upload itself still happens fresh every launch -- that needs a live GL
context, and was never the slow part).

shapes/text.py caches its own much larger *set* of glyphs the same way,
but keeps its own bespoke multi-entry version of this logic (see that
module's own _load_glyph_cache/_save_glyph_cache) rather than using
this -- one glyph per (character, style) is a different shape of
caching problem (many small keyed entries) than the single whole-mesh
case here.
"""

import os
import numpy as np

from .. import utils as _utils
from .. import check_types as _check_types


@_check_types.do
def path(name: str) -> str:
    """Return the on-disk path for cache *name* (no extension needed --
    always ``<appdata>/<name>.hdm``)."""
    return os.path.join(_utils.get_appdata(), f'{name}{_utils.HDM_EXTENSION}')


@_check_types.do
def load(name: str, version: int) -> tuple[np.ndarray, int, np.ndarray, np.ndarray, np.ndarray | None] | None:
    """Return ``(packed, count, aabb, obb, extra)`` cached on disk for
    *name*, or ``None`` if there's no cache file yet, it's unreadable,
    or it was written by a different *version*.

    *extra* is whatever small ``float64`` array the caller passed to
    :func:`save` (``None`` if it passed none) -- e.g.
    shapes/cylinder_helix.py uses it to remember ``create_vbo()``'s own
    extra connection-point coordinate, which isn't part of the mesh
    itself.
    """
    cache_path = path(name)

    try:
        # a cache written before the .hdm format is upgraded in place
        _utils.migrate_hdm(cache_path)

        if not os.path.exists(cache_path):
            return None

        data = _utils.load_hdm_arrays(cache_path)

        if int(data['version'][0]) != version:
            return None

        return (data['packed'], int(data['count'][0]),
                data['aabb'], data['obb'], data.get('extra'))
    except Exception:  # NOQA -- any read/format problem just means rebuild
        return None


@_check_types.do
def save(name: str, version: int, packed: np.ndarray, count: int,
         aabb: np.ndarray, obb: np.ndarray, extra: np.ndarray | None = None) -> None:
    """Write *packed*/*count*/*aabb*/*obb* (plus optional small *extra*
    float array) to disk for cache *name*, so the next app launch can
    :func:`load` it back instead of rebuilding. Written to a temp file
    and moved into place with ``os.replace`` so a run interrupted
    mid-save never leaves a corrupt/partial cache file behind for the
    next launch to trip over.
    """
    arrays = {
        'version': np.array([version], dtype=np.int64),
        'packed': packed,
        'count': np.array([count], dtype=np.int64),
        'aabb': aabb,
        'obb': obb,
    }

    if extra is not None:
        arrays['extra'] = np.asarray(extra, dtype=np.float64)

    _utils.save_hdm_arrays(path(name), arrays)
