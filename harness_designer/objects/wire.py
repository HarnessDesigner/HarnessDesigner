from typing import TYPE_CHECKING, Union

from . import base as _base
from ..editor_3d.shapes import cylinder as _cylinder


if TYPE_CHECKING:
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.global_db import wire as _wire
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d


class Wire(_base.ObjectBase):

    def __init__(self, db_obj: "_pjt_wire.PJTWire",
                 editor3d: Union["_editor_3d.Editor3D", None],
                 editor2d: Union["_editor_2d.Editor2D", None]):

        _base.ObjectBase.__init__(self, db_obj, editor3d, editor2d)
        p1_3d = db_obj.start_point3d.point
        p2_3d = db_obj.stop_point3d.point

        stripe_colors = self.part.addl_colors
        if stripe_colors:
            stripe_color = stripe_colors[0]
        else:
            stripe_color = None

        p1_2d = db_obj.start_point2d.point
        p2_2d = db_obj.stop_point2d.point
        cyl = _cylinder.CylinderWithStripe(p1_3d, None, self.part.od_mm, self.part.color, stripe_color, p2_3d)
        cyl.add_to_plot(editor3d.axes)

    @property
    def part(self) -> "_wire.Wire":
        return self._part

    def SetEditorPosition(self, pos):
        x1, y1, z1 = self._endpoint1.GetEditorPosition()
        x, y, z = pos

        xs, ys, zs = self._plot_obj.get_data_3d()

        if xs[0] == x1 and ys[0] == y1 and zs[0] == z1:
            xs[0] = x
            ys[0] = y
            zs[0] = z
        elif xs[1] == x1 and ys[1] == y1 and zs[1] == z1:
            xs[1] = x
            ys[1] = y
            zs[1] = z

        self._obj.set_data_3d(xs, ys, zs)

    def SetPlotObject(self, obj):
        self._plot_obj = obj

    def AddEndpoint(self, obj):
        if self._endpoint1 is None:
            self._endpoint1 = obj
        elif self._endpoint2 is None:
            self._endpoint2 = obj

    def RemoveEndpoint(self, obj):
        if self._endpoint1 == obj:
            self._endpoint1 = None
        elif self._endpoint2 == obj:
            self._endpoint2 = None

    def AddLayout(self, layout):
        wire = Wire(layout)
        wire.AddEndpoint(self._endpoint2)
        self._endpoint2 = layout
        return wire

    def AddSplice(self, splice):
        wire = Wire(splice)
        wire.AddEndpoint(self._endpoint2)
        self._endpoint2 = splice
        return wire

    def RemoveSplice(self, splice):
        if self._endpoint1 == splice:
            self._endpoint1 = None
        if self._endpoint2 == splice:
            self._endpoint2 = None

    def JoinWires(self, wire):
        endpoint1 = wire.GetEndpoint1()
        endpoint2 = wire.GetEndpoint2()

        if endpoint1 is not None:
            wire.RemoveEndpoint(endpoint1)
            self.AddEndpoint(endpoint1)

        elif endpoint2 is not None:
            wire.RemoveEndpoint(endpoint2)
            self.AddEndpoint(endpoint2)

    def GetEndpoint1(self):
        return self._endpoint1

    def GetEndpoint2(self):
        return self._endpoint2

