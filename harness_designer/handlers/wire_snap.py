# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Invisible sphere probes used to make wire-end/terminal/splice snapping
reliable.

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
"""

import uuid as _uuid_module
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

from ..database.project_db import pseudo_wire_layout as _pseudo_wire_layout
from ..objects import wire_layout as _wire_layout
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..objects import terminal as _terminal
    from ..objects import wire as _wire
    from ..objects import splice as _splice
    from ..database.global_db import wire as _global_wire


class SnapOverlay(QLabel):
    """Floating, click-through label shown near the cursor for a snap
    target's own compatibility message -- either a hard block (red; a
    genuine crimp-range mismatch) or a non-blocking capacity warning
    (amber; the combined cross-section of existing wires plus the one
    being placed/dragged exceeds the terminal's/splice's own maximum --
    see check_terminal_compat/check_splice_compat's own docstrings for why
    this one never blocks: only the upper bound is ever checked, and only
    as a heads-up -- a future design-rules-checker is the real place this
    gets enforced). Needs no user action to dismiss either way -- it
    tracks the cursor while the message applies and simply hides once it
    no longer does (the target changes, the mouse moves off it, or the
    connection is made).
    """

    _BLOCK_STYLE = (
        'background-color: rgba(180,0,0,200); color: white;'
        ' padding: 4px 6px; border-radius: 3px;')
    _WARNING_STYLE = (
        'background-color: rgba(180,120,0,200); color: white;'
        ' padding: 4px 6px; border-radius: 3px;')

    @_check_types.do
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(self._BLOCK_STYLE)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    @_check_types.do
    def show_message(self, mouse_pos, text: str, blocking: bool = True):
        self.setStyleSheet(self._BLOCK_STYLE if blocking else self._WARNING_STYLE)
        self.setText(text)
        self.adjustSize()
        self.move(int(mouse_pos.x) + 14, int(mouse_pos.y) + 14)
        self.show()
        self.raise_()

    @_check_types.do
    def hide_message(self):
        if self.isVisible():
            self.hide()


@_check_types.do
def _make_probe(mainframe: "_ui.MainFrame", position, wire_part: "_global_wire.Wire",
                 terminal: "_terminal.Terminal | None" = None,
                 wire: "_wire.Wire | None" = None,
                 end: str | None = None,
                 splice: "_splice.Splice | None" = None) -> _wire_layout.WireLayout:
    """Construct and register one invisible snap probe at *position*."""
    db_obj = _pseudo_wire_layout.PseudoPJTWireLayout(None, _uuid_module.uuid4().bytes)
    db_obj.configure(position, wire_part, terminal=terminal, wire=wire, end=end, splice=splice)

    return _wire_layout.WireLayout(mainframe, db_obj)


@_check_types.do
def _awg_fits(part, wire_part: "_global_wire.Wire") -> bool:
    """True when *wire_part*'s own AWG falls within *part*'s (a terminal's
    or splice's global part row) crimp range -- a genuine physical
    mismatch otherwise (the wire literally doesn't fit the crimp barrel),
    the one thing that still legitimately blocks a connection. AWG runs
    inverse to physical wire size, so awg_min (derived from the smallest
    accepted wire diameter) is numerically the LARGER of the two AWG
    numbers and awg_max the smaller -- see
    database.global_db.mixins.wire_size.WireSizeMixin's wire_size_dia_min/
    _max setters, which always derive _awg_min/_awg_max from dia_min/
    dia_max via d_mm_to_awg.
    """
    awg_min = part.wire_size_awg_min
    awg_max = part.wire_size_awg_max
    wire_awg = wire_part.size_awg

    if awg_min is not None and wire_awg > awg_min:
        return False

    if awg_max is not None and wire_awg < awg_max:
        return False

    return True


@_check_types.do
def capacity_warning(attached_wires, part, wire_part: "_global_wire.Wire", label: str) -> str | None:
    """Return a non-blocking capacity-warning message if adding
    *wire_part* to a terminal/splice already carrying *attached_wires*
    would push their combined cross-section past *part*'s own
    ``wire_size_cross_max``, or ``None`` if there's no such max or it
    still fits.

    Deliberately never blocks anything -- only the upper bound is ever
    checked here, never the lower one, because there's no way to know
    whether more wires are still going to be added to this same terminal/
    splice later. A future design-rules-checker is the right place to
    flag a terminal/splice that ends up under-filled; this is just a
    heads-up shown via SnapOverlay at the moment of snapping.
    """
    cross_max = part.wire_size_cross_max
    wire_cross = wire_part.size_mm2

    if cross_max is None or wire_cross is None:
        return None

    existing = sum(
        w.db_obj.part.size_mm2 for w in attached_wires
        if w.db_obj.part is not None and w.db_obj.part.size_mm2 is not None)

    total = existing + wire_cross
    if total <= cross_max:
        return None

    return (f'Combined cross-section {total:.1f} mm² exceeds this '
            f'{label}\'s maximum ({cross_max:.1f} mm²)')


@_check_types.do
def check_terminal_compat(terminal, wire_part: "_global_wire.Wire") -> tuple:
    """Return ``(is_compatible, block_message, warning_message)`` for
    attaching *wire_part* to *terminal*.

    ``is_compatible`` is only ever False for a genuine AWG crimp-range
    mismatch (``block_message`` set then, ``warning_message`` always
    ``None``). The combined-cross-section check never blocks -- see
    capacity_warning -- it only ever sets ``warning_message`` (with
    ``is_compatible`` staying True).
    """
    term_part = terminal.db_obj.part
    if term_part is None:
        return True, None, None

    if not _awg_fits(term_part, wire_part):
        awg_min = term_part.wire_size_awg_min
        awg_max = term_part.wire_size_awg_max
        wire_awg = wire_part.size_awg

        if awg_min is not None and wire_awg > awg_min:
            return False, f'Wire {wire_awg} AWG — terminal min is {awg_min} AWG', None

        return False, f'Wire {wire_awg} AWG — terminal max is {awg_max} AWG', None

    return True, None, capacity_warning(terminal.wires, term_part, wire_part, 'terminal')


@_check_types.do
def check_splice_compat(splice, wire_part: "_global_wire.Wire") -> tuple:
    """Return ``(is_compatible, block_message, warning_message)`` for
    attaching *wire_part* to *splice* -- mirrors check_terminal_compat
    exactly.

    Only the single-crimp splice variety is handled here (the only one
    modeled/attachable interactively today) -- see
    handlers.splice_handler._wire_fits, the pre-existing AWG-range check
    this reuses the same convention as.

    A splice has only 2 real crimp locations -- confirmed 2026-08-06:
    there's no third "branch" crimp; the branch point is purely a
    software/visual convenience for attaching and rendering a wire there.
    ``start_sibling``/``stop_sibling`` are the same physical through-wire
    continuing on both sides of the splice, not two separate conductors,
    so only ONE of them (never both) counts toward the combined
    cross-section -- summing both would double-count that one wire's own
    gauge. Every ``branch_wire`` is a genuinely separate conductor and
    always counts.
    """
    splice_part = splice.db_obj.part
    if splice_part is None:
        return True, None, None

    if not _awg_fits(splice_part, wire_part):
        awg_min = splice_part.wire_size_awg_min
        awg_max = splice_part.wire_size_awg_max
        wire_awg = wire_part.size_awg

        if awg_min is not None and wire_awg > awg_min:
            return False, f'Wire {wire_awg} AWG — splice min is {awg_min} AWG', None

        return False, f'Wire {wire_awg} AWG — splice max is {awg_max} AWG', None

    through_wire = splice.start_sibling if splice.start_sibling is not None else splice.stop_sibling
    attached = ([through_wire] if through_wire is not None else []) + splice.branch_wires

    return True, None, capacity_warning(attached, splice_part, wire_part, 'splice')


@_check_types.do
def _is_open_wire_end(project, point) -> bool:
    """True when exactly one wire endpoint (project-wide) sits at *point*.

    More than one means *point* is a junction/merge seam, not a free
    dangling end -- not a valid snap target (mirrors the "must be an
    endpoint, not a split mid-point" rule ``_wire_layout_end_wire`` already
    applies to real WireLayout markers).
    """
    point_id = point.db_id[:-2]
    count = 0

    for w in project.wires:
        if w.obj3d.start_position.db_id[:-2] == point_id:
            count += 1
        if w.obj3d.stop_position.db_id[:-2] == point_id:
            count += 1

    return count == 1


class SnapProbeSet:
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
    def __init__(self, mainframe: "_ui.MainFrame", wire_part: "_global_wire.Wire",
                 exclude_wire: "_wire.Wire | None" = None):
        from ..drag_handlers.editor_3d import wire as _dragging  # NOQA -- avoid a cycle at import time

        self.mainframe = mainframe
        self._probes: list[_wire_layout.WireLayout] = []

        project = mainframe.project

        for terminal in project.terminals:
            if terminal.db_obj.cavity is not None:
                # Seated -- see class docstring; the owning cavity gets the
                # probe instead, below.
                continue

            probe = _make_probe(
                mainframe, terminal.db_obj.wire_position3d, wire_part, terminal=terminal)
            self._probes.append(probe)

        for cavity in project.cavities:
            pjt_terminal = cavity.db_obj.terminal
            if pjt_terminal is None:
                continue

            terminal = pjt_terminal.get_object()
            if terminal is None:
                continue

            ok, _block_msg, _warning_msg = check_terminal_compat(terminal, wire_part)
            if not ok:
                continue

            probe = _make_probe(
                mainframe, cavity.db_obj.wire_position3d, wire_part, terminal=terminal)
            self._probes.append(probe)

        for splice in project.splices:
            probe = _make_probe(
                mainframe, splice.db_obj.branch_position3d, wire_part, splice=splice)
            self._probes.append(probe)

        for wire in project.wires:
            if wire is exclude_wire:
                continue
            if wire.db_obj.part_id != wire_part.db_id:
                continue

            start_anchored, stop_anchored = _dragging.wire_end_anchors(project, wire)

            if not start_anchored:
                point = wire.obj3d.start_position
                if _is_open_wire_end(project, point):
                    self._probes.append(
                        _make_probe(mainframe, point, wire_part, wire=wire, end='start'))

            if not stop_anchored:
                point = wire.obj3d.stop_position
                if _is_open_wire_end(project, point):
                    self._probes.append(
                        _make_probe(mainframe, point, wire_part, wire=wire, end='stop'))

    @_check_types.do
    def close(self) -> None:
        """Tear down every probe -- see module docstring for why this
        never calls ``.delete()`` on them."""
        for probe in self._probes:
            self.mainframe.remove_object(probe)

        self._probes = []


@_check_types.do
def resolve_picked(picked):
    """Unwrap a snap-probe hit back to the real object it stands in for.

    A terminal or splice probe unwraps to the real ``Terminal``/``Splice``
    -- every existing ``isinstance(picked, Terminal)`` /
    ``isinstance(picked, Splice)`` branch in wire_handler.py then handles
    it completely unchanged. A wire-end probe needs no unwrapping: its
    ``position3d_id`` already matches the real endpoint's, so the existing
    ``isinstance(picked, WireLayout)`` / ``_wire_layout_end_wire`` branch
    already treats it exactly like a hit on a real WireLayout marker.
    """
    if isinstance(picked, _wire_layout.WireLayout):
        terminal = getattr(picked.db_obj, 'snap_terminal', None)
        if terminal is not None:
            return terminal

        splice = getattr(picked.db_obj, 'snap_splice', None)
        if splice is not None:
            return splice

    return picked


@_check_types.do
def get_snap_info(picked) -> tuple:
    """Return ``(kind, target)`` describing a snap-probe hit, for callers
    (dragging.EndpointDragObject) that need to know exactly what a hit
    stands for rather than having it unwrapped/left in place the way
    ``resolve_picked`` does for wire_handler.py's own pick branches.

    ``kind`` is ``'terminal'`` (``target`` the real ``Terminal``),
    ``'splice'`` (``target`` the real ``Splice``), ``'wire_end'``
    (``target`` the ``(Wire, end)`` pair), or ``None`` (``target`` also
    ``None``) when *picked* isn't one of this session's own probes at all.
    """
    if not isinstance(picked, _wire_layout.WireLayout):
        return None, None

    db_obj = picked.db_obj

    terminal = getattr(db_obj, 'snap_terminal', None)
    if terminal is not None:
        return 'terminal', terminal

    splice = getattr(db_obj, 'snap_splice', None)
    if splice is not None:
        return 'splice', splice

    wire = getattr(db_obj, 'snap_wire', None)
    end = getattr(db_obj, 'snap_end', None)
    if wire is not None and end is not None:
        return 'wire_end', (wire, end)

    return None, None


@_check_types.do
def snap_point(kind: str, target):
    """Return the live world-space ``Point`` a resolved snap target sits
    at -- the exact position ``dragging.EndpointDragObject`` should move
    the dragged endpoint onto (never a copy: the caller must copy before
    mutating, since this is the same live Point the target itself uses).
    """
    if kind == 'terminal':
        # wire_position3d (the terminal's own back point), NOT
        # attach_position3d -- see SnapProbeSet's own docstring. If the
        # terminal is seated, this is still correct: EndpointDragObject's
        # own visual teleport-on-snap just needs *some* sensible point on
        # or near the terminal to land the cursor on before commit_snap
        # calls Terminal.add_wire() (which writes the real connection
        # geometry using attach_position3d regardless of where the
        # preview visually snapped to).
        return target.db_obj.wire_position3d

    if kind == 'splice':
        return target.obj3d.wire_position

    if kind == 'wire_end':
        wire, end = target
        return wire.obj3d.start_position if end == 'start' else wire.obj3d.stop_position

    return None


@_check_types.do
def commit_snap(mainframe: "_ui.MainFrame", wire_obj: "_wire.Wire", end: str,
                 kind: str, target) -> None:
    """Commit a real connection for a resolved snap hit once the mouse
    releases on a snapped drag (dragging.EndpointDragObject) -- the
    two-click placement flow (wire_handler.py) already commits its own
    connections inline as part of its normal click handling and never
    needs this.

    Mirrors exactly what wire_handler.py's own click-commit code already
    does for each case (Terminal.add_wire for a terminal, repointing onto
    the splice's own branch point + Splice.add_wire/Wire.set_sibling for a
    splice, wire_handler.merge_wire_into for a wire-end -- collapsing both
    rows into one with a real interior waypoint + WireLayout at the seam,
    not just sharing a Point between two still-separate rows, confirmed
    2026-08-05 as the correct behavior after testing showed the initial
    share-a-Point version left two separate database entries where the
    user expects one) -- just generalized to whichever end ('start' or
    'stop') is actually being dragged, since the existing code only ever
    had to handle a preview wire's fixed stop end.
    """
    if kind == 'wire_end':
        # merge_wire_into deletes both original wire rows itself (including
        # wire_obj's own now-seam point, kept alive as an interior waypoint
        # on the merged row) -- none of the shared stale-point cleanup
        # below applies here, and running it anyway would wrongly delete
        # that seam point right back out from under the merge.
        from . import wire_handler as _wire_handler  # NOQA -- avoid a cycle at import time

        other_wire, other_end = target
        _wire_handler.merge_wire_into(
            mainframe.project, wire_obj, other_wire, other_end, own_end=end)
        return

    obj3d = wire_obj.obj3d
    moving_point = obj3d.start_position if end == 'start' else obj3d.stop_position
    stale_id = moving_point.db_id[:-2]

    if kind == 'terminal':
        target.add_wire(wire_obj, end)

    elif kind == 'splice':
        target_point = target.obj3d.wire_position
        branch_id = target.db_obj.branch_position3d_id

        if end == 'start':
            wire_obj.obj3d.set_start_position(target_point)
            wire_obj.db_obj.start_position3d_id = branch_id
            wire_obj.db_obj.start_position2d_id = target.db_obj.position2d_id
            wire_obj.objschematic.set_start_position(target.db_obj.position2d)
        else:
            wire_obj.obj3d.set_stop_position(target_point)
            wire_obj.db_obj.stop_position3d_id = branch_id
            wire_obj.db_obj.stop_position2d_id = target.db_obj.position2d_id
            wire_obj.objschematic.set_stop_position(target.db_obj.position2d)

        target.add_wire(wire_obj)
        wire_obj.set_sibling(target, end)

        # A layout at the wire's own true end -- purely a visual cap
        # showing it properly seated into the splice, not a routing bend,
        # so the point is never tagged with wire_id/idx (unlike a
        # terminal's/cavity's own back-routing waypoints). Every branch
        # wire on this splice shares the exact same branch_position3d_id
        # (never cloned -- see check_splice_compat's own docstring: a
        # splice's branch point is a software/visual convenience, not a
        # real per-wire crimp location), so a 2nd/3rd wire snapping here
        # must not create a duplicate layout at the same point.
        ptables = mainframe.project.ptables
        existing = ptables.pjt_wire_layouts_table.select('id', position3d_id=branch_id)
        if not existing:
            layout_db = ptables.pjt_wire_layouts_table.insert(branch_id)
            layout_obj = _wire_layout.WireLayout(mainframe, layout_db)
            mainframe.project.add_wire_layout(layout_obj)

    else:
        return

    # Only delete the wire's own now-superseded point if nothing else in
    # the project still references it -- it can be a plain junction shared
    # with another wire's own endpoint (see dragging.EndpointDragObject's
    # own docstring), which a blind delete would corrupt.
    project = mainframe.project
    still_referenced = any(
        w.obj3d.start_position.db_id[:-2] == stale_id or
        w.obj3d.stop_position.db_id[:-2] == stale_id
        for w in project.wires)

    if not still_referenced:
        mainframe.project.ptables.pjt_points3d_table[stale_id].delete()
