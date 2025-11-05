from typing import TYPE_CHECKING, Union

from . import base as _base
from ..editor_3d.shapes import cylinder as _cylinder


if TYPE_CHECKING:
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.global_db import wire as _wire
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


class Wire(_base.ObjectBase):
    _part: "_wire.Wire" = None
    _db_obj: "_pjt_wire.PJTWire" = None

    def __init__(self, db_obj: "_pjt_wire.PJTWire", editor3d: "_editor_3d.Editor3D", editor2d: "_editor_2d.Editor2D"):

        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)
        p1_3d = db_obj.start_point3d.point
        p2_3d = db_obj.stop_point3d.point

        stripe_colors = self.part.addl_colors
        if stripe_colors:
            stripe_color = stripe_colors[0]
        else:
            stripe_color = None

        cyl = _cylinder.CylinderWithStripe(p1_3d, None, self.part.od_mm, self.part.color, stripe_color, p2_3d)
        cyl.add_to_plot(editor3d.axes)
        self._objs.append(cyl)
        cyl.p1.add_object(self)
        cyl.p2.add_object(self)
        cyl.set_py_data(self)
        editor2d.add_wire(db_obj)
