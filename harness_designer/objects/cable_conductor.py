# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A conductor of a placed cable, as the junction between its leads.

A split cable end gives each conductor a LEAD at that end: an ordinary wire (``pjt_wires``, ``cable_conductor_id`` set) from the
lead's free end (where a terminal or splice attaches) to the conductor's split point on the trunk's split plane. The conductor is
the middle of the run, the junction the leads' split ends attach to. It is modelled on :class:`.wire_service_loop.WireServiceLoop`:
two connection points (``start_split_point3d_id`` / ``stop_split_point3d_id``) and a wire on each, so it is what
:attr:`.wire.Wire.start_sibling` / :attr:`.wire.Wire.stop_sibling` return for the split end of a lead.

It has no view of its own: the trunk is drawn by the cable (:mod:`.objects_3d.cable`) and the leads by their own wires, so this
is only the sibling-graph node. The :class:`.cable.Cable` makes and owns these (one per conductor row, made when first asked
for), and ``Project._reconcile_wire_sibling_graph`` links the leads on a project load. See ``TWISTED_WIRE_DESIGN.md``.

In the schematic the conductor is drawn as one wire between the terminals (or splices) its two leads end on, while both leads
end on one: that is :class:`ConductorRun`, made and dropped by :meth:`CableConductor.refresh_schematic`.
"""

from typing import TYPE_CHECKING, Union as _Union

import weakref

from PySide6 import QtCore

from . import ObjectBase as _ObjectBase
from .objects_schematic import cable_conductor as _conductor_schematic
from .. import check_types as _check_types
from ..crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_cable_conductor as _pjt_cable_conductor
    from . import cable as _cable_obj
    from . import wire as _wire_obj


@capturable()
class ConductorRun(_ObjectBase):
    """A cable conductor as the schematic draws it: one wire from the terminal or splice at the end of its lead at the cable's
    start to the one at the end of its lead at the cable's stop.

    It is not a :class:`.wire.Wire` (it is not a wire row's object, and the editors do not treat it as one), but it answers what
    the schematic's router and canvas ask of a wire: ``db_obj`` (the conductor's row, which is a wire row), ``start_sibling`` and
    ``stop_sibling`` (the terminals or splices at its two ends, not the leads), ``is_connected``, ``route_prefix`` and
    ``objschematic``. The row's 2D end points are the leads' own, so the line follows the terminals; its 2D route is the row's own
    list of waypoints (``pjt_wire_paths`` by the conductor's id). Deleting it only takes it out of the schematic: the conductor
    belongs to the cable.
    """
    objschematic: "_conductor_schematic.CableConductor" = None
    db_obj: "_pjt_cable_conductor.PJTCableConductor" = None

    # a run is never drawn by hand, so there is no hand-placed start of its path (the router asks)
    route_prefix: list | None = None

    @_check_types.do
    def __init__(self, node: "CableConductor"):
        """Initialise the :class:`ConductorRun` instance.

        :param node: The conductor's junction object.
        :type node: :class:`CableConductor`
        """
        super().__init__(node.mainframe, node.db_obj)

        self._node_ref = weakref.ref(node)

    @property
    @_check_types.do
    def node(self) -> "CableConductor":
        """The conductor's junction object.

        :rtype: :class:`CableConductor`
        """
        return self._node_ref()

    @property
    @_check_types.do
    def start_sibling(self) -> _Union[_ObjectBase, None]:
        """What the conductor ends on at the cable's start: whatever its start lead's free end is attached to (a terminal or
        splice), ``None`` while that end is not split or not attached.

        :rtype: :class:`.ObjectBase` | None
        """
        lead = self.node.start_sibling

        return None if lead is None else lead.start_sibling

    @property
    @_check_types.do
    def stop_sibling(self) -> _Union[_ObjectBase, None]:
        """What the conductor ends on at the cable's stop: whatever its stop lead's free end is attached to.

        :rtype: :class:`.ObjectBase` | None
        """
        lead = self.node.stop_sibling

        return None if lead is None else lead.start_sibling

    @property
    @_check_types.do
    def is_connected(self) -> bool:
        """Whether both ends are a terminal or a splice, which is when the schematic draws the conductor.

        :rtype: bool
        """
        return all(sibling is not None and (sibling.is_terminal or sibling.is_splice)
                   for sibling in (self.start_sibling, self.stop_sibling))

    @_check_types.do
    def attach(self, route: bool) -> None:
        """Draw the conductor in the schematic (the leads' end points are its end points) and put it on the canvas.

        :param route: Whether to route its path now (a conductor that has just been attached), or leave the waypoints it has
            (a project being loaded, whose path is already stored).
        :type route: bool
        """
        node = self.node
        row = self.db_obj

        start_id = node.start_sibling.db_obj.start_position2d_id
        stop_id = node.stop_sibling.db_obj.start_position2d_id

        if self.objschematic is None:
            row.start_position2d_id = start_id
            row.stop_position2d_id = stop_id
            row.is_visible2d = True

            self.objschematic = _conductor_schematic.CableConductor(self, row)
        elif row.start_position2d_id != start_id or row.stop_position2d_id != stop_id:
            # an end was attached to another terminal: the line has new ends
            row.start_position2d_id = start_id
            row.stop_position2d_id = stop_id

            self.objschematic.set_start_position(row.start_position2d)
            self.objschematic.set_stop_position(row.stop_position2d)

        if route:
            from ..wire_routing import reroute as _reroute  # NOQA -- avoid a cycle at import time

            _reroute.on_wire_attached(self.mainframe.project, self)
        else:
            self.mainframe.editor2d.add_object(self)

    @_check_types.do
    def detach(self) -> None:
        """Take the conductor out of the schematic: its waypoints (and their handles) and its view go; the row stays."""
        if self.objschematic is None:
            return

        from ..wire_routing import reroute as _reroute  # NOQA -- avoid a cycle at import time

        _reroute.set_waypoints(self.mainframe.project, self, [])

        self.mainframe.editor2d.remove_object(self)
        self.objschematic._delete()  # NOQA
        self.objschematic = None

        self.db_obj.is_visible2d = False

    @_check_types.do
    def get_treeitem(self) -> _Union["_objectbrowser.TreeItem", None]:  # NOQA
        """The conductor's item in the object browser (the junction object's: this is the same conductor).

        :rtype: :class:`_objectbrowser.TreeItem` | None
        """
        node = self.node

        return None if node is None else node.get_treeitem()

    @_check_types.do
    def delete(self) -> None:
        """Take the conductor out of the schematic. The conductor itself is not deleted: it is part of its cable."""
        node = self.node

        self.detach()
        self._deleted = True

        if node is not None and node._run is self:  # NOQA
            node._run = None  # NOQA


@capturable()
class CableConductor(_ObjectBase):
    """The junction of a cable conductor's two leads."""
    db_obj: "_pjt_cable_conductor.PJTCableConductor" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_pjt_cable_conductor.PJTCableConductor",
                 cable: "_cable_obj.Cable"):
        """Initialise the :class:`CableConductor` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: The conductor's row.
        :type db_obj: :class:`_pjt_cable_conductor.PJTCableConductor`
        :param cable: The cable the conductor is in.
        :type cable: :class:`_cable_obj.Cable`
        """
        super().__init__(mainframe, db_obj)

        self._cable_ref = weakref.ref(cable)

        # The lead at the cable's start end (its stop point is this conductor's start split point) and at the cable's stop end.
        self._start_sibling_ref: weakref.ReferenceType | None = None
        self._stop_sibling_ref: weakref.ReferenceType | None = None

        # How the schematic draws this conductor, while both its leads end on a terminal or splice (see refresh_schematic).
        self._run: ConductorRun | None = None

    @property
    def objschematic(self) -> "_conductor_schematic.CableConductor | None":
        """The conductor's view in the schematic; ``None`` while it is not drawn there. (The conductor's row is a wire row, and code
        that finds a wire's object from its row, a waypoint handle for one, asks for this.)"""
        return None if self._run is None else self._run.objschematic

    @property
    @_check_types.do
    def run(self) -> _Union[ConductorRun, None]:
        """The conductor as the schematic draws it; ``None`` while it is not drawn there.

        :rtype: :class:`ConductorRun` | None
        """
        return self._run

    @_check_types.do
    def refresh_schematic(self, route: bool) -> None:
        """Draw the conductor in the schematic when both of its leads end on a terminal or splice, and take it out when they no
        longer do. Called when a lead is attached (``wire_routing.reroute.on_wire_attached``), when one is cut free or deleted,
        and for every conductor as a project loads.

        :param route: Whether a conductor that has just become drawn is routed now. A project being loaded passes False: the
            path it stored is kept.
        :type route: bool
        """
        start = self.start_sibling
        stop = self.stop_sibling

        if start is None or stop is None:
            connected = False
        else:
            connected = all(sibling is not None and (sibling.is_terminal or sibling.is_splice)
                            for sibling in (start.start_sibling, stop.start_sibling))

        if connected:
            if self._run is None:
                self._run = ConductorRun(self)

            self._run.attach(route)
        elif self._run is not None:
            self._run.delete()

    @property
    @_check_types.do
    def cable(self) -> "_cable_obj.Cable":
        """The cable this conductor is in.

        :rtype: :class:`_cable_obj.Cable`
        """
        return self._cable_ref()

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_sibling(self) -> _Union["_wire_obj.Wire", None]:
        """The lead at the cable's start end, or ``None`` while that end is not split.

        :rtype: :class:`_wire_obj.Wire` | None
        """
        return None if self._start_sibling_ref is None else self._start_sibling_ref()

    @property
    @dump_property(severity=2)
    @_check_types.do
    def stop_sibling(self) -> _Union["_wire_obj.Wire", None]:
        """The lead at the cable's stop end, or ``None`` while that end is not split.

        :rtype: :class:`_wire_obj.Wire` | None
        """
        return None if self._stop_sibling_ref is None else self._stop_sibling_ref()

    @property
    @_check_types.do
    def wires(self) -> list["_wire_obj.Wire"]:
        """The leads attached to this conductor (one or two).

        :rtype: list[:class:`_wire_obj.Wire`]
        """
        return [wire for wire in (self.start_sibling, self.stop_sibling) if wire is not None]

    @_check_types.do
    def set_lead(self, start: bool, wire: _Union["_wire_obj.Wire", None]) -> None:
        """Record *wire* as the lead at one end of the cable (``None`` clears it).

        One-sided, like :meth:`.wire_service_loop.WireServiceLoop.set_siblings`: the caller also calls
        ``wire.set_sibling(conductor, wire.obj3d.stop_position)`` so the wire knows this end.

        :param start: Which end of the cable the lead is at.
        :type start: bool
        :param wire: The lead.
        :type wire: :class:`_wire_obj.Wire` | None
        """
        ref = None if wire is None else weakref.ref(wire)

        if start:
            self._start_sibling_ref = ref
        else:
            self._stop_sibling_ref = ref

    @_check_types.do
    def replace_wire(self, old_wire: "_wire_obj.Wire", new_wire: "_wire_obj.Wire") -> None:
        """Swap *old_wire* for *new_wire* on whichever side it is on (a lead that was split or merged elsewhere along its length).

        :param old_wire: The lead being replaced.
        :type old_wire: :class:`_wire_obj.Wire`
        :param new_wire: Its replacement.
        :type new_wire: :class:`_wire_obj.Wire`
        """
        if self._start_sibling_ref is not None and self._start_sibling_ref() is old_wire:
            self._start_sibling_ref = weakref.ref(new_wire)
        elif self._stop_sibling_ref is not None and self._stop_sibling_ref() is old_wire:
            self._stop_sibling_ref = weakref.ref(new_wire)

    @_check_types.do
    def remove_wire(self, wire: "_wire_obj.Wire") -> None:
        """Forget *wire* on whichever side it is on (called when the lead is deleted).

        :param wire: The lead.
        :type wire: :class:`_wire_obj.Wire`
        """
        if self._start_sibling_ref is not None and self._start_sibling_ref() is wire:
            self._start_sibling_ref = None

        if self._stop_sibling_ref is not None and self._stop_sibling_ref() is wire:
            self._stop_sibling_ref = None

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        """Select or deselect the conductor. It has no view in any editor, so nothing is drawn selected and the editors are not
        told (their canvases hold objects that have views); what selecting it does is show its property control in the object
        editor and its entry in the object browser.

        :param flag: Whether it is selected.
        :type flag: bool
        """
        self._is_selected = flag
        mainframe = self.mainframe

        if flag:
            mainframe._selected_obj = self  # NOQA
            mainframe.object_browser.set_selected(self)
            QtCore.QTimer.singleShot(0, lambda: mainframe.editor_obj.set_selected(self))
        else:
            if mainframe._selected_obj is self:  # NOQA
                mainframe._selected_obj = None  # NOQA

            # queued before whatever is selected next, so that the next selection's own update comes after it
            QtCore.QTimer.singleShot(0, lambda: mainframe.editor_obj.set_selected(None))

    @_check_types.do
    def delete(self) -> None:
        """Let go of the leads, and take the conductor out of the schematic. The conductor is not deleted on its own: its row goes
        with the cable, and it has no view, tree item or registry entry to remove.
        """
        if self._run is not None:
            self._run.delete()

        self._run = None
        self._deleted = True
        self._start_sibling_ref = None
        self._stop_sibling_ref = None
