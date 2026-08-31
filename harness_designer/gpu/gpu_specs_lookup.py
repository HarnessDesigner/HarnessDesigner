# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""GL_RENDERER -> GPU-spec lookup for :mod:`harness_designer.gpu`.

Data source: the ``RightNow-GPU-Database`` project's ``all-gpus.json``
(itself sourced from TechPowerUp's GPU database), filtered to every
AMD/NVIDIA/Intel entry that reports a real, nonzero VRAM size AND a
reported OpenGL version of at least 3.3 -- this app's own minimum (every
shader declares ``#version 330 core``; a GPU below that can't run
harness_designer at all, so its GL_RENDERER string could never actually
appear here) -- 1757 GPUs (791 AMD, 931 NVIDIA, 35 Intel). Every value is a
real reported spec, not a guess. Every name was checked for collisions
against every other name in the source data, both within and across
vendors, before being trusted as a lookup key (none exist).

https://github.com/RightNow-AI/RightNow-GPU-Database/blob/main/data/all-gpus.json

``gpu_table.json`` is organized ``{"AMD": {model name: spec}, "NVIDIA":
{...}, "INTEL": {...}}`` -- manufacturer as the top-level key, both so a
known vendor can jump straight to its bucket instead of scanning all 1757
entries, and so the manufacturer isn't redundantly repeated inside every
one of those 1757 leaf dicts on disk. :func:`lookup` adds it back in
(``gpu_manufacturer``, matching :class:`.backend_base.GPUBackend`'s own
casing -- ``'AMD'``/``'NVIDIA'``/``'Intel'``) on the dict it returns, since
that's a real, useful field for a caller that only has a spec dict in hand
and not the bucket it came from.

Every other dict key in an entry is already a
:class:`.backend_base.GPUBackend` attribute name -- a caller copies a
matched entry straight across with no renaming.
``pcie_version``/``pcie_max_width`` are parsed out of the source data's
``busInterface`` field (e.g. "PCIe 4.0 x16"); entries on a non-PCIe bus
(AGP, MXM, Apple MPX, integrated) have neither key, not a wrong guess.

Used to fill in whatever a live vendor SDK/GL extension couldn't supply
(see :mod:`.gl_meminfo`, :mod:`.manager`) -- gaps only, never overwriting a
real measurement.

All 1757 entries live in ``gpu_table.json`` next to this file, not a Python
dict literal kept resident for the process lifetime -- the GPU installed in
a machine doesn't change while the app is running, so there's nothing to
gain from caching this in memory once :func:`lookup` has returned an
answer. :func:`lookup` opens, parses, searches, and lets the whole thing go
back out of scope in one call; nothing here holds a module-level reference
to any of it, so it's eligible for GC the moment the caller is done with
the single matched entry it actually wanted.
"""

import json
import os

from .. import check_types as _check_types

_JSON_PATH = os.path.join(os.path.dirname(__file__), 'gpu_table.json')

# gpu_table.json top-level key -> the casing GPUBackend.gpu_manufacturer
# actually uses elsewhere (nvidia.py/amd.py set 'NVIDIA'/'AMD' directly;
# apple.py sets 'Apple' -- Title Case is this app's real convention, even
# though the JSON's own top-level keys are plain uppercase for easy reading).
_MANUFACTURER_DISPLAY = {'AMD': 'AMD', 'NVIDIA': 'NVIDIA', 'INTEL': 'Intel'}


@_check_types.do
def lookup(renderer_string: str, manufacturer: str = None):
    """Best-guess GPU spec dict, matched from a GL_RENDERER string.

    :param renderer_string: The raw string returned by
        ``glGetString(GL_RENDERER)``.
    :param manufacturer: Restrict the search to one manufacturer's bucket
        (``'AMD'``, ``'NVIDIA'``, or ``'Intel'``, case-insensitive).
        ``None`` (the default) searches every vendor's bucket -- harmless
        even when the vendor is already known, since a real AMD
        ``GL_RENDERER`` string will never match an NVIDIA/Intel entry, but
        pass it when known to skip the wasted comparisons.
    :returns: The matched model's spec dict (with ``gpu_manufacturer``
        added), or ``None`` if no known model matched (including if the
        JSON file can't be read, or ``manufacturer`` names an unknown
        bucket).
    :rtype: dict | None
    """
    try:
        with open(_JSON_PATH, 'r', encoding='utf-8') as f:
            buckets = json.load(f)
    except Exception:  # NOQA -- missing/unreadable/corrupt file
        return None

    if manufacturer is not None:
        bucket = buckets.get(manufacturer.upper())
        buckets = {manufacturer.upper(): bucket} if bucket is not None else {}

    upper_renderer = renderer_string.upper()

    # Windows drivers commonly render as e.g. "Radeon(TM) RX 6600" or
    # "GeForce RTX(R) 4090" -- the symbol splits what would otherwise be
    # a clean substring match against the table's plain model name.
    for symbol in ('(TM)', '(R)', '(C)'):
        upper_renderer = upper_renderer.replace(symbol, '')

    for bucket_key, specs in buckets.items():
        # Longest keys first, so e.g. "Radeon RX 7900 XTX" is tried before
        # the "Radeon RX 7900 XT" that would also match as a substring of it.
        for key in sorted(specs, key=len, reverse=True):
            if key.upper() in upper_renderer:
                result = dict(specs[key])
                result['gpu_manufacturer'] = _MANUFACTURER_DISPLAY.get(bucket_key, bucket_key)
                return result

    return None
