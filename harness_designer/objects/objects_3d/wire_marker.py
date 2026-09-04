# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...gl.canvas_base import interaction as _interaction
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color
from ... import logger as _logger
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker
    from ...database.project_db import pjt_wire as _pjt_wire


Config = _config.Config.editor_3d


class WireMarker(_base_3d.Base3D):
    """Represent a wire marker in :mod:`harness_designer.objects.objects_3d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker" = None

    # Sits on/inside its wire's own OBB by design -- see Base3D._pick_priority.
    _pick_priority = 1

    @_check_types.do
    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part
            position = db_obj.position3d
            wire = db_obj.wire

            # Bound by whichever of the wire's sub-segments (start<->first
            # waypoint, waypoint<->waypoint, ..., last waypoint<->stop) the
            # marker actually sits on -- a bent wire's own start/stop
            # endpoints alone would put the marker on the wrong straight
            # chord (see _segment_for_point).
            wire_p1, wire_p2 = self._segment_for_point(wire, position)

            # self._position is the marker's CENTER, and the marker itself
            # spans self._marker_length along the wire, so its center can
            # never come closer to either endpoint than half that length --
            # otherwise it hangs off the end of a short enough wire. _buffer
            # adds a further 3mm of clearance on top of that half-length.

            diameter = wire.part.od_mm

            self._marker_length = diameter * 5.0

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

            angle = _angle.Angle.from_points(wire_p2, wire_p1)

            color = db_obj.part.color.ui
            material = _materials.Plastic(color)

            color = _color.Color(0.05, 0.05, 0.05, 1.0)

            length = self._marker_length

            if wire.has_stripe:
                scale = _point.Point(diameter + 0.26, diameter + 0.26, length)
            else:
                scale = _point.Point(diameter + 0.05, diameter + 0.05, length)

            vbo = _cylinder.create_vbo()

            label_material = _materials.Plastic(color)
            self._p1 = wire_p1
            self._p2 = wire_p2

            wire_p1.bind(self._update_position)
            wire_p2.bind(self._update_position)

            super().__init__(parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wire_markers

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @staticmethod
    @_check_types.do
    def _segment_for_point(
        wire: "_pjt_wire.PJTWire", position: _point.Point
    ) -> tuple[_point.Point, _point.Point]:
        """Return the (p1, p2) Points bounding whichever sub-segment of
        *wire*'s current path -- start, through each interior waypoint in
        idx order, to stop -- *position* sits closest to.

        Mirrors objects_3d.mixins.wire_type.WireTypeMixin._segments'/
        _point_on_wire's own walk over the same start->waypoints->stop
        path, needed here as a standalone helper because a WireMarker
        binds directly to a PJTWire row, not to that wire's own 3D facade
        object.
        """
        points = [wire.start_position3d]
        for waypoint in wire.waypoints3d:
            points.append(waypoint.point)
        points.append(wire.stop_position3d)

        best_pair = (points[0], points[1])
        best_dist = None

        for p1, p2 in zip(points, points[1:]):
            seg = p2.as_numpy - p1.as_numpy
            seg_len_sq = float(np.dot(seg, seg))
            if seg_len_sq < 1e-12:
                continue

            t = max(0.0, min(1.0, float(np.dot(
                position.as_numpy - p1.as_numpy, seg)) / seg_len_sq))
            closest = p1.as_numpy + t * seg
            dist = float(np.sum((position.as_numpy - closest) ** 2))

            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_pair = (p1, p2)

        return best_pair

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
                'Wire marker: wire too short to fit marker '
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
        callback in __init__ *and* Base3D binds it to the marker's own
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
            # Storing a percentage instead of an absolute distance means
            # the wire endpoint-moved branch below never has to clamp --
            # _point_for_percent always returns an in-range point.
            projected = line.project_to_line(position)

            self._percent = self._percent_for_point(line, projected)
            new_position = self._point_for_percent(line, self._percent)

            delta = new_position - position
            with position:
                position += delta

            self._o_position = position.copy()

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

            self._o_position = self._position.copy()

            angle = _angle.Angle.from_points(self._p2, self._p1)
            self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh()

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
        caller is responsible for picking the correct new wire (the
        marker's own position doesn't move, so which half it now
        belongs to is a geometry question, not something this method
        can answer on its own) and persisting ``db_obj.wire_id``.
        """
        self._p1.unbind(self._update_position)
        self._p2.unbind(self._update_position)

        self._p1, self._p2 = self._segment_for_point(wire_db_obj, self._position)

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

        self._o_position = self._position.copy()

        angle = _angle.Angle.from_points(self._p2, self._p1)
        self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh()

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMarkerMenu(self.mainframe.editor3d.editor, self)

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Along-the-wire drag -- overrides Base3D's generic single-
        position drag so the specific WireMarker handler (a rotated,
        wire-aligned arrow gizmo instead of the default axis-aligned one;
        see drag_handlers.editor_3d.wire_marker's own docstring) gets
        armed instead of the generic one. The actual along-the-wire
        constraint is enforced by this object's own _update_position, not
        the handler -- it applies a plain unlocked delta and the position
        callback re-projects it back onto the wire.
        """
        if self._active_handler is not None:
            if interaction_type is _interaction.MouseInteraction.MOVE:
                self._active_handler(current_pos - last_pos, current_pos)
                return True

            if interaction_type is _interaction.MouseInteraction.LEFT_UP:
                self._active_handler.delete()
                self._active_handler = None
                # No real drag happened -- let a plain click-release fall
                # through to the default select/deselect toggle instead of
                # being eaten here (see objects_3d.base_3d.handle_interaction).
                return had_motion

            return False

        if (
            interaction_type is not _interaction.MouseInteraction.LEFT_DOWN or
            clicked_object is not self.parent or
            self.mainframe.get_selected() is not self.parent or
            not self.can_drag()
        ):
            return False

        from ...drag_handlers.editor_3d import wire_marker as _drag_wire_marker  # NOQA -- avoid a cycle at import time (drag_handlers.editor_3d -> move_arrows -> base_3d)

        self._active_handler = _drag_wire_marker.WireMarker(self.editor3d.editor, self.parent)
        return True


class WireMarkerMenu(QMenu):
    """Represent a wire marker menu in :mod:`harness_designer.objects.objects_3d.wire_marker`.

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
            self.selected.editor3d.Refresh()

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_select(self):
        """Make this wire marker the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this wire marker as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this wire marker from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this wire marker's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
