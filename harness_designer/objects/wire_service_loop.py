# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
import weakref

from . import ObjectBase as _ObjectBase
from .objects3d import wire_service_loop as _wire_service_loop_3d
from .objects2d import wire_service_loop as _wire_service_loop_2d
from .objectspeg import wire_service_loop as _wire_service_loop_peg
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from . import wire as _wire_obj


class WireServiceLoop(_ObjectBase):
    """Represent a wire service loop in :mod:`harness_designer.objects.wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _wire_service_loop_2d.WireServiceLoop = None
    obj3d: _wire_service_loop_3d.WireServiceLoop = None
    objpeg: _wire_service_loop_peg.WireServiceLoop = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop" = None

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop", project_load=False):
        """Initialise the :class:`WireServiceLoop` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _wire_service_loop_2d.WireServiceLoop(self, db_obj)
        self.obj3d = _wire_service_loop_3d.WireServiceLoop(self, db_obj)
        self.objpeg = _wire_service_loop_peg.WireServiceLoop(self, db_obj)

        # Sibling graph: a service loop always sits inline between exactly
        # two lengths of the same physical wire -- never a branch, never
        # directly against a terminal or splice -- so this is the same
        # fixed-pair shape as Splice's own through-pair, with no branch
        # list. Set together via set_siblings when this loop is placed
        # into an existing wire.
        self._start_sibling_ref = None
        self._stop_sibling_ref = None

        self.mainframe.add_object(self)

    @property
    @_check_types.do
    def start_sibling(self) -> "_wire_obj.Wire | None":
        return None if self._start_sibling_ref is None else self._start_sibling_ref()

    @property
    @_check_types.do
    def stop_sibling(self) -> "_wire_obj.Wire | None":
        return None if self._stop_sibling_ref is None else self._stop_sibling_ref()

    @_check_types.do
    def set_siblings(self, wire_a: "_wire_obj.Wire", wire_b: "_wire_obj.Wire") -> None:
        """Record *wire_a*/*wire_b* as this loop's two wire-facing ends.

        Both must be actual wires -- a service loop only ever sits inline
        on a single wire's own path, never directly against a terminal or
        splice. Which of the two goes on the start side vs. stop side is
        determined by matching against this loop's own
        ``start_position3d_id``/``stop_position3d_id``, same technique as
        ``objects.splice.Splice.set_siblings``.

        One-sided, same as Wire.set_sibling: callers are also responsible
        for calling ``wire.set_sibling(self, end)`` on each wire.

        :raises TypeError: if either argument isn't a Wire.
        """
        from . import wire as _wire

        for wire in (wire_a, wire_b):
            if not isinstance(wire, _wire.Wire):
                raise TypeError(
                    f'WireServiceLoop can only connect to wires, got {type(wire).__name__}')

        start_id = self.db_obj.start_position3d_id
        stop_id = self.db_obj.stop_position3d_id

        for wire in (wire_a, wire_b):
            w_start = wire.db_obj.start_position3d_id
            w_stop = wire.db_obj.stop_position3d_id

            if start_id in (w_start, w_stop):
                self._start_sibling_ref = weakref.ref(wire)
            elif stop_id in (w_start, w_stop):
                self._stop_sibling_ref = weakref.ref(wire)

    @_check_types.do
    def replace_wire(self, old_wire: "_wire_obj.Wire", new_wire: "_wire_obj.Wire") -> None:
        """Swap *old_wire* for *new_wire* on whichever side it's
        currently on, preserving position.

        Used when a wire attached to this loop gets forked or merged
        elsewhere along its length (handlers.wire_topology) -- this
        loop's own end of the relationship doesn't change, only which
        Wire object represents that end now.
        """
        if self._start_sibling_ref is not None and self._start_sibling_ref() is old_wire:
            self._start_sibling_ref = weakref.ref(new_wire)
        elif self._stop_sibling_ref is not None and self._stop_sibling_ref() is old_wire:
            self._stop_sibling_ref = weakref.ref(new_wire)

    @_check_types.do
    def delete(self):
        """Reconnect the two wires this loop sits between (undoing the
        fork handlers.wire_service_loop_handler made when it was placed)
        before actually deleting this loop -- see handlers.wire_topology.
        merge_wires. Only the handler's own cancel() did this before;
        deleting an already-placed loop (e.g. via its context menu) now
        does too.
        """
        wire_a = self.start_sibling
        wire_b = self.stop_sibling
        if wire_a is not None and wire_b is not None:
            from ..handlers import wire_topology as _wire_topology
            _wire_topology.merge_wires(self.mainframe.project, wire_a, wire_b)

        super().delete()
        self.mainframe.project.delete_wire_service_loop(self.db_obj.db_id)
        self.db_obj.delete()
