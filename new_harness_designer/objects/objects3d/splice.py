
from typing import TYPE_CHECKING

import math
import wx
import build123d

# from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils

if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


Config = _config.Config.editor3d


def _build_model(p1: _point.Point, p2: _point.Point, diameter: float):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / 2.0 + 0.1

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    bb = model.bounding_box()

    corner1 = _point.Point(*[item for item in bb.min])
    corner2 = _point.Point(*[item for item in bb.max])

    return model, (corner1, corner2)


class Splice(_base3d.Base3D):
    _parent: "_splice.Splice"
    db_obj: "_pjt_splice.PJTSplice"

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):

        self._part = db_obj.part

        self._p1 = db_obj.start_position3d
        self._p2 = db_obj.stop_position3d
        self._p3 = db_obj.branch_position3d

        color = self._part.color.ui
        material = _materials.Rubber(color)
        angle = _angle.Angle.from_points(self._p1, self._p2)

        model = self._part.model3d
        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_covers:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            length = self._part.length

            wires = db_obj.wires

            area1 = [0.0]
            area2 = [0.0]

            for wire in wires[0]:
                dia = wire.od_mm
                area = math.pi * ((dia / 2.0) ** 2.0)
                area1.append(area)

            for wire in wires[-1]:
                dia = wire.od_mm
                area = math.pi * ((dia / 2.0) ** 2.0)
                area2.append(area)

            area1 = sum(area1)
            area2 = sum(area2)

            if area1:
                dia1 = 2.0 * math.sqrt(area1 / math.pi)
            else:
                dia1 = 0.0

            if area2:
                dia2 = 2.0 * math.sqrt(area2 / math.pi)
            else:
                dia2 = 0.0

            if dia2 > dia1:
                dia = dia2
            else:
                dia = dia1

            scale = _point.Point(dia, dia, length)
            vbo = _cylinder.create_vbo()

        position = self._p1

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)


class SpliceMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()