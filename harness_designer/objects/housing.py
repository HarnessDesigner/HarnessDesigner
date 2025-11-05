from typing import TYPE_CHECKING

from . import base as _base

if TYPE_CHECKING:
    from ..database.global_db import housing as _housing
    from ..database.project_db import pjt_housing as _pjt_housing
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


class Housing(_base.ObjectBase):
    _part: "_housing.Housing" = None
    _db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, db_obj: "_pjt_housing.PJTHousing", editor3d: "_editor_3d.Editor3D", editor2d: "_editor_2d.Editor2D"):
        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)

        part = db_obj.part

        center = db_obj.point3d.point

        model3d = part.model3d
        if model3d is None:
            from ..editor_3d.shapes import box as _box
            model3d = _box.Box(center, part.length, part.width, part.height, part.color, part.color)
        else:
            from ..editor_3d.shapes import model3d as _model3d

            model3d = _model3d.Model3D(center, model3d, part.model3d_type, part.color)

        model3d.set_angles(db_obj.x_angle_3d, db_obj.y_angle_3d, db_obj.z_angle_3d, center)
        model3d.add_to_plot(editor3d.axes)
        self._objs.append(model3d)
        model3d.center.add_object(self)
        model3d.set_py_data(self)

        editor2d.add_connector(db_obj)
