# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-marker drag for the 3D editor.

A wire marker can only be repositioned along the wire it was added to --
that constraint is already enforced by the object itself
(``objects.objects_3d.wire_marker.WireMarker._update_position``, bound to
the marker's own live position), which projects any position change back
onto the wire's current line and clamps it to stay clear of both ends by
the marker's own buffer. Because of that, this handler applies a plain,
un-locked 3D world-space delta (see
:meth:`~harness_designer.drag_handlers.editor_3d.DragHandler3D._delta3d`)
-- there is no ambiguous axis to lock in the first place, since whatever
direction the raw delta points in, the object's own callback immediately
re-projects the result back onto the wire regardless.

Unlike every other 3D drag, the directional-arrow gizmo shown here is
NOT the axis-aligned ``move_arrows.MoveArrows`` -- it's rotated to align
with the wire's own direction instead of a world axis (see
``gl.canvas_3d.wire_marker_arrow.WireMarkerArrow``), since "which axis is
locked" isn't a meaningful question for a drag that's always constrained
to one arbitrary line.
"""

from typing import TYPE_CHECKING

import numpy as np

from .. import wire_marker_arrow as _wire_marker_arrow
from ...geometry import point as _point
from .. import editor_3d as _editor_3d
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class WireMarker(_editor_3d.DragHandler3D):
    """Wire-marker drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        self.last_pos = target.obj3d.position.copy()

        wire = target.db_obj.wire
        direction = (np.asarray(wire.stop_position3d.as_float, dtype=np.float32)
                     - np.asarray(wire.start_position3d.as_float, dtype=np.float32))

        self._arrows = _wire_marker_arrow.WireMarkerArrow(
            target.obj3d.position, direction, canvas.mainframe, target.obj3d.aabb)

    @_check_types.do
    def delete(self) -> None:
        self._arrows.delete()
        super().delete()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, nothing to snap onto
        position = self.target.obj3d.position

        delta3d = self._delta3d(position, self.last_pos, delta)
        position += delta3d
        self.last_pos = position.copy()
