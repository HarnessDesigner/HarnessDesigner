# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generic locked-X/Z drag for the Peg Board Editor.

Applies to: transitions, housings, wire layouts, bundle layouts, and
terminals (not in a cavity) -- anything whose entire position is the one
thing a drag ever needs to move (no per-segment/rope mechanics, unlike
wire/bundle -- see :mod:`~.wire`/:mod:`~.bundle`).

No directional-arrows gizmo, no axis lock (see the package's own
``__init__`` docstring) -- the camera's locked top-down orthographic
projection already maps the cursor to an unambiguous world X/Z position
every frame. Movement is bound only by the length budget of whatever
wire/bundle segments touch this object (see
:meth:`~harness_designer.objects.objectsvar.base_var.BaseVar.touching_budgets`),
clamped independently against every move -- it never pulls whatever's
attached at the other end.
"""

from typing import TYPE_CHECKING

from .. import editor_pegboard as _editor_pegboard
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects


class Generic(_editor_pegboard.DragHandlerPegboard):
    """Generic locked-X/Z drag -- see the module docstring."""

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        objpegboard = self.target.objpegboard

        world_pos = self.canvas.camera.screen_to_world(mouse_pos)
        cand_x, cand_z = self._apply_local_clamp(
            float(world_pos.x), float(world_pos.z))

        current = objpegboard.position
        world_delta = _point.Point(
            cand_x - float(current.x), 0.0, cand_z - float(current.z))

        objpegboard.drag(world_delta)
