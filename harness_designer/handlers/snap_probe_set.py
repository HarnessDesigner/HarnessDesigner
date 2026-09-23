# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Abstract base for the invisible sphere probes used to make wire-end/
terminal/splice snapping reliable.

``gl.object_picker.find_object`` only ever registers a hit when the mouse
ray actually intersects an object's real mesh -- a terminal's/splice's own
tiny connection point (or a plain, marker-less dangling wire end) is
genuinely hard to hit exactly, which is why snapping felt "hit or miss"
before this.

The fix reuses ``objects.wire_layout.WireLayout`` itself as the hit-test
target instead of inventing a new pickable object type: a real
``WireLayout`` already renders as a sphere sized to its wire's own
``od_mm`` (see ``objects.objects_3d.wire_layout.WireLayout.__init__``) and
is already recognized by every hover/click branch in ``wire_handler.py``.
One is placed at every location a wire is allowed to snap to (every
terminal's own attach point, every splice's own branch point, every
open/dangling same-part wire end), each sized to the wire currently being
placed/dragged -- exactly the invisible snap sphere described by the
person who asked for this.
``database.project_db.pseudo_wire_layout.PseudoPJTWireLayout`` is the
pseudo ``PJTWireLayout`` row backing one -- see that module for why it
subclasses the real row type instead of duck-typing it.

Never call ``.delete()`` on a probe's ``WireLayout`` wrapper -- that runs
``_reconnect_wires()`` (assumes a real attached wire row). Tear probes
down via ``SnapProbeSet.close()``, which removes them straight from the
canvases instead (``PseudoPJTWireLayout.delete()`` is also a no-op, as a
second line of defense).

**This module holds ONLY the abstract ``SnapProbeSet``/``SnapProbeSetType``
-- deliberately kept out of :mod:`~harness_designer.handlers.wire_snap`,
which holds every other, genuinely view-agnostic helper (``SnapOverlay``,
the compatibility checks, snap-hit resolution/commit). Import THIS module
only from code that actually builds on the abstract class itself -- its
two concrete per-editor subclasses
(:class:`~harness_designer.drag_handlers.editor_3d.wire_snap.SnapProbeSet`/
:class:`~harness_designer.drag_handlers.editor_pegboard.wire_snap.
SnapProbeSet`) -- never from code that only needs the shared helpers;
import :mod:`~.wire_snap` for those instead (confirmed 2026-09-13: keeping
the two files separate means a caller that only wants ``check_terminal_compat``
or ``commit_snap`` never has to pull in the abstract probe-building
machinery it has no use for).
"""

from typing import TYPE_CHECKING, Union as _Union

import uuid as _uuid_module

from ..database.project_db import pseudo_wire_layout as _pseudo_wire_layout
from ..objects import wire_layout as _wire_layout
from . import wire_snap as _wire_snap
from .. import check_types as _check_types
from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import terminal as _terminal
    from ..objects import wire as _wire
    from ..objects import splice as _splice
    from ..objects import project as _project
    from ..database.global_db import wire as _global_wire


class SnapProbeSetType(type):
    pass


class SnapProbeSet(metaclass=SnapProbeSetType):
    """Every invisible snap probe live for one wire placement/drag session.

    Built once for the wire part being placed/dragged:

    - One probe per free-standing terminal (``PJTTerminal.cavity is
      None``), positioned at that terminal's own back point
      (``PJTTerminal.wire_position3d`` -- the real physical location a
      wire approaches and connects from outside the terminal; NOT
      ``attach_position3d``, the bare-conductor crimp point further
      inside the terminal's own body, which is never a sensible place to
      aim the mouse at and is never used as a snap point). Confirmed
      2026-08-06: ``Terminal.add_wire`` itself still always uses
      ``attach_position3d`` as the wire's own true outer endpoint and
      ``wire_position3d`` as an interior waypoint -- unchanged, already
      correct -- this probe's *position* is purely a visual snap target;
      the actual connection geometry ``add_wire`` writes is unaffected by
      where the probe happened to sit.
    - UNLESS the terminal is seated in a cavity, in which case NEITHER of
      its own points is used at all -- the owning cavity gets the probe
      instead, at the cavity's own wire-side/back connection point
      (``PJTCavity.wire_position3d``) -- only when the seated terminal's
      crimp range actually fits the wire part being placed/dragged (see
      ``check_terminal_compat`` -- a combined-cross-section-only mismatch
      does NOT skip the probe, since that never blocks the connection,
      only warns; a genuine AWG-range mismatch does, since there's
      nothing to snap onto if it can't ever connect). Both probe kinds
      resolve to the exact same real ``Terminal`` once picked -- see
      ``PseudoPJTWireLayout.snap_terminal`` -- so wire_handler.py's/
      dragging.py's own commit logic (``Terminal.add_wire``) needs no
      cavity-specific handling at all.
    - One probe at every splice's own branch point.
    - One at every OTHER open/dangling wire endpoint sharing that same
      part_id (excluding *exclude_wire*, the wire currently being
      placed/dragged, and any end already anchored to a terminal/cavity --
      that point already gets a terminal/cavity probe above).
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 wire_part: "_global_wire.Wire",
                 exclude_wire: _Union["_wire.Wire", None] = None) -> None:

        self.mainframe = mainframe
        self._probes: list[_wire_layout.WireLayout] = []

        project = mainframe.project

        for terminal in project.terminals:
            if terminal.db_obj.cavity is not None:
                # Seated -- see class docstring; the owning cavity gets the
                # probe instead, below.
                continue

            kwargs = self._get_wire_position(terminal.db_obj)

            probe = self._make_probe(wire_part, terminal=terminal, **kwargs)

            self._probes.append(probe)

        for cavity in project.cavities:
            pjt_terminal = cavity.db_obj.terminal
            if pjt_terminal is None:
                continue

            terminal = pjt_terminal.get_object()
            if terminal is None:
                continue

            ok, _block_msg, _warning_msg = (
                _wire_snap.check_terminal_compat(terminal, wire_part))

            if not ok:
                continue

            kwargs = self._get_wire_position(cavity.db_obj)
            probe = self._make_probe(wire_part, terminal=terminal, **kwargs)

            self._probes.append(probe)

        for splice in project.splices:
            kwargs = self._get_branch_position(splice.db_obj)

            probe = self._make_probe(wire_part, splice=splice, **kwargs)
            self._probes.append(probe)

        for wire in project.wires:
            if wire is exclude_wire:
                continue

            if wire.db_obj.part_id != wire_part.db_id:
                continue

            start_anchored, stop_anchored = self._wire_end_anchors(project, wire)

            if not start_anchored:
                view_obj = self._get_view_object(wire)
                point = view_obj.start_position

                if self._is_open_wire_end(project, point):
                    kwargs = self._get_start_position(wire.db_obj)

                    probe = self._make_probe(
                        wire_part, wire=wire, end='start', **kwargs)

                    self._probes.append(probe)

            if not stop_anchored:
                view_obj = self._get_view_object(wire)
                point = view_obj.stop_position

                if self._is_open_wire_end(project, point):

                    kwargs = self._get_stop_position(wire.db_obj)

                    probe = self._make_probe(
                        wire_part, wire=wire, end='stop', **kwargs)

                    self._probes.append(probe)

    @_check_types.do
    def _is_open_wire_end(self, project: "_project.Project", point: _point.Point) -> bool:
        """True when exactly one wire endpoint (project-wide) sits at *point*.

        More than one means *point* is a junction/merge seam, not a free
        dangling end -- not a valid snap target (mirrors the "must be an
        endpoint, not a split mid-point" rule ``_wire_layout_end_wire`` already
        applies to real WireLayout markers).
        """
        point_id = point.db_id[:-2]
        count = 0

        for w in project.wires:
            view_obj = self._get_view_object(w)

            if view_obj.start_position.db_id[:-2] == point_id:
                count += 1

            if view_obj.stop_position.db_id[:-2] == point_id:
                count += 1

        return count == 1

    @_check_types.do
    def _make_probe(
        self,
        wire_part: "_global_wire.Wire",
        terminal: _Union["_terminal.Terminal", None] = None,
        wire: _Union["_wire.Wire", None] = None,
        end: str | None = None,
        splice: _Union["_splice.Splice", None] = None,
        position3d: _point.Point | None = None,
        position_pegboard: _point.Point | None = None,

    ) -> _wire_layout.WireLayout:

        """Construct and register one invisible snap probe.

        *position* (3D) and *position_pegboard* are independent -- pass only
        the one matching whichever view's ``SnapProbeSet`` this probe is for
        (``None`` for the other), same as any other object type: a facade
        with a ``None`` position in a given view just has no presence
        there (see ``CanvasBase.add_object``), so the probe naturally never
        shows up as pickable in the view it wasn't built for.
        """
        db_obj = _pseudo_wire_layout.PseudoPJTWireLayout(None, _uuid_module.uuid4().bytes)
        db_obj.configure(wire_part, terminal=terminal, wire=wire, end=end, splice=splice,
                         position3d=position3d,
                         position_pegboard=position_pegboard)

        return _wire_layout.WireLayout(self.mainframe, db_obj)

    @staticmethod
    def _get_start_position(db_obj: object) -> dict[str, _point.Point]:
        raise NotImplementedError

    @staticmethod
    def _get_stop_position(db_obj: object) -> dict[str, _point.Point]:
        raise NotImplementedError

    @staticmethod
    def _get_branch_position(db_obj: object) -> dict[str, _point.Point]:
        raise NotImplementedError

    @staticmethod
    def _get_wire_position(db_obj: object) -> dict[str, _point.Point]:
        raise NotImplementedError

    @staticmethod
    def _get_view_object(obj: object) -> object:
        raise NotImplementedError

    @staticmethod
    def _wire_end_anchors(project: "_project.Project", wire_obj: "_wire.Wire") -> tuple[bool, bool]:
        """Return (start_anchored, stop_anchored) for *wire_obj* -- see
        ``handlers.wire_drag_base.WireDragMixin.wire_end_anchors``'s own
        docstring for the full rule (whether an end is anchored to a
        cavity/terminal is a project-wide topology fact, not a per-view
        rendering detail, so this is expected to always resolve through
        the 3D concrete ``Wire`` specifically, regardless of which
        view's ``SnapProbeSet`` subclass this is).

        This class deliberately never imports any concrete per-view
        ``Wire`` itself -- doing so from here would make the *abstract*
        base depend on one specific view's module, the same coupling
        the per-view accessors below exist to avoid (confirmed
        2026-09-13). Each concrete subclass overrides this to reach
        whichever ``Wire`` it needs, the same as every other accessor.
        """
        raise NotImplementedError

    @_check_types.do
    def close(self) -> None:
        """Tear down every probe -- see module docstring for why this
        never calls ``.delete()`` on them."""
        for probe in self._probes:
            self.mainframe.remove_object(probe)

        self._probes = []
