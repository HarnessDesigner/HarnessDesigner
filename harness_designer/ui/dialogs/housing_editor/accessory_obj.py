# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .... import objects as _objects
from ....objects.objects3d import base3d as _base3d
from ....geometry import point as _point
from ....geometry import angle as _angle
from ....gl import materials as _materials
from .... import color as _color
from ....shapes import sphere as _sphere


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor
    from ....database.global_db import housing as _housing


class HousingAccessory(_objects.ObjectBase):
    obj3d: "HousingAccessory3D" = None

    def __init__(self, parent: "_housing_editor.HousingEditorDialog",
                 position: _point.Point, color: _color.Color):

        super().__init__(parent, None)
        self.dialog = parent
        self.obj3d = HousingAccessory3D(self, position, color)
        self.obj2d = None

        parent.add_object(self)


class HousingAccessory3D(_base3d.Base3D):
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: HousingAccessory,
                 position: _point.Point, color: _color.Color):

        self.dialog = parent.dialog

        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        scale = _point.Point(3.0, 3.0, 3.0)

        parent.dialog.context.acquire()
        vbo = _sphere.create_vbo()
        vbo.acquire()

        material = _materials.Plastic(color)

        _base3d.Base3D.__init__(self, parent, None, vbo, angle,
                                position, scale, material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.8, 0.8, 0.2, 0.99))

        self._is_visible = True
        self.editor3d.Refresh(False)
        parent.dialog.context.release()

    def _update_position(self, position: _point.Point):
        super()._update_position(position)
        self.dialog.canvas.Refresh()
