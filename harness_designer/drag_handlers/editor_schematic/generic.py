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

import cProfile
import io
import pstats
import time
from typing import TYPE_CHECKING

from .. import editor_schematic as _editor_schematic
from ...wire_routing import reroute as _wire_reroute
from ...geometry import point as _point
from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


# Set True to print where every mouse move of a drag spends its time: the
# housing move itself (this includes the database writes and the callbacks
# that redraw the terminals), following, and routing. Off by default -- the
# timers are a few perf_counter calls, but the print is not free.
_TIMING = False

# Set True to profile the drag events themselves: it prints the busiest
# functions (by their own time, then including what they call) when you let go
# of the mouse -- or sooner, every _PROFILE_EVENTS mouse moves -- and starts
# over. For finding out WHAT inside a slow move is slow; much heavier than
# _TIMING, so leave it off otherwise.
_PROFILE = False
_PROFILE_EVENTS = 12
_profile = {'stats': None, 'count': 0}


def _profile_report() -> None:
    stats = _profile['stats']
    if stats is None:
        return

    stream = io.StringIO()
    stats.stream = stream
    stats.strip_dirs().sort_stats('tottime').print_stats(30)
    stats.sort_stats('cumulative').print_stats(30)
    print(f'---- profile of {_profile["count"]} drag events ----')
    print(stream.getvalue())

    _profile['stats'] = None
    _profile['count'] = 0


def _profile_event(profiler: cProfile.Profile) -> None:
    if _profile['stats'] is None:
        _profile['stats'] = pstats.Stats(profiler)
    else:
        _profile['stats'].add(profiler)

    _profile['count'] += 1
    if _profile['count'] >= _PROFILE_EVENTS:
        _profile_report()


class Generic(_editor_schematic.DragHandlerSchematic):
    """Generic locked-X/Z drag -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        self._deadlocked = False

        # Resolved once at drag-arm, not per move -- same discipline
        # DragHandlerPegboard's own touching_budgets cache uses, and for
        # the same reason: what's attached doesn't change mid-drag, only
        # its routed path does.
        #
        # Sorted junction wires first (see ``wire_routing.reroute.
        # is_junction_wire``'s own docstring -- a wire-junction terminal's
        # own wires need to claim their lanes around its pushed-out
        # attach point before anyone else routes near it), then, within
        # each of those two groups, shortest-crow-flies-distance first: a
        # short run is the more constrained one (less room to route around
        # a conflict), so it gets first pick of the available lanes each
        # frame while its longer siblings are still unsettled -- see
        # __call__.
        self._attached = sorted(
            _wire_reroute.wires_attached_to(target),
            key=lambda w: (not _wire_reroute.is_junction_wire(w), _wire_reroute.crow_flies_distance(w)))

    @_debug.logfunc
    @_check_types.do
    def __call__(self, delta, mouse_pos: _point.Point) -> None:  # NOQA -- delta unused, the locked ortho camera gives an absolute world position directly
        objschematic = self.target.objschematic

        profiler = None
        if _PROFILE:
            profiler = cProfile.Profile()
            profiler.enable()

        t_begin = time.perf_counter()

        try:
            # ONE entry into the GL context for the whole move. Nearly every
            # object that reacts to a position change (the housing, each of its
            # terminals and cavities, the handle on each moved waypoint) does
            # ``with self.editor.context:`` in its callback, and each outermost
            # entry is a makeCurrent()/doneCurrent() pair on the widget. The
            # context nests (it is reference counted, and an entry made while
            # it is already current only re-checks), so holding it here turns
            # all of those into cheap checks.
            with objschematic.editor.context:
                t_context = time.perf_counter()
                self._event(objschematic, mouse_pos, t_begin, t_context)
        finally:
            if profiler is not None:
                profiler.disable()
                _profile_event(profiler)

    def _event(self, objschematic, mouse_pos: _point.Point, t_begin: float, t_context: float) -> None:
        world_pos = self._world_xz(mouse_pos)
        current = objschematic.position
        world_delta = _point.Point(
            float(world_pos.x) - float(current.x), 0.0, float(world_pos.z) - float(current.z))

        t_start = time.perf_counter()
        objschematic.drag(world_delta)
        t_drag = time.perf_counter()

        project = self.canvas.mainframe.project

        # A route is worth keeping until it collides: wires whose end moved with
        # the housing just FOLLOW it where their existing path can, and only the
        # ones that can't get a new route.
        remaining = _wire_reroute.follow_moved(
            project, self.target, self._attached, (float(world_delta.x), float(world_delta.z)))

        t_follow = time.perf_counter()

        self._route(project, remaining)

        renested = False
        if self._deadlocked:
            # A wire that had to be re-routed found no legal lane between the
            # wires that followed: a real collision, so re-nest the whole bundle.
            renested = True
            self._route(project, self._attached)

        if _TIMING:
            t_end = time.perf_counter()
            print(f'drag event: context {1000 * (t_context - t_begin):6.1f} ms | '
                  f'move {1000 * (t_drag - t_start):6.1f} ms | follow {1000 * (t_follow - t_drag):6.1f} ms | '
                  f'route {1000 * (t_end - t_follow):6.1f} ms ({len(remaining)} of {len(self._attached)} wires'
                  f'{", re-nested" if renested else ""}) | total {1000 * (t_end - t_begin):6.1f} ms')

    def _route(self, project, wires) -> None:
        # One grid for the whole batch, built once (see RoutingFrame). Every
        # wire in it not yet routed THIS pass stays out of the way of whichever
        # one IS being routed (only its fixed exit stubs count), and each one
        # settled becomes a real obstacle for the next -- the frame tracks that
        # split itself; skip_wires is only for the no-frame fallback.
        # The wires attached to the dragged object that are NOT being routed
        # (they followed it) are the ones to run alongside.
        routed = set(wires)
        siblings = [wire for wire in self._attached if wire not in routed]
        frame = _wire_reroute.build_frame(project, wires, siblings)

        unsettled = set(wires)
        for wire in wires:
            unsettled.discard(wire)
            _wire_reroute.reroute_wire(project, wire, skip_wires=unsettled, frame=frame)

        self._deadlocked = frame is not None and bool(frame.relaxed) and len(wires) < len(self._attached)

    @_check_types.do
    def delete(self) -> None:
        # Mouse released: report whatever the profiler gathered this drag.
        _profile_report()

        project = self.canvas.mainframe.project
        _wire_reroute.sweep_for_overlaps(project, self.target, self._attached)
        super().delete()
