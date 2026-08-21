# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Shared length-budget clamp mechanics for every Peg Board Editor drag
handler.

Peg-board dragging never shows a directional-arrows gizmo and is never
axis-locked -- the camera is a locked top-down orthographic projection
(see ``gl.canvas_pegboard.camera.Camera.screen_to_world``), so a screen
position maps unambiguously to a world X/Z position with no depth
ambiguity to resolve at all, unlike the free-orbit 3D camera (see
:mod:`~harness_designer.drag_handlers.editor_3d`).

Instead, every peg-board drag is length-budget clamped: it will never
stretch an attached wire/bundle segment past its real remaining length,
and it never pulls whatever's at the other end along with it -- purely a
local, independent clamp per touching segment, exactly as specified
("it will not pull the things that are at the other ends of the wires
and bundles"). The budgets themselves come from the dragged object's own
:meth:`~harness_designer.objects.objectsvar.base_var.BaseVar.touching_budgets`
(see :mod:`harness_designer.objects.objects_pegboard.chain_edges` for how
an anchor/wire-layout/bundle-layout object computes its own) -- this
class only owns the clamp *math*, never *what's attached or its budget*.
"""

from typing import TYPE_CHECKING
import math

from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_pegboard import canvas as _canvas
    from ... import objects as _objects


class DragHandlerPegboard(_base.DragHandlerBase):
    """Shared peg-board length-budget clamp mechanics.

    See the module docstring for the full rationale.
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        # Cached once at drag-arm, never rebuilt per move -- recomputing
        # continuously would make the edge touching the very point being
        # dragged chase its own tail (see touching_budgets's own
        # docstring for why the budget is recomputed fresh on every
        # *call* to it, but that call itself only ever happens once here).
        self._touching = target.objpegboard.touching_budgets()

    @staticmethod
    @_check_types.do
    def _clamp_to_edge(cand_x: float, cand_z: float, neighbor_x: float,
                       neighbor_z: float, max_length_mm: float) -> tuple:
        """Clamp ``(cand_x, cand_z)`` so its distance from
        ``(neighbor_x, neighbor_z)`` never exceeds *max_length_mm*.

        Applied once per touching edge, independently -- never a
        simultaneous/relaxed solve across every edge at once.
        """
        dx = cand_x - neighbor_x
        dz = cand_z - neighbor_z
        dist = math.hypot(dx, dz)

        if dist <= max_length_mm or dist < 1e-9:
            return cand_x, cand_z

        scale = max_length_mm / dist
        return neighbor_x + dx * scale, neighbor_z + dz * scale

    @_check_types.do
    def _apply_local_clamp(self, cand_x: float, cand_z: float) -> tuple:
        """Apply :meth:`_clamp_to_edge` for every cached touching budget
        (see :attr:`_touching`), in sequence -- each edge clamped
        independently against the *previous* clamp's result. The
        neighbor itself never moves.
        """
        for neighbor_x, neighbor_z, max_length_mm in self._touching:
            cand_x, cand_z = self._clamp_to_edge(
                cand_x, cand_z, neighbor_x, neighbor_z, max_length_mm)

        return cand_x, cand_z
