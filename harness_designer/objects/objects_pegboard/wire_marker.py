# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import logger as _logger
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker
    from ...database.project_db import pjt_wire as _pjt_wire


Config = _config.Config.editor_pegboard


class WireMarker(_base_pegboard.BasePegboard):
    """Peg-board representation of a wire marker -- a short cylinder
    riding on its wire's own peg-board path, positioned as a fixed
    percentage along the buffered (clear of both ends) usable range of
    the wire's ``start_position_pegboard``/``stop_position_pegboard``
    chord. Mirrors ``objects_3d.wire_marker.WireMarker`` almost exactly
    (same percent-based positioning/re-derivation math, same end-buffer
    reasoning), adapted for the peg board's own start/stop columns and
    with no independent ``angle_pegboard`` of its own -- like the 3D
    version, orientation is always derived fresh from the wire's current
    direction, never independently stored/user-set.

    No stripe-aware sizing bump (``objects_3d.wire_marker.WireMarker``'s
    own ``wire.has_stripe`` branch) -- ``objects_pegboard.wire.Wire`` has
    no stripe overlay at all (a 3D-only cosmetic refinement), so this
    always uses the plain no-stripe sizing.
    """
    db_obj: "_pjt_wire_marker.PJTWireMarker"

    @_check_types.do
    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """
        with parent.mainframe.editor_pegboard.context:
            self._part = db_obj.part
            position = db_obj.position_pegboard
            wire = db_obj.wire
            wire_p1 = wire.start_position_pegboard
            wire_p2 = wire.stop_position_pegboard

            # self._position is the marker's CENTER, and the marker itself
            # spans self._marker_length along the wire, so its center can
            # never come closer to either endpoint than half that length --
            # otherwise it hangs off the end of a short enough wire. _buffer
            # adds a further 3mm of clearance on top of that half-length.
            # Mirrors objects_3d.wire_marker.WireMarker.__init__ exactly.
            self._marker_length = 5.0
            self._buffer = self._marker_length / 2.0 + 3.0

            line = _line.Line(wire_p2, wire_p1)
            self._percent = 0.5

            if not self._wire_too_short(line.length()):
                self._percent = self._percent_for_point(line, position)

                buffered = self._point_for_percent(line, self._percent)
                delta = buffered - position
                with position:
                    position += delta

            angle = _angle.Angle.from_points(wire_p2, wire_p1)

            material = _materials.Plastic(self._part.color.ui)

            length = self._marker_length
            diameter = wire.part.od_mm
            scale = _point.Point(diameter + 0.05, diameter + 0.05, length)

            vbo = _cylinder.create_vbo()

            self._p1 = wire_p1
            self._p2 = wire_p2

            wire_p1.bind(self._update_position)
            wire_p2.bind(self._update_position)

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self.point3d_id = db_obj.position_pegboard_id

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

    @_check_types.do
    def _wire_too_short(self, length: float) -> bool:
        """See ``objects_3d.wire_marker.WireMarker._wire_too_short``."""
        minimum = self._marker_length + 6.0

        if length < minimum:
            _logger.error(
                'Wire marker (peg-board): wire too short to fit marker '
                f'(wire length {length:.2f}mm < minimum {minimum:.2f}mm) '
                '-- leaving wire marker position/angle unchanged.')
            return True

        return False

    @_check_types.do
    def _percent_for_point(self, line: _line.Line, point: _point.Point) -> float:
        """See ``objects_3d.wire_marker.WireMarker._percent_for_point``."""
        length = line.length()
        usable_length = length - (self._buffer * 2.0)

        raw_distance = _line.Line(line.p1, point).length()
        raw_distance = max(self._buffer, min(length - self._buffer, raw_distance))

        percent = (raw_distance - self._buffer) / usable_length
        return max(0.0, min(1.0, percent))

    @_check_types.do
    def _point_for_percent(self, line: _line.Line, percent: float) -> _point.Point:
        """See ``objects_3d.wire_marker.WireMarker._point_for_percent``."""
        length = line.length()
        usable_length = length - (self._buffer * 2.0)
        distance = percent * usable_length + self._buffer

        return line.point_from_start(distance)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """See ``objects_3d.wire_marker.WireMarker._update_position`` --
        same two-trigger reasoning (the marker dragged directly, or one
        of the wire's own peg-board endpoints moving), same db_id
        comparison to tell them apart.
        """
        line = _line.Line(self._p2, self._p1)

        if self._wire_too_short(line.length()):
            return

        if position.db_id == self._position.db_id:
            projected = line.project_to_line(position)

            self._percent = self._percent_for_point(line, projected)
            new_position = self._point_for_percent(line, self._percent)

            delta = new_position - position
            with position:
                position += delta

            self._o_position = position.copy()

        else:
            new_position = self._point_for_percent(line, self._percent)

            delta = new_position - self._position
            with self._position:
                self._position += delta

            self._o_position = self._position.copy()

            angle = _angle.Angle.from_points(self._p2, self._p1)
            self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

        self.pegboard.Refresh()

    @_check_types.do
    def rebind_wire(self, wire_db_obj: "_pjt_wire.PJTWire") -> None:
        """See ``objects_3d.wire_marker.WireMarker.rebind_wire`` -- same
        reasoning (a wire split creates two brand new rows, orphaning
        this marker's own bindings unless re-pointed explicitly).
        """
        self._p1.unbind(self._update_position)
        self._p2.unbind(self._update_position)

        self._p1 = wire_db_obj.start_position_pegboard
        self._p2 = wire_db_obj.stop_position_pegboard

        self._p1.bind(self._update_position)
        self._p2.bind(self._update_position)

        line = _line.Line(self._p2, self._p1)

        if self._wire_too_short(line.length()):
            return

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

        self.pegboard.Refresh()
