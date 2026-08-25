# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Cavity-pick terminal placement for the schematic editor.

Unlike the 3D editor, a schematic terminal has no free position of its
own to preview -- its rendered position is entirely derived from its
seated cavity's own row in the owning Housing's layout (see
``objects_schematic.housing.Housing._layout_children``), so there is
nothing meaningful to show following the cursor before a cavity is
actually picked. The placeholder built by
``objects.objects_schematic.terminal.Terminal.start_add`` stays hidden
the whole session; a click on any of this session's own eligible empty
cavities (every empty cavity project-wide, or -- when *housing* was
given -- just that housing's own, mirroring 3D Terminal's own Mode 2 vs
Mode 3 distinction) seats it there immediately, computing the same
male/female 3D attach position 3D's own Mode 1/2/3 already do (reused
directly, not duplicated).
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_schematic import canvas as _canvas
    from ... import objects as _objects
    from ...objects import housing as _housing


class Terminal(_base.AddHandlerBase):
    """Cavity-pick terminal placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part,
        housing: "_housing.Housing | None"
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part = part
        self._housing = housing
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.objschematic

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

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize(current_pos)
            return True

        return False

    @_check_types.do
    def _finalize(self, mouse_pos: _point.Point) -> None:
        from ...objects.objects_schematic import cavity as _cavity_schematic

        picked = _object_picker.find_object(
            mouse_pos, self.mainframe.editor2d.editor.objects,
            self.camera, self._get_view_object)

        if not isinstance(picked, _cavity_schematic.Cavity):
            return

        cavity_obj = picked.parent

        if cavity_obj.db_obj.terminal is not None:
            return

        if self._housing is not None and cavity_obj.db_obj.housing.db_id != self._housing.db_obj.db_id:
            return

        self._seat(cavity_obj)
        self._finalized = True

    @_check_types.do
    def _seat(self, cavity_obj) -> None:
        from ...handlers import terminal_handler as _terminal_handler
        from ...handlers import handler_base as _handler_base

        pjt_cavity = cavity_obj.db_obj
        is_male = _terminal_handler._resolve_is_male(self._part, pjt_cavity.housing.part)  # NOQA

        if is_male:
            tx, ty, tz = _terminal_handler._male_terminal_position(self._part, pjt_cavity)  # NOQA
        else:
            tx, ty, tz = _terminal_handler._female_terminal_position(self._part, pjt_cavity)  # NOQA

        target_point = _point.Point(tx, ty, tz)
        position = self.target.db_obj.position3d
        position += target_point - position

        self.target.db_obj.cavity_id = pjt_cavity.db_id
        _handler_base.HandlerBase.set_angle_from_cavity(self.target, pjt_cavity)

        self.target.obj3d.is_visible = True
        self.mainframe.project.add_terminal(self.target)

    @_check_types.do
    def cancel(self) -> None:
        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
