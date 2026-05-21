# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
from PySide6.QtWidgets import QMenu
import build123d

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
    parent: "_splice.Splice" = None
    db_obj: "_pjt_splice.PJTSplice" = None

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):

        parent.mainframe.editor3d.context.acquire()

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
        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        parent.mainframe.editor3d.context.release()


    def get_context_menu(self):
        return SpliceMenu(self.mainframe.editor3d.editor, self)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def wire_position(self) -> _point.Point:
        return self.branch_position

    @property
    def branch_position(self):
        """Wire branch position (Point instance)"""
        return self._p3

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class SpliceMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_add_wire(self):
        pass

    def on_trace_circuit(self):
        pass

    def on_select(self):
        pass

    def on_clone(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
