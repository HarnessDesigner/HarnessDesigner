# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..geometry import angle as _angle
from ..objects import seal as _seal
from ..objects import terminal as _terminal
from ..objects import housing as _housing
from ..objects import cavity as _cavity
from ..gl import materials as _materials
from .. import config as _config
from .. import color as _color


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


def _get_compat_object_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _terminal.Terminal | _housing.Housing | _cavity.Cavity | None:

    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, (_terminal.Terminal, _housing.Housing, _cavity.Cavity)):
        return selected

    return None


class AddSealHandler(_handler_base.HandlerBase):
    obj: _seal.Seal = None

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._terminal_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.terminal_highlight))
        self._housing_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.housing_highlight))
        self._cavity_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.cavity_highlight))

        self.part = mainframe.project.gtables.seals_table[part_id]
        part_number = self.part.part_number

        self.compat_terminals = mainframe.project.gtables.terminals_table.get_compat(seal=part_number)
        self.compat_terminals.extend(self.part.compat_terminals)

        if self.part.o_dia:
            self.compat_housings = None

        else:
            self.compat_housings = mainframe.project.gtables.housings_table.get_compat(seal=part_number)
            self.compat_housings.extend(self.part.compat_housings)

            self.compat_housings = list(set(self.compat_housings))

            for housing in mainframe.project.housings:
                if housing.db_obj.db_id in self.compat_housings:
                    housing.identify([0.3, 1.0, 0.3, 1.0])
                else:
                    housing.identify([1.0, 0.6549, 0.0, 1.0])

        self.compat_terminals = list(set(self.compat_terminals))

        for cavity in mainframe.project.cavities:
            cavity.identify([1.0, 0.6549, 0.0, 1.0])

        for terminal in mainframe.project.terminals:
            if terminal.db_obj.db_id in self.compat_terminals:
                terminal.identify([0.3, 1.0, 0.3, 1.0])
            else:
                terminal.identify([1.0, 0.6549, 0.0, 1.0])

    def release_capture(self) -> None:
        raise NotImplementedError

    def finalize(self, mouse_pos: _point.Point):
        for housing in self.mainframe.project.housings:
            housing.identify(None)

        for cavity in self.mainframe.project.cavities:
            cavity.identify(None)

        for terminal in self.mainframe.project.terminals:
            terminal.identify(None)

        if not self.is_active:
            return

        obj = _get_compat_object_at_mouse(mouse_pos, self.camera)

        if obj is None:
            return

        if isinstance(obj, _terminal.Terminal):
            position = obj.obj3d.seal_position
            angle = obj.obj3d.angle
            terminal_id = obj.db_obj.db_id
            housing_id = None
            cavity_id = None

        elif isinstance(obj, _cavity.Cavity):
            position = obj.obj3d.seal_position
            angle = obj.obj3d.angle
            cavity_id = obj.db_obj.db_id
            housing_id = None
            terminal_id = None

        elif isinstance(obj, _housing.Housing):
            position = obj.obj3d.seal_position
            angle = _angle.Angle()
            housing_id = obj.db_obj.db_id
            cavity_id = None
            terminal_id = None

        else:
            return

        seal = self.ptables.pjt_seals_table.insert(
            self.part_id, position.db_id[:-2], housing_id=housing_id,
            terminal_id=terminal_id, cavity_id=cavity_id)

        angle_delta = angle - seal.angle3d
        angle = seal.angle3d
        angle += angle_delta

        seal = _seal.Seal(self.mainframe, seal)

        self.mainframe.project.add_seal(seal)

    def start(self, mouse_pos: _point.Point):
        self.finalize(mouse_pos)
