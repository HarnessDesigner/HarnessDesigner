# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Single-click housing placement for the schematic editor.

Mirrors ``add_handlers.editor_3d.housing.Housing`` -- a housing floats
freely in the schematic view too (no attach targets), so this is the
same simplest-possible add session, just following the cursor across
the schematic's own flat (Y=0) plane instead of the 3D camera's focal
plane.
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects


class Housing(_base.AddHandlerBase):
    """Single-click housing placement -- see the module docstring."""

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase"):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera
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
            self._follow(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._follow(current_pos)

            self.mainframe.project.add_housing(self.target)
            self.target.db_obj.update_cavities()
            self.target.obj3d.match_cavity_surfaces()

            self._finalized = True
            return True

        return False

    @_check_types.do
    def _follow(self, mouse_pos: _point.Point) -> None:
        world_pos = self.camera.screen_to_world(mouse_pos)
        self.target.objschematic.move_to(world_pos.x, world_pos.z)

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
