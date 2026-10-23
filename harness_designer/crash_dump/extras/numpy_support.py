"""Rendering for ``numpy.ndarray`` -- the only place in crash_dump that
ever imports numpy, and only once a value of this type is actually
captured. Large arrays are summarized (shape/dtype + a bounded preview)
rather than enumerated element by element.
"""
from __future__ import annotations

from ... import check_types as _check_types

_MAX_PREVIEW_ITEMS = 20


@_check_types.do
def render(value):
    flat = value.ravel()
    preview = [item.item() for item in flat[:_MAX_PREVIEW_ITEMS]]
    summary = {
        'shape': list(value.shape),
        'dtype': str(value.dtype),
        'preview': preview,
        'truncated': bool(flat.size > _MAX_PREVIEW_ITEMS),
    }
    return ('value', summary)
