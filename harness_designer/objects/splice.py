from typing import TYPE_CHECKING

from . import base as _base

from .. editor_3d.shapes import sphere as _sphere

if TYPE_CHECKING:
    from ..database.project_db import pjt_splice as _pjt_splice
    from ..database.global_db import splice as _splice
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


class Housing(_base.ObjectBase):
    _part: "_splice.Splice" = None
    _db_obj: "_pjt_splice.PJTSplice" = None

    def __init__(self, db_obj: "_pjt_splice.PJTSplice", editor3d: "_editor_3d.Editor3D", editor2d: "_editor_2d.Editor2D"):
        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)

        part = db_obj.part
        center = db_obj.point3d.point

        sphere = _sphere.Sphere(center, db_obj.diameter, part.color)

        sphere.add_to_plot(editor3d.axes)
        self._objs.append(sphere)
        sphere.center.add_object(self)
        sphere.set_py_data(self)

        editor2d.add_splice(db_obj)
