from typing import TYPE_CHECKING

from . import handler_base as _handler_base

from ..geometry import point as _point
from ..geometry import angle as _angle
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import cpa_lock as _cpa_lock
from ..objects import housing as _housing


if TYPE_CHECKING:
    from ..gl.canvas3d import camera as _camera
    from .. import ui as _ui


def _get_compat_object_at_mouse(
    mouse_pos: _point.Point,
    camera: "_camera.Camera"
) -> _housing.Housing | None:

    selected = _object_picker.find_object(mouse_pos, camera.objects_in_view, camera)

    if isinstance(selected, _housing.Housing):
        return selected

    return None


class AddCPALockHandler(_handler_base.HandlerBase):

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        super().__init__(mainframe, part_id)

        self.part = mainframe.project.gtables.cpa_locks_table[part_id]
        part_number = self.part.part_number

        compat_housings = mainframe.project.gtables.housings_table.get_compat(seal=part_number)
        compat_housings.extend(self.part.compat_housings)

        self.compat_housings = list(set(compat_housings))

        for housing in mainframe.project.housings:
            if housing.db_obj.db_id in self.compat_housings:
                housing.identify([0.3, 1.0, 0.3, 1.0])
            else:
                housing.identify([1.0, 0.6549, 0.0, 1.0])

    def finalize(self, mouse_pos: _point.Point):
        for housing in self.mainframe.project.housings:
            housing.identify(None)

        if not self.is_active:
            return

        obj = _get_compat_object_at_mouse(mouse_pos, self.camera)

        if obj is None:
            return

        position = obj.obj3d.seal_position
        angle = _angle.Angle()
        housing_id = obj.db_obj.db_id

        cpa_lock = self.ptables.pjt_cpa_locks_table.insert(
            self.part_id, position.db_id[:-2], housing_id=housing_id)

        angle_delta = angle - cpa_lock.angle3d
        angle = cpa_lock.angle3d
        angle += angle_delta

        cpa_lock = _cpa_lock.CPALock(self.mainframe, cpa_lock)

        self.mainframe.project.add_cpa_lock(cpa_lock)

    def start(self, mouse_pos: _point.Point):
        self.finalize(mouse_pos)

