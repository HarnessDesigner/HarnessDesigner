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
    """Represent a housing accessory in :mod:`harness_designer.ui.dialogs.housing_editor.accessory_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj3d: "HousingAccessory3D" = None

    def __init__(self, parent: "_housing_editor.HousingEditorDialog",
                 position: _point.Point, color: _color.Color):
        """Initialise the :class:`HousingAccessory` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing_editor.HousingEditorDialog`
        :param position: Position value.
        :type position: :class:`_point.Point`
        :param color: Value for ``color``.
        :type color: :class:`_color.Color`
        """

        super().__init__(parent, None)
        self.dialog = parent
        self.obj3d = HousingAccessory3D(self, position, color)
        self.obj2d = None

        parent.add_object(self)


class HousingAccessory3D(_base3d.Base3D):
    """Represent a housing accessory 3D in :mod:`harness_designer.ui.dialogs.housing_editor.accessory_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: HousingAccessory,
                 position: _point.Point, color: _color.Color):
        """Initialise the :class:`HousingAccessory3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`HousingAccessory`
        :param position: Position value.
        :type position: :class:`_point.Point`
        :param color: Value for ``color``.
        :type color: :class:`_color.Color`
        """

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
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        super()._update_position(position)
        self.dialog.canvas.Refresh()
