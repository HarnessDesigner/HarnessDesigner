# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .... import objects as _objects
from ....objects.objects3d import base3d as _base3d
from ....geometry import point as _point
from ....geometry import angle as _angle
from ...widgets import float_ctrl as _float_ctrl
from .. import error as _error_dialog
from ....shapes import box as _box
from ....gl import vbo as _vbo
from ....gl import materials as _materials
from .... import color as _color
from .... import utils as _utils


if TYPE_CHECKING:
    from ....database.global_db import housing as _housing
    from . import housing_editor as _housing_editor


class Housing(_objects.ObjectBase):
    """Represent a housing in :mod:`harness_designer.ui.dialogs.housing_editor.housing_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj3d: "Housing3D" = None

    def __init__(self, parent: "_housing_editor.HousingEditorDialog",
                 housing: "_housing.Housing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing_editor.HousingEditorDialog`
        :param housing: Value for ``housing``.
        :type housing: :class:`_housing.Housing`
        """

        super().__init__(parent, housing)
        self.dialog = parent
        self.obj3d = Housing3D(self, housing)

        parent.add_object(self)


class Housing3D(_base3d.Base3D):
    """Represent a housing 3D in :mod:`harness_designer.ui.dialogs.housing_editor.housing_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_housing.Housing" = None

    def __init__(self, parent: Housing, db_obj: "_housing.Housing"):
        """Initialise the :class:`Housing3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_housing.Housing`
        """
        self.dialog: "_housing_editor.HousingEditorDialog" = parent.dialog
        self.db_obj = db_obj

        parent.dialog.context.acquire()

        self._angle = db_obj.angle3d
        self._position = _point.Point(0.0, 0.0, 0.0)
        model = db_obj.model3d

        if model is None:
            length = db_obj.length
            width = db_obj.width
            height = db_obj.height

            parent.dialog.mainframe.status_bar.showMessage()

            if 0.0 in (length, width, height):
                length_ctrl = _float_ctrl.FloatCtrl(None, 'Length',
                                                    0.01, 500.0, 0.01)

                width_ctrl = _float_ctrl.FloatCtrl(None, 'Width',
                                                   0.01, 500.0, 0.01)

                height_ctrl = _float_ctrl.FloatCtrl(None, 'Height',
                                                    0.01, 500.0, 0.01)

                length_ctrl.SetValue(length)
                width_ctrl.SetValue(width)
                height_ctrl.SetValue(height)

                dlg = _error_dialog.ErrorDialog(
                    parent.dialog.mainframe,
                    'Dimensions are not valid.\n\nPlease set correct dimensions.',
                    'Dimension Error', length_ctrl, width_ctrl, height_ctrl)

                while 0.0 in (length, width, height):
                    dlg.exec()
                    length = length_ctrl.GetValue()
                    width = width_ctrl.GetValue()
                    height = height_ctrl.GetValue()

                db_obj.length = length
                db_obj.width = width
                db_obj.height = height

            scale = _point.Point(width, height, length)
            vbo = _box.create_vbo()
            position3d = _point.Point(0.0, 0.0, 0.0)
            angle3d = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        else:
            scale = model.scale
            angle3d = model.angle3d
            position3d = model.position3d
            vbo = _vbo.create_model_vbo(model)
            if vbo is None:
                vbo = _box.create_vbo()
                scale = _point.Point(1.0, 1.0, 1.0)

        vbo.acquire()

        material = _materials.Plastic(
            _color.Color(0.6, 0.6, 0.8, 1.0))

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle3d, position3d, scale, material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.3, 0.8, 0.3, 1.0))

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
