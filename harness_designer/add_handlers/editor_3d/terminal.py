# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive cavity-snapping terminal placement for the 3D editor.

Ported from ``handlers.terminal_handler.AddTerminalHandler`` -- only its
Mode 2 ("housing given, snap to that housing's own empty cavities") and
Mode 3 ("nothing given, snap to any compatible cavity in the project")
ever need an interactive session; Mode 1 (housing AND cavity both given)
finalizes synchronously inside ``objects.objects_3d.terminal.Terminal.
start_add`` itself and never arms one of these at all -- see that
classmethod's own docstring.

The male/female positioning geometry (``_male_terminal_position``/
``_female_terminal_position``/``_resolve_is_male``) stays put in
``handlers.terminal_handler`` and is imported from there rather than
duplicated -- it's also used by ``objects.objects_3d.terminal.Terminal.
_set_model`` (``reposition_from_model``, once a first-time model
download completes), independent of which placement flow created the
terminal.
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from ...handlers import handler_base as _handler_base
from ...handlers import terminal_handler as _terminal_handler
from ... import utils as _utils
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


class Terminal(_base.AddHandlerBase):
    """Cavity-snapping terminal placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part,
        project_cavities: list, is_male: bool
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part = part
        self._project_cavities = project_cavities
        self._is_male = is_male
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
        objects = []
        positions = []

        for cavity in self._project_cavities:
            if not cavity.is_in_3dview:
                continue

            if self._is_male:
                x, y, z = _terminal_handler._male_terminal_position(self._part, cavity.db_obj)  # NOQA
            else:
                x, y, z = _terminal_handler._female_terminal_position(self._part, cavity.db_obj)  # NOQA

            positions.append(_point.Point(x, y, z))
            objects.append(cavity)

        return _utils.SnapPool(objects, positions)

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        snap_pool = self.snap_pool
        world_pos = self.camera.get_position_on_focal_plane(mouse_pos)
        snapped = snap_pool.query(world_pos)

        prev_snapped = self._snapped

        if snapped is None:
            point = world_pos
            self._snapped = None

            if prev_snapped is not None:
                _handler_base.HandlerBase.reset_angle(self.target)
        else:
            if self._is_male:
                x, y, z = _terminal_handler._male_terminal_position(self._part, snapped.db_obj)  # NOQA
            else:
                x, y, z = _terminal_handler._female_terminal_position(self._part, snapped.db_obj)  # NOQA

            point = _point.Point(x, y, z)
            self._snapped = snapped

            if prev_snapped is not snapped:
                _handler_base.HandlerBase.set_angle_from_cavity(self.target, snapped.db_obj)

        position = self.target.db_obj.position3d
        position += point - position

    @_check_types.do
    def _finalize(self) -> None:
        if self._snapped is None:
            return

        for cavity in self._project_cavities:
            cavity.identify(None)

        self.target.db_obj.cavity_id = self._snapped.db_obj.db_id
        _handler_base.HandlerBase.set_angle_from_cavity(self.target, self._snapped.db_obj)

        self.target.identify(None)
        self.mainframe.project.add_terminal(self.target)

        self._finalized = True

    @_check_types.do
    def cancel(self) -> None:
        for cavity in self._project_cavities:
            cavity.identify(None)

        if self.target is not None:
            self.target.identify(None)
            self.target.delete()

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
