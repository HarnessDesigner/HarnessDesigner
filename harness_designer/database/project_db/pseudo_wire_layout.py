# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Pseudo ``PJTWireLayout`` row backing an invisible wire-snap probe.

Background -- why this exists
------------------------------
Wire snapping (onto a terminal's own attach point, a splice's own branch
point, or another wire's open/dangling end of the same part) used to be
unreliable: it only ever worked when ``gl.object_picker.find_object``'s
ray happened to intersect the target's own real, exact mesh geometry -- a
terminal's/splice's connection point is small, and a plain dangling wire
end with no bend on it has no mesh there at all to hit. That's what made
snapping feel "hit or miss".

The fix: reuse ``objects.wire_layout.WireLayout`` itself as the pickable
hit-test target instead of inventing a new pickable object type. A real
``WireLayout`` already renders as a sphere sized to its wire's own
``od_mm`` (see ``objects.objects3d.wire_layout.WireLayout.__init__``), and
is already recognized by every hover/click branch that places or drags a
wire. Handlers.wire_snap.SnapProbeSet builds one of these invisible
probes at every location a wire is allowed to snap onto -- every
terminal's own attach point, every splice's own branch point, and every
OTHER open/dangling wire end that shares the same part being
placed/dragged -- each sized to that same part's own ``od_mm``, so the
effective "hit region" is a generous sphere matching the wire's real
diameter instead of a pixel-precise mesh hit. Both consumers build a
fresh probe set at the start of their session:

- ``handlers.wire_handler.AddWireHandler`` (the two-click wire placement
  flow) builds one via ``_ensure_snap_probes()``, called from every
  ``hover()`` -- the existing pick calls in that file already recognize a
  hit on any ``WireLayout`` (real or a probe); ``wire_snap.resolve_picked``
  additionally unwraps a terminal probe back to the real ``Terminal`` so
  every existing ``isinstance(picked, Terminal)`` branch runs unchanged.
- ``gl.canvas3d.dragging.EndpointDragObject`` (dragging an existing wire's
  already-placed, freely-draggable end) builds one at drag-start and
  hit-tests against it on every mouse-move via the same picker, using
  ``wire_snap.get_snap_info`` to decide whether to commit the connection
  on mouse-up (``terminal.add_wire`` for a terminal hit, or sharing the
  other wire's own live endpoint ``Point`` for a wire-end hit).

This module supplies the one new piece both of those needed: something
that satisfies ``PJTWireLayout``'s type contract (see class docstring
below for why that has to be a real subclass) while never touching a
real database row.
"""

from typing import TYPE_CHECKING


from .pjt_wire_layout import PJTWireLayout
from ...geometry import point as _point


if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire
    from ...database.global_db import wire as _global_wire
    from ...objects import terminal as _terminal
    from ...objects import wire as _wire
    from ...objects import splice as _splice


class _PseudoAttachedWire:
    """Stand-in for a ``PJTWire`` row, exposing only what a caller of
    ``attached_wires()[0]`` actually reads: ``.part`` (objects3d/objects2d's
    WireLayout constructors use ``.part.od_mm``/``.part.color.ui`` to size
    and color the marker sphere) and ``.part_id`` (wire_handler.py's
    ``_handle_first_click`` reads it to inherit the part being started from
    when a new wire begins on an existing WireLayout).
    """
    __slots__ = ('part', 'part_id')

    def __init__(self, part: "_global_wire.Wire"):
        self.part = part
        self.part_id = part.db_id


class PseudoPJTWireLayout(PJTWireLayout):
    """Pseudo ``PJTWireLayout`` row for an invisible wire-snap probe.

    One of these backs every probe ``handlers.wire_snap.SnapProbeSet``
    creates -- see this module's own docstring for the full picture. Never
    a real ``pjt_wire_layouts`` row -- constructed directly, with
    ``table=None`` and a throwaway, never-persisted ``db_id`` (see
    ``handlers.wire_snap._make_probe``), rather than through
    ``PJTWireLayoutsTable``. Every property below is overridden to return
    in-memory state set by :meth:`configure` instead of touching a
    (nonexistent) real row; every setter is a no-op for the same reason --
    nothing here is ever meant to be written back to the database.
    Subclassing the real row type (instead of a duck-typed stand-in) is
    deliberate -- ``_check_types.do`` enforces the declared
    ``PJTWireLayout`` annotations everywhere a wire layout's db_obj gets
    passed around, and passing something not a genuine ``PJTWireLayout``
    would fail those checks outright.

    :meth:`configure` records which real thing a given probe stands in
    for, read back via these attributes (exactly one group is ever set for
    a given probe, the rest stay ``None``):

    - ``snap_terminal`` -- the real ``Terminal`` ObjectBase wrapper, for a
      probe placed at a terminal's own true attach point
      (``PJTTerminal.attach_position3d`` -- the same point
      ``Terminal.add_wire`` itself connects a wire's end to; NOT
      ``wire_point3d``, a separate interior back-routing waypoint
      ``add_wire`` extends through afterward). ``wire_snap.resolve_picked``
      unwraps a hit on one of these straight back to this terminal so
      every existing ``isinstance(picked, Terminal)`` branch in
      ``wire_handler.py`` runs unchanged; ``wire_snap.get_snap_info``
      returns it as ``('terminal', terminal)`` for
      ``dragging.EndpointDragObject`` to call ``terminal.add_wire()`` with
      on drop.
    - ``snap_wire`` / ``snap_end`` -- the real ``Wire`` ObjectBase wrapper
      and which of its own ends (``'start'`` or ``'stop'``) is open and
      dangling there, for a probe placed at another wire's own free end.
      ``wire_handler.py`` needs no unwrapping for this case at all --
      ``position3d_id`` below already matches the real endpoint's, so the
      existing ``isinstance(picked, WireLayout)`` /
      ``_wire_layout_end_wire`` branch already treats a hit on this probe
      exactly like a hit on a real WireLayout marker.
    - ``snap_splice`` -- the real ``Splice`` ObjectBase wrapper, for a
      probe placed at a splice's own branch point
      (``PJTSplice.branch_position3d``). Needs unwrapping like a terminal
      probe does (``wire_handler.py``'s splice branch is
      ``isinstance(picked, Splice)``, not ``WireLayout``) --
      ``wire_snap.resolve_picked``/``get_snap_info`` both handle it the
      same way as ``snap_terminal``.
    """

    _table = None

    snap_terminal: "_terminal.Terminal | None" = None
    snap_wire: "_wire.Wire | None" = None
    snap_end: str | None = None
    snap_splice: "_splice.Splice | None" = None

    _position: "_point.Point | None" = None
    _wire_part: "_global_wire.Wire | None" = None

    def configure(self, position: "_point.Point", wire_part: "_global_wire.Wire",
                  terminal: "_terminal.Terminal | None" = None,
                  wire: "_wire.Wire | None" = None,
                  end: str | None = None,
                  splice: "_splice.Splice | None" = None) -> None:
        self._position = position
        self._wire_part = wire_part
        self.snap_terminal = terminal
        self.snap_wire = wire
        self.snap_end = end
        self.snap_splice = splice

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        if self._wire_part is None:
            return []

        return [_PseudoAttachedWire(self._wire_part)]

    @property
    def table(self) -> None:
        return None

    def delete(self) -> None:
        # No real row backs this instance -- see wire_snap.SnapProbeSet.close,
        # which tears probes down directly instead of ever calling this.
        pass

    @property
    def smooth(self) -> bool | None:
        return True

    @smooth.setter
    def smooth(self, value: bool | None):
        pass

    @property
    def is_visible2d(self) -> bool:
        return False

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        pass

    @property
    def is_visible3d(self) -> bool:
        return False

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        pass

    _position2d: "_point.Point | None" = None

    @property
    def position2d(self) -> "_point.Point":
        # A real Point, never None -- objects2d.wire_layout.WireLayout's
        # constructor unconditionally passes this straight into
        # Base2D.__init__ (this probe never actually renders in the 2D
        # view -- is_visible2d is always False above -- but Base2D itself
        # doesn't tolerate a None position; every other real WireLayout's
        # own position2d getter lazily creates a real row rather than ever
        # returning None, so this matches that same invariant). Fresh,
        # unbound, never persisted -- created once and cached, same
        # "unbound identity" pattern objects2d/splice.py's Splice uses for
        # its own angle.
        if self._position2d is None:
            self._position2d = _point.Point(0.0, 0.0)

        return self._position2d

    @property
    def position2d_id(self) -> bytes | None:
        return None

    @position2d_id.setter
    def position2d_id(self, value: bytes):
        pass

    @property
    def position3d(self) -> "_point.Point | None":
        return self._position

    @property
    def position3d_id(self) -> bytes | None:
        if self._position is None:
            return None

        db_id = self._position.db_id
        return db_id[:-2] if db_id is not None else None

    @position3d_id.setter
    def position3d_id(self, value: bytes):
        pass

