from typing import TYPE_CHECKING

from . import base as _base

if TYPE_CHECKING:
    from ..database.project_db import pjt_terminal as _pjt_terminal
    from ..database.global_db import terminal as _terminal
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


class Housing(_base.ObjectBase):
    _part: "_terminal.Terminal" = None
    _db_obj: "_pjt_terminal.PJTTerminal" = None

    def __init__(self, db_obj: "_pjt_terminal.PJTTerminal", editor3d: "_editor_3d.Editor3D", editor2d: "_editor_2d.Editor2D"):
        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)

        part = db_obj.part
        center = db_obj.point3d.point

        sphere = _sphere.Sphere(center, db_obj.diameter, part.color)

        sphere.add_to_plot(editor3d.axes)
        self._objs.append(sphere)
        sphere.center.add_object(self)
        sphere.set_py_data(self)

        editor2d.add_splice(db_obj)
