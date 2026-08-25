# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Housing-snapping TPA lock placement for the 3D editor.

Ported from ``handlers.tpa_lock_handler.AddTPALockHandler`` -- same
shape as :class:`add_handlers.editor_3d.cover.Cover`, except a housing
carries up to two independent TPA lock slots (``tpa_lock1``/
``tpa_lock2``), so the free-placement snap has to pick whichever slot
is still open on each candidate housing.
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


class TPALock(_base.AddHandlerBase):
    """Housing-snapping TPA lock placement -- see the module docstring."""

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

            if housing.db_obj.tpa_lock1 is None:
                positions.append(housing.db_obj.tpa_lock_1_position3d)
                housings.append(housing)

            if housing.db_obj.tpa_lock2 is None:
                positions.append(housing.db_obj.tpa_lock_2_position3d)
                housings.append(housing)

        return _utils.SnapPool(housings, positions, threshold=10.0)

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
            if housing.db_obj.tpa_lock1 is None:
                point = housing.db_obj.tpa_lock_1_position3d
            else:
                point = housing.db_obj.tpa_lock_2_position3d

            self._snapped = housing

            if prev_snapped is not housing:
                _handler_base.HandlerBase.set_angle_from_housing(self.target, housing)

        position = self.target.obj3d.position
        delta = point - position
        position += delta

    @_check_types.do
    def _finalize(self) -> None:
        if self._housing is None:
            if self._snapped is None:
                return

            for housing in self.mainframe.project.housings:
                housing.identify(None)

            if self._snapped.db_obj.tpa_lock1 is None:
                point = self._snapped.db_obj.tpa_lock_1_position3d
                idx = 1
            else:
                point = self._snapped.db_obj.tpa_lock_2_position3d
                idx = 2

            self.target.db_obj.housing_id = self._snapped.db_obj.db_id
            point.attach(self.target.obj3d.position)
            self.target.db_obj.idx = idx

        self._finalized = True
        self.mainframe.project.add_tpa_lock(self.target)

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
