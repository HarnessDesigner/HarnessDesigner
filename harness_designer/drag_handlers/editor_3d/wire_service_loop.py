# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-locked service-loop drag for the 3D editor.

A wire service loop whose context menu has "Lock to Wire" checked is dragged
along the wire it sits in, not freely (``objects_3d.wire_service_loop.
WireServiceLoop._create_drag_handler`` picks this handler over
:class:`~.generic.Generic` for it).

Like a wire marker's drag (:mod:`~.wire_marker`) the directional-arrow gizmo
is the wire-aligned :class:`~harness_designer.drag_handlers.wire_marker_arrow.
WireMarkerArrow`, and the raw 3D delta the mouse implies is applied as-is --
no axis lock, since there is only one direction to go. Here the direction is
the wire's own, taken from the two wire points either side of the loop (not
the line between the loop's start and stop points, which is about 27 degrees
off it), and only the part of the delta along it counts. The loop itself
(``WireServiceLoop.slide_along_wire``) decides what a slide may do: carry the
loop round a bend, hand the bend's waypoint to the wire behind it, pass a
marker, or stop. When a bend turns the wire the arrows are rebuilt to match.

Everything else a drag of a loop does (the move gesture, realizing the
peg-board length, the collision session) is :class:`~.generic.Generic`'s.
"""

from typing import TYPE_CHECKING

import numpy as np

from . import generic as _generic
from .. import wire_marker_arrow as _wire_marker_arrow
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas_window as _canvas_window
    from ... import objects as _objects


# The wire counts as having turned when the dot product of the old and new
# directions drops below this
_TURNED = 0.9999


class WireServiceLoop(_generic.Generic):
    """Wire-locked service-loop drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas_window.CanvasWindow", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        loop = target.obj3d

        # The arrows' own Point, at the loop's centroid (its position is its
        # start point, off to one end), moved by hand as the loop moves
        self._arrow_center = loop.centroid
        self._axle = loop.slide_axle()
        self._arrows = self._make_arrows()

    @_check_types.do
    def _make_arrows(self) -> _wire_marker_arrow.WireMarkerArrow:
        loop = self.target.obj3d

        return _wire_marker_arrow.WireMarkerArrow(
            self._arrow_center, self._axle, self.canvas.mainframe, loop.aabb)

    @_check_types.do
    def delete(self) -> None:
        try:
            self._arrows.delete()
        finally:
            super().delete()

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:  # NOQA -- mouse_pos unused, nothing to snap onto
        loop = self.target.obj3d

        delta3d = self._delta3d(loop.position, self.last_pos, delta)

        # The wire turns as the loop is carried round a bend, so the
        # direction it is slid along is read afresh every event
        axle = loop.slide_axle()
        if axle is None:
            return

        distance = float(np.dot(delta3d.as_numpy.astype(np.float64), axle))
        loop.slide_along_wire(distance)

        self.last_pos = loop.position.copy()

        self._follow_loop()
        self._realize_pegboard_length()

    @_check_types.do
    def _follow_loop(self) -> None:
        """Keep the arrows on the loop's centroid, and pointing along the wire."""
        loop = self.target.obj3d

        self._arrow_center += loop.centroid - self._arrow_center

        axle = loop.slide_axle()
        if axle is None:
            return

        if float(np.dot(axle, self._axle)) >= _TURNED:
            return

        # The arrows' orientation is fixed when they are built
        self._arrows.delete()
        self._axle = axle
        self._arrows = self._make_arrows()
