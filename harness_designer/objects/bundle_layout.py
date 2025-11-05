from typing import TYPE_CHECKING

from . import base as _base
from ..editor_3d.shapes import sphere as _sphere
from ..wrappers import color as _color

if TYPE_CHECKING:
    from ..database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import editor_3d as _editor_3d


class BundleLayout(_base.ObjectBase):

    def __init__(self, db_obj: "_pjt_bundle_layout.PJTBundleLayout", editor3d: "_editor_3d.Editor3D", _):
        _base.ObjectBase.__init__(self, db_obj, editor3d, None)

        sphere = _sphere.Sphere(db_obj.point.point, db_obj.diameter, _color.Color(51, 51, 51, 255))

        sphere.add_to_plot(editor3d.axes)
        self._objs.append(sphere)
        sphere.center.add_object(self)
        sphere.set_py_data(self)

