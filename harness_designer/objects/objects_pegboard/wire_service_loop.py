# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from . import base_pegboard as _base_pegboard
from ...gl import materials as _materials
from ...shapes import cylinder_helix as _cylinder_helix
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_service_loop as _pjt_wire_service_loop
    from .. import wire_service_loop as _wire_service_loop


Config = _config.Config.editor_pegboard


# First-pass, fixed placement margin (mm) -- how far off a housing's own
# peg-board anchor a service loop is seeded when it has never been placed
# before (still sitting at the fresh-row (0.0, 0.0) default). Not derived
# from the housing's real footprint (would need its peg-board OBB, not
# available yet) -- a simple, adjustable placeholder until real collision/
# layout handling for peg-board service loops exists, matching the "we'll
# get to wire rendering later" scope this was built under.
_HOUSING_OFFSET_MM = 25.0


class WireServiceLoop(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a wire service loop -- reuses the
    real helix mesh the 3D editor's own ``shapes.cylinder_helix`` shape
    family uses (see ``objects.objects_3d.wire_service_loop.
    WireServiceLoop``), but with its own independently-built scale/
    material (never borrowed from ``obj3d`` -- see
    ``base_pegboard.BasePegboard.__init__``'s own docstring).

    Like the 3D version, only the start point is the render pivot
    (``BaseVar``/``BasePegboard`` know about that one ``Point`` alone);
    the stop point is this class's own concern. :meth:`_update_position`
    and :meth:`_update_angle` are overridden so that whenever the start
    point moves or the loop rotates -- from the object editor, a drag or
    the DB layer -- the derived stop point is recomputed to match, and a
    rotation pivots around the loop's own centroid rather than its start
    point.

    No collision avoidance/roll-slide resolution here yet (unlike the 3D
    version's extensive ``_resolve_collision`` machinery). Wire rendering
    in the peg-board view (so a loop's own attached wires show where they
    connect) is a separate, later piece of work.
    """
    _parent: "_wire_service_loop.WireServiceLoop" = None
    db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"

    @_check_types.do
    def __init__(self, parent: "_wire_service_loop.WireServiceLoop",
                 db_obj: "_pjt_wire_service_loop.PJTWireServiceLoop"):
        """Initialise the :class:`WireServiceLoop` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_service_loop.WireServiceLoop`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_service_loop.PJTWireServiceLoop`
        """

        # Y axis is honored -- start_position_pegboard already stores a
        # real x/y/z (pjt_points_pegboard has all 3 columns, see
        # PJTPointPegboard.point), no separate handling needed here.
        #
        # angle_pegboard starts at identity (fresh-row default), same as
        # housing/terminal's own -- unlike transition's fixed local mesh
        # convention (always confined to Z=0, so a single corrective
        # rotation is always correct), this mesh's "natural" coil
        # orientation isn't a simple fixed offset the way a straight
        # part's is (see shapes/cylinder_helix.py's own path-following
        # construction), so no seed rotation is applied here -- the user
        # rotates it to taste once, same as housing/terminal, rather
        # than this guessing at a default that might read backwards.
        #
        # The only time the wire service loops will be rendered is if
        # there is no boot or if the boot is not visible.
        self._part = db_obj.part

        # scale/material built fresh from the catalog part's own data,
        # mirroring objects_3d.wire_service_loop.WireServiceLoop.__init__'s
        # own construction exactly (diameter-derived scale, Plastic
        # material from the part's color) -- never borrowed from obj3d.
        diameter = self._part.od_mm
        scale = _point.Point(diameter, diameter, diameter)
        material = _materials.Plastic(self._part.color.ui)

        position = db_obj.start_position_pegboard
        position2 = db_obj.stop_position_pegboard

        # Must exist before BaseVar.__init__ binds the position/angle
        # callbacks below -- both overrides read it.
        self._last_centroid: np.ndarray | None = None

        with parent.mainframe.editor_pegboard.context:
            vbo = _cylinder_helix.create_vbo()

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=db_obj.angle_pegboard,
                position=position,
                scale=scale,
                material=material,
            )

        self._p1 = position
        self._p2 = position2

        # Always derive the stop point fresh from the start point/angle/
        # scale rather than trusting whatever was last persisted -- same
        # self-healing as the 3D version.
        self._last_centroid = self._world_centroid()
        self._sync_stop_position()

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # a service loop has no single position_pegboard the way housing/
        # terminal/transition/splice do (StartStopPositionPegboardMixin,
        # not PositionPegboardMixin), so key off the start point, same
        # "pick one" simplification splice.py uses for the same reason.
        self.point3d_id = db_obj.start_position_pegboard_id

        # Seed a sensible initial peg-board position -- placed close to
        # the housing its terminal is seated in, so the loop's own wires
        # stay visually near where they actually connect (only the first
        # time ever; position_pegboard starts at the (0.0, 0.0) fresh-row
        # default, same sentinel convention every other anchor type here
        # uses -- see housing.py's own comment on this).
        if self._position.x == 0.0 and self._position.z == 0.0:
            self._seed_position_near_housing()

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def _world_centroid(self) -> np.ndarray:
        """World-space centroid of the loop's own OBB -- the rotation pivot
        (see :meth:`_update_angle`), not the start/stop connection points.
        """
        centroid = self._vbo.local_obb.mean(axis=0)
        centroid = centroid * self._scale.as_numpy
        centroid = centroid @ self._angle
        centroid = centroid + self._position.as_numpy

        return centroid

    @_check_types.do
    def _sync_stop_position(self) -> None:
        """Recompute the derived stop point from the current start
        position, angle and scale -- the same scale/rotate/translate of
        the VBO's own endpoint that the render applies to the full mesh.
        """
        tmp = self._vbo.endpoint.copy()
        tmp *= self._scale
        tmp @= self._angle
        tmp += self._position

        self._p2 += tmp - self._p2

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """Keep the derived stop point in step with the start point, and
        the centroid baseline used by :meth:`_update_angle` current.
        """
        super()._update_position(position)
        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        """Rotate the loop around its own centroid, not its start point.

        The rendering pivot is always the start point, so pivoting around
        the centroid means compensating the start position by however far
        the centroid would otherwise move under the new angle -- applied
        *before* the base bookkeeping (OBB/AABB) runs against the corrected
        position. Only this object's own ``_update_position`` listener is
        unbound for that one write (so it isn't re-entered); anything else
        sharing this same ``Point`` (e.g. an attached wire's endpoint)
        still sees the move normally.
        """
        if self._last_centroid is not None:
            # Where the centroid would land if the position stayed put,
            # under the angle that was just applied.
            unshifted_centroid = self._world_centroid()
            delta = self._last_centroid - unshifted_centroid

            if not np.allclose(delta, 0.0, atol=1e-9):
                self._position.unbind(self._update_position)

                try:
                    self._position += _point.Point(*[float(v) for v in delta])
                finally:
                    self._position.bind(self._update_position)

        super()._update_angle(angle)

        self._sync_stop_position()
        self._last_centroid = self._world_centroid()

    @_check_types.do
    def _seed_position_near_housing(self) -> None:
        """Offset this loop's peg-board position a fixed margin
        (:data:`_HOUSING_OFFSET_MM`) from its terminal's housing's own
        peg-board anchor -- see the module docstring for why this is a
        simple placeholder rather than real footprint-aware placement.

        No-op if this loop's terminal can't be resolved (``db_obj.
        terminal`` -- matched via the 3D-side ``wire_point3d_id``, the
        terminal object itself is the same regardless of view) or that
        terminal isn't seated in a housing (a bare terminal has no
        housing to sit near).
        """
        terminal = self.db_obj.terminal
        if terminal is None:
            return

        cavity = terminal.cavity
        if cavity is None:
            return

        housing = cavity.housing
        if housing is None:
            return

        housing_pos = housing.position_pegboard
        self._position.x = float(housing_pos.x) + _HOUSING_OFFSET_MM
        self._position.z = float(housing_pos.z)
