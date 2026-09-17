# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Generic locked-X/Z drag for the Schematic Editor.

Applies to: housing, terminal, splice -- anything whose entire position
is the one thing a drag ever needs to move (no per-segment/rope
mechanics, unlike wire -- see :mod:`~.wire`).

No directional-arrows gizmo, no axis lock, no length-budget clamp
(unlike the peg board) -- the camera's locked top-down orthographic
projection already maps the cursor to an unambiguous world X/Z
position, and a schematic wire's own path is entirely auto-routed
around whatever it connects to rather than a fixed-length physical run.

Every wire directly attached to the dragged object (see
``wire_routing.reroute.wires_attached_to``) is live-rerouted
on every move -- exactly the "live drag rerouting" use case that
module's own docstring already names as its reason for existing. On
release, :func:`~...wire_routing.reroute.sweep_for_overlaps` catches any other
wire elsewhere in the project left crossing the object's new footprint.

Routed shortest-crow-flies-distance first, one at a time, each pass
excluding whichever siblings haven't been routed yet THIS pass (see
``wire_routing.reroute.reroute_wire``'s own ``skip_wires``) from the
"don't run too close to another wire" check -- an unsettled sibling's
current path is stale (it's about to be recomputed itself, possibly a
frame later in the same drag), so treating it as a hard obstacle only
makes a wire dodge a position that's already changing, and can make two
siblings chase each other's stale path back and forth every frame
instead of ever settling.
"""

from typing import TYPE_CHECKING

from .. import editor_schematic as _editor_schematic
from ...wire_routing import reroute as _wire_reroute
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class Generic(_editor_schematic.DragHandlerSchematic):
    """Generic locked-X/Z drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        # Resolved once at drag-arm, not per move -- same discipline
        # DragHandlerPegboard's own touching_budgets cache uses, and for
        # the same reason: what's attached doesn't change mid-drag, only
        # its routed path does.
        #
        # Sorted shortest-crow-flies-distance first: a short run is the
        # more constrained one (less room to route around a conflict),
        # so it gets first pick of the available lanes each frame while
        # its longer siblings are still unsettled -- see __call__.
        self._attached = sorted(
            _wire_reroute.wires_attached_to(target), key=_wire_reroute.crow_flies_distance)

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        objschematic = self.target.objschematic

        world_pos = self._world_xz(mouse_pos)
        current = objschematic.position
        world_delta = _point.Point(
            float(world_pos.x) - float(current.x), 0.0, float(world_pos.z) - float(current.z))

        objschematic.drag(world_delta)

        project = self.canvas.mainframe.project

        # Every attached wire not yet routed THIS pass stays excluded as
        # an obstacle for whichever one IS currently being routed (see
        # the module docstring) -- shrinks as each wire in turn gets its
        # path settled, so only already-settled siblings (this pass)
        # count as real obstacles by the time the next one routes.
        unsettled = set(self._attached)
        for wire in self._attached:
            unsettled.discard(wire)
            _wire_reroute.reroute_wire(project, wire, skip_wires=unsettled)

    @_check_types.do
    def delete(self) -> None:
        project = self.canvas.mainframe.project
        _wire_reroute.sweep_for_overlaps(project, self.target, self._attached)
        super().delete()
