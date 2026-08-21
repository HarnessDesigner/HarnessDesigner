# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from . import terminal as _terminal
from . import splice as _splice
from .objects_schematic import wire as _wire_schematic
from .objects_3d import wire as _wire_3d
from .objects_pegboard import wire as _wire_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire
    from . import wire_layout as _wire_layout_obj


class Wire(_ObjectBase):
    """Represent a wire in :mod:`harness_designer.objects.wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    objschematic: _wire_schematic.Wire = None
    obj3d: _wire_3d.Wire = None
    objpegboard: _wire_pegboard.Wire = None
    db_obj: "_pjt_wire.PJTWire" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire.PJTWire", project_load=False):
        """Initialise the :class:`Wire` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire.PJTWire`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.objschematic = _wire_schematic.Wire(self, db_obj)
        self.obj3d = _wire_3d.Wire(self, db_obj)
        self.objpegboard = _wire_pegboard.Wire(self, db_obj)

        # Sibling graph: whatever this wire's own start/stop end attaches to
        # -- a Terminal, Splice, or WireServiceLoop, never another Wire (two
        # wires touching are merged into one row instead of staying linked,
        # see handlers.wire_handler's wire-to-wire join). Each end holds at
        # most one sibling; the thing on the other side may hold several
        # (Terminal.wires, Splice.branch_wires) -- see set_sibling.
        self._start_sibling_ref = None
        self._stop_sibling_ref = None

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def start_sibling(self):
        """Whatever this wire's start end attaches to (Terminal, Splice,
        WireServiceLoop), or None for a dangling/free-space end."""
        return None if self._start_sibling_ref is None else self._start_sibling_ref()

    @property
    @_check_types.do
    def stop_sibling(self):
        """Whatever this wire's stop end attaches to (Terminal, Splice,
        WireServiceLoop), or None for a dangling/free-space end."""
        return None if self._stop_sibling_ref is None else self._stop_sibling_ref()

    @_check_types.do
    def set_sibling(self, other, end: str) -> None:
        """Record *other* as what this wire's *end* ('start' or 'stop')
        attaches to.

        One-sided: this only stores this wire's own side of the link. The
        reverse direction (Terminal.add_wire, Splice.set_siblings/add_wire,
        WireServiceLoop.set_siblings) is a separate, explicit call made by
        whichever handler is wiring the two objects together -- see
        handlers.splice_handler/handlers.wire_service_loop_handler.

        :param other: The Terminal/Splice/WireServiceLoop object attached
            at *end*, or None to clear it.
        :param end: 'start' or 'stop'.
        """
        ref = None if other is None else weakref.ref(other)

        if end == 'start':
            self._start_sibling_ref = ref
        elif end == 'stop':
            self._stop_sibling_ref = ref
        else:
            raise ValueError(f"end must be 'start' or 'stop', got {end!r}")

    @property
    @_check_types.do
    def is_connected(self) -> bool:
        """Whether this wire has a completed connection (a Terminal or a
        Splice, never a dangling/free-space end or a bare WireLayout) at
        *both* its start and stop -- the schematic editor only ever
        shows/picks a wire meeting this (see ``gl/canvas2d/canvas.py``'s
        ``_render_vbo_objects``/``gl/canvas2d/mouse_handler.py``'s
        ``_get_object_at_point``), and it's also what the auto-router
        (``objects_schematic/wire_routing.py``) treats as a real obstacle to
        route around -- an in-progress wire isn't really "there" yet.
        """
        return (isinstance(self.start_sibling, (_terminal.Terminal, _splice.Splice))
                and isinstance(self.stop_sibling, (_terminal.Terminal, _splice.Splice)))

    @property
    @_check_types.do
    def layouts(self) -> list["_wire_layout_obj.WireLayout"]:
        """Every WireLayout marking a point on this wire's own path --
        its true start/stop and every interior waypoint."""
        point_ids = {self.db_obj.start_position3d_id, self.db_obj.stop_position3d_id}
        point_ids.update(wp.db_id for wp in self.db_obj.waypoints3d)

        return [
            layout for layout in self.mainframe.project.wire_layouts
            if layout.db_obj.position3d_id in point_ids
        ]

    @_check_types.do
    def set_selected(self, flag):
        """Select this wire, and show every WireLayout on its own path
        in the selected color too -- via identify(), not set_selected()
        (the layouts themselves never become the true selection;
        mainframe only ever tracks one at a time, see
        ObjectBase.set_selected)."""
        super().set_selected(flag)

        for layout in self.layouts:
            if layout.obj3d is not None:
                layout.obj3d.identify(layout.obj3d.selected_material if flag else None)
            if layout.objschematic is not None:
                layout.objschematic.identify(layout.objschematic.selected_material if flag else None)

    @_check_types.do
    def trace_run(self) -> tuple[float, float]:
        """Walk outward from both ends of this wire through any attached
        Splice/WireServiceLoop, summing physical length (mm) and
        resistance across every Wire in the same electrical run.

        Stops at a Terminal or a dangling end -- continuing a run across a
        mated connector interface (terminal-to-terminal) isn't supported
        yet; there's no housing-mating model to walk through.

        :returns: (total_length_mm, total_resistance)
        """
        seen = set()
        total_length = 0.0
        total_resistance = 0.0
        stack = [self]

        while stack:
            wire = stack.pop()
            db_id = wire.db_obj.db_id
            if db_id in seen:
                continue
            seen.add(db_id)

            total_length += wire.db_obj.length_mm
            total_resistance += wire.db_obj.resistance

            for sibling in (wire.start_sibling, wire.stop_sibling):
                if sibling is None:
                    continue

                # Splice (wires: start+stop+branch) and Terminal (wires:
                # open list) both expose every attached wire the same way;
                # WireServiceLoop exposes its fixed pair via start_sibling/
                # stop_sibling instead (same shape as Wire itself).
                if hasattr(sibling, 'wires'):
                    for w in sibling.wires:
                        if w is not wire and w.db_obj.db_id not in seen:
                            stack.append(w)
                elif hasattr(sibling, 'start_sibling'):
                    for w in (sibling.start_sibling, sibling.stop_sibling):
                        if w is not None and w is not wire and w.db_obj.db_id not in seen:
                            stack.append(w)

        return total_length, total_resistance

    @_check_types.do
    def delete(self):
        # TODO: If a wire segment is connected to other wire segments
        #       then the layouts at the ends that are attached shuld also be
        #       deleted.
        super().delete()
        self.mainframe.project.delete_wire(self.db_obj.db_id)
        self.db_obj.delete()
