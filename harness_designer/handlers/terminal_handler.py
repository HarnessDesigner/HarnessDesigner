# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import terminal as _terminal
from ..objects import cavity as _cavity
from ..objects import housing as _housing
from ..gl import materials as _materials
from .. import config as _config


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


Config = _config.Config.colors


def _get_compat_object_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _cavity.Cavity | _housing.Housing | None:

    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, (_cavity.Cavity, _housing.Housing)):
        return selected

    return None


class AddTerminalHandler(_handler_base.HandlerBase):
    obj: _terminal.Terminal = None

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

        self.part = mainframe.project.gtables.terminals_table[part_id]
        part_number = self.part.part_number

        self._preview_material = _materials.Plastic(Config.add_object.preview_color)
        self._wire_highlight_material = _materials.Plastic(Config.add_object.wire_highlight)
        self._cavity_highlight_material = _materials.Plastic(Config.add_object.cavity_highlight)

        compat_housings = mainframe.project.gtables.housings_table.get_compat(terminal=part_number)
        compat_housings.extend(self.part.compat_housings)
        self.compat_housings = list(set(compat_housings))

        for housing in mainframe.project.housings:
            if housing.db_obj.db_id in self.compat_housings:
                housing.identify([0.3, 1.0, 0.3, 1.0])
            else:
                housing.identify([1.0, 0.6549, 0.0, 1.0])

        for cavity in mainframe.project.cavities:
            cavity.identify([0.3, 1.0, 0.3, 1.0])

    def release_capture(self) -> None:
        raise NotImplementedError

    def finalize(self, mouse_pos: _point.Point):
        for housing in self.mainframe.project.housings:
            housing.identify(None)

        for cavity in self.mainframe.project.cavities:
            cavity.identify(None)

        if not self.is_active:
            return

        obj = _get_compat_object_at_mouse(mouse_pos, self.camera)

        if obj is None:
            return

        if isinstance(obj, _cavity.Cavity):
            position3d = obj.obj3d.position
            position2d = obj.obj2d.position if obj.obj2d else None
            cavity_id = obj.db_obj.db_id
        elif isinstance(obj, _housing.Housing):
            position3d = obj.obj3d.position
            position2d = obj.obj2d.position if obj.obj2d else None
            cavity_id = None
        else:
            return

        p3d = self.ptables.pjt_points3d_table.insert(
            position3d.x, position3d.y, position3d.z)

        p2d = None
        if position2d is not None:
            p2d = self.ptables.pjt_points2d_table.insert(
                position2d.x, position2d.y)

        p2d_id = p2d.db_id if p2d is not None else None

        terminal_db = self.ptables.pjt_terminals_table.insert(
            self.part_id, p2d_id, p3d.db_id, cavity_id)

        angle = _angle.Angle()
        angle_delta = angle - terminal_db.angle3d
        angle = terminal_db.angle3d
        angle += angle_delta

        terminal = _terminal.Terminal(self.mainframe, terminal_db)

        self.mainframe.project.add_terminal(terminal)

    def start(self, mouse_pos: _point.Point):
        self.finalize(mouse_pos)
