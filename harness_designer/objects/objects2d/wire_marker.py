# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMenu

from . import base2d as _base2d
from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ...shapes import cylinder as _cylinder
from ... import logger as _logger
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker
    from ...database.project_db import pjt_wire as _pjt_wire


# TODO: add render function


class WireMarker(_base2d.Base2D):
    """
    2D representation of a wire marker for schematic view

    Renders as a small colored cylinder band along the wire -- the same
    shared ``shapes/cylinder.py`` mesh ``objects2d/wire.py``'s ``Wire``
    (and ``objects3d/wire_marker.py``'s ``WireMarker``) use, since the
    ``schematic2d`` shader already does the full 3D transform before
    projecting to 2D -- sitting at a percentage along the wire's length,
    tracked and re-clamped as either the marker or the wire's own
    endpoints move. Structurally mirrors
    ``objects3d/wire_marker.py``'s ``WireMarker`` (percent-of-buffered-
    range tracking, wire-too-short guard, ``rebind_wire`` for a split
    wire), with one 2D-specific difference: its rotation is computed directly
    (``atan2(dx, dz)`` about world Y, same formula ``objects2d/wire.py``
    already uses and has verified against ``_rotate_about_y``) rather
    than via ``Angle.from_points``, whose axis convention isn't verified
    against this pipeline's 2D rotation contract.
    """
    _parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker" = None

    # Sits on/inside its wire's own OBB by design -- see
    # objects.objectsvar.base_var.BaseVar._pick_priority.
    _pick_priority = 1

    @_check_types.do
    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """
        with parent.mainframe.editor2d.editor.context:

            self._part = db_obj.part
            position = db_obj.position2d
            wire = db_obj.wire
            wire_p1 = wire.start_position2d
            wire_p2 = wire.stop_position2d

            # self._position is the marker's CENTER, and the marker itself
            # spans self._marker_length along the wire, so its center can
            # never come closer to either endpoint than half that length --
            # otherwise it hangs off the end of a short enough wire. _buffer
            # adds a further 3mm of clearance on top of that half-length.
            self._marker_length = 5.0
            self._buffer = self._marker_length / 2.0 + 3.0

            line = _line.Line(wire_p2, wire_p1)
            self._percent = 0.5

            if not self._wire_too_short(line.length()):
                self._percent = self._percent_for_point(line, position)

                # _percent_for_point already clamps to the buffered range --
                # snap the DB-backed position to match so a marker placed
                # (via click, midpoint fallback, etc.) too close to an end
                # starts buffered instead of only snapping in on the next
                # wire move.
                buffered = self._point_for_percent(line, self._percent)
                delta = buffered - position
                with position:
                    position += delta

            material = _materials.Generic(self._part.color.ui)

            diameter = wire.part.od_mm
            length = self._marker_length

            if wire.has_stripe:
                scale = _point.Point(diameter + 0.22, diameter + 0.22, length)
            else:
                scale = _point.Point(diameter + 0.05, diameter + 0.05, length)

            vbo = _cylinder.create_vbo()

            dx = wire_p2.x - wire_p1.x
            dz = wire_p2.z - wire_p1.z
            angle = _angle.Angle.from_euler(0.0, math.degrees(math.atan2(dx, dz)), 0.0)

            self._p1 = wire_p1
            self._p2 = wire_p2

            wire_p1.bind(self._update_position)
            wire_p2.bind(self._update_position)

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    @_check_types.do
    def _wire_too_short(self, length: float) -> bool:
        """Return whether ``length`` is too short to fit this marker plus
        its end buffer on each side, logging an error when it is.

        Callers must bail out (do nothing further) when this is True --
        :meth:`_percent_for_point`/:meth:`_point_for_percent` assume the
        wire is long enough and don't guard against it themselves.
        """
        minimum = self._marker_length + 6.0

        if length < minimum:
            _logger.error(
                'Wire marker (2D): wire too short to fit marker '
                f'(wire length {length:.2f}mm < minimum {minimum:.2f}mm) '
                '-- leaving wire marker position/angle unchanged.')
            return True

        return False

    @_check_types.do
    def _percent_for_point(self, line: _line.Line, point: _point.Point) -> float:
        """Return where ``point`` (assumed already on/near ``line``) sits
        as a percentage of the buffered usable range (0.0 = ``self._buffer``
        mm past ``line.p1``, 1.0 = ``self._buffer`` mm before ``line.p2``).
        Clamped, so a point outside the buffered range still yields a
        valid 0..1 percent instead of one that would push
        :meth:`_point_for_percent` past the buffer zone. Assumes the
        caller already checked :meth:`_wire_too_short`.
        """
        length = line.length()
        usable_length = length - (self._buffer * 2.0)

        raw_distance = _line.Line(line.p1, point).length()
        raw_distance = max(self._buffer, min(length - self._buffer, raw_distance))

        percent = (raw_distance - self._buffer) / usable_length
        return max(0.0, min(1.0, percent))

    @_check_types.do
    def _point_for_percent(self, line: _line.Line, percent: float) -> _point.Point:
        """Return the point on ``line`` at ``percent`` through the
        buffered usable range -- see :meth:`_percent_for_point`. Assumes
        the caller already checked :meth:`_wire_too_short`.
        """
        length = line.length()
        usable_length = length - (self._buffer * 2.0)
        distance = percent * usable_length + self._buffer

        return line.point_from_start(distance)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Update the position.

        Two independent triggers land here (both endpoints bind this same
        callback in __init__ *and* Base2D binds it to the marker's own
        position): the marker being dragged directly, or one of the
        wire's endpoints moving. They're told apart by whose db_id the
        moved point matches.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        line = _line.Line(self._p2, self._p1)

        if self._wire_too_short(line.length()):
            return

        if position.db_id == self._position.db_id:
            # The marker itself moved -- snap it back onto the line
            # (respecting the end buffer) and remember its new position
            # as a percentage of the wire's current buffered range.
            projected = line.project_to_line(position)

            self._percent = self._percent_for_point(line, projected)
            new_position = self._point_for_percent(line, self._percent)

            delta = new_position - position
            with position:
                position += delta

        else:
            # A wire endpoint moved. self._p1/self._p2 are live-bound to
            # those same Points, so by the time this fires they already
            # reflect the NEW endpoint positions -- there is no "old"
            # state left to rotate away from. Re-derive the marker's
            # position from its fixed percentage along the current line.
            new_position = self._point_for_percent(line, self._percent)

            delta = new_position - self._position
            with self._position:
                self._position += delta

            dx = self._p2.x - self._p1.x
            dz = self._p2.z - self._p1.z
            self._angle.y = math.degrees(math.atan2(dx, dz))

        self._compute_obb()
        self._compute_aabb()

        self.editor2d.Refresh()

    @_check_types.do
    def rebind_wire(self, wire_db_obj: "_pjt_wire.PJTWire") -> None:
        """Reattach this marker to a different :class:`PJTWire` row.

        Needed when the wire this marker sits on gets split by a new
        wire layout point (see ``handlers.wire_layout_handler
        ._split_wire_at_point``): that doesn't just move the wire's
        endpoints, it deletes the original ``pjt_wires`` row outright
        and creates two brand new ones, so this marker's ``wire_id`` and
        its ``_update_position`` bindings (still pointing at the old
        row's endpoints) would otherwise be silently orphaned. The
        caller is responsible for picking the correct new wire and
        persisting ``db_obj.wire_id`` -- mirrors
        ``objects3d/wire_marker.py``'s ``WireMarker.rebind_wire`` exactly,
        though nothing calls this one yet (only the 3D side is wired
        into ``handlers/wire_layout_handler.py``/
        ``handlers/wire_service_loop_handler.py`` currently).
        """
        self._p1.unbind(self._update_position)
        self._p2.unbind(self._update_position)

        self._p1 = wire_db_obj.start_position2d
        self._p2 = wire_db_obj.stop_position2d

        self._p1.bind(self._update_position)
        self._p2.bind(self._update_position)

        line = _line.Line(self._p2, self._p1)

        if self._wire_too_short(line.length()):
            return

        # The marker itself didn't physically move -- just re-derive
        # percent/position/angle from where it already is against the
        # new (shorter) line.
        self._percent = self._percent_for_point(line, self._position)
        new_position = self._point_for_percent(line, self._percent)

        delta = new_position - self._position
        with self._position:
            self._position += delta

        dx = self._p2.x - self._p1.x
        dz = self._p2.z - self._p1.z
        self._angle.y = math.degrees(math.atan2(dx, dz))

        self._compute_obb()
        self._compute_aabb()

        self.editor2d.Refresh()


class WireMarkerMenu(QMenu):
    """Represent a wire marker menu in :mod:`harness_designer.objects.objects2d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`WireMarkerMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Set Label')
        action.triggered.connect(self.on_set_label)

        action = self.addAction('Flip Label')
        action.triggered.connect(self.on_flip_label)

        self.addSeparator()

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_set_label(self):
        """Edit the marker label."""
        @_check_types.do
        def _do():
            from PySide6.QtWidgets import QInputDialog

            mainframe = self.selected.mainframe
            current = self.selected.db_obj.label or ''

            label, ok = QInputDialog.getText(
                mainframe, 'Set Label', 'Label:', text=current)

            if not ok or label == current:
                return

            self.selected.db_obj.label = label
            self.selected.editor2d.Refresh()

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_flip_label(self):
        """Handle the flip label event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
