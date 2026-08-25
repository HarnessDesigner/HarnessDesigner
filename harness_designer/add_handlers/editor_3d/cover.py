# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Housing-snapping cover placement for the 3D editor.

Ported from ``handlers.cover_handler.AddCoverHandler``. Even the
housing-given case (the cover's position already shares the housing's
own ``cover_position3d`` point from the moment ``start_add`` builds it,
so nothing needs to move) still waits for a click to actually register
the cover with the project -- ``hover`` only ever moves anything in the
free-placement case.
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...handlers import handler_base as _handler_base
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects
    from ...objects import housing as _housing


class Cover(_base.AddHandlerBase):
    """Housing-snapping cover placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
        housing: "_housing.Housing | None", project_housings: list
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._housing = housing
        self._project_housings = project_housings
        self._snapped = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize()
            return True

        return False

    @property
    @_check_types.do
    def snap_pool(self):
        from ... import utils as _utils

        housings = []
        positions = []

        for housing in self._project_housings:
            if not housing.is_in_3dview:
                continue

            positions.append(housing.db_obj.cover_position3d)
            housings.append(housing)

        return _utils.SnapPool(housings, positions)

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        if self._housing is not None:
            return

        snap_pool = self.snap_pool
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        housing = snap_pool.query(world_pos)

        prev_snapped = self._snapped

        if housing is None:
            point = world_pos
            self._snapped = None

            if prev_snapped is not None:
                _handler_base.HandlerBase.reset_angle(self.target)
        else:
            point = housing.db_obj.cover_position3d
            self._snapped = housing

            if prev_snapped is not housing:
                _handler_base.HandlerBase.set_angle_from_housing(self.target, housing)

        position = self.target.db_obj.position3d
        delta = point - position
        position += delta

    @_check_types.do
    def _finalize(self) -> None:
        if self._housing is None:
            if self._snapped is None:
                return

            for housing in self.mainframe.project.housings:
                housing.identify(None)

            self._snapped.db_obj.cover_position3d.attach(self.target.db_obj.position3d)
            self.target.db_obj.housing_id = self._snapped.db_obj.db_id
            _handler_base.HandlerBase.set_angle_from_housing(self.target, self._snapped)

        self._finalized = True
        self.mainframe.project.add_cover(self.target)

    @_check_types.do
    def cancel(self) -> None:
        if self._housing is None:
            for housing in self.mainframe.project.housings:
                housing.identify(None)

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
