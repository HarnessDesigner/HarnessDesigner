# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared classes/helpers reused by the object-owned add-handler system
(``add_handlers``) and by ``objects.*``'s own ``start_add`` classmethods
-- every ``handlers.Add*Handler`` class this package used to export has
been migrated onto the objects themselves (see ``add_handlers/`` and
each view's own ``objects_3d``/``objects_schematic``/``objects_pegboard``
package) and removed. What remains here is the reusable, view-agnostic
logic those replacements still call into: part-compatibility lookups,
wire fork/merge, terminal/transition placement geometry, and
``HandlerBase``'s own shared classmethods (``set_angle_from_cavity``/
``set_angle_from_housing``/``reset_angle``/etc.).
"""

from . import handler_base as _handler_base

HandlerBase = _handler_base.HandlerBase

del _handler_base
