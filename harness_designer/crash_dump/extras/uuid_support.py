# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Rendering for ``uuid.UUID`` -- imported only once a UUID is actually
captured.
"""

from __future__ import annotations

from ... import check_types as _check_types


@_check_types.do
def render(value):
    return 'value', str(value)
