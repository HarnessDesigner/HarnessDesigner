# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Segment drag for a bundle in the Peg Board Editor.

Identical mechanics to :mod:`~.wire` -- a ``PJTBundle`` row exposes the
exact same ``start_position_pegboard_id``/``stop_position_pegboard_id``/
``waypoints_pegboard``/``length_mm`` shape a ``PJTWire`` does, and
:class:`~.wire.Wire` never assumes anything more specific than that
shape, so no new logic is needed here at all -- see that module's
docstring for the full rationale (waypoints/ends already covered by
:mod:`~.generic`; a clicked segment's two bounding nodes move together,
rigidly, clamped by the most restrictive of their own outer budgets so
the segment itself never stretches).
"""

from . import wire as _wire


class Bundle(_wire.Wire):
    """Segment drag for a bundle -- identical to :class:`~.wire.Wire`,
    see the module docstring."""
