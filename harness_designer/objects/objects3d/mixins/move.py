from typing import TYPE_CHECKING

import build123d
import numpy as np

from ....geometry import point as _point
from ....geometry import angle as _angle
from .... import gl_materials as _gl_materials

from .. import base3d as _base3d
from .... import debug as _debug
from ....wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from ... import ObjectBase as _ObjectBase
    from .... import ui as _ui
    from ....editor_3d.canvas import canvas as _canvas


class StraightArrow:

    @_debug.timeit
    def __init__(self, parent: "ArrowMove", scale):

        self.parent = parent
        edge = build123d.Edge.extrude(
            build123d.Vertex(2.0, 0.0, 0.0), (6.0, 0.0, 0.0))

        wire = build123d.Wire(edge)

        wire_angle = wire.tangent_angle_at(0) - 20.0

        # Create the arrow head
        arrow_head = build123d.ArrowHead(size=2.0, rotation=wire_angle,
                                         head_type=build123d.HeadType.CURVED)

        # because of the curved arrow head there is a small space that would
        # appear in the arrowhead at the bottom. This polygon is used to fill
        # in that space so the bottom edge of the arrow shaft and arrow head
        # is a straight line.
        polygon = build123d.Polygon(
            (7.5, 0.20), (6.5, -0.125), (8.50, -0.125), align=None)

        arrow_head = arrow_head.move(build123d.Location((8.50, -0.125, 0.0)))

        # Trim the path so the tip of the arrow isn't lost
        trim_amount = 1.0 / wire.length
        shaft_path = wire.trim(trim_amount, 1.0)

        # Create a perpendicular line to sweep the tail path
        shaft_pen = shaft_path.perpendicular_line(0.25, 0)
        shaft = build123d.sweep(shaft_pen, shaft_path)

        # assembled the pieces that make up the complete arrow
        arrow = arrow_head + shaft
        arrow += polygon

        arrow = build123d.extrude(arrow, 0.25, (0, 0, 1))
        arrow = arrow.scale(float(scale))
        arrow = arrow.scale(1.20)

        # collect and copy the model, triangles and
        # normals from the class variables
        self.model = arrow


class ArrowMove(_base3d.Base3D):

    @_debug.timeit
    def __init__(self, parent: "MoveMixin", center: _point.Point,
                 angle: _angle.Angle, scale,
                 color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        super().__init__(parent.mainframe)
        self._real_parent = parent

        opposite_angle = angle.copy()

        if angle.y:
            opposite_angle.y += _decimal(180.0)
        elif angle.x and angle.z:
            opposite_angle.y += _decimal(180.0)
        else:
            opposite_angle.y = _decimal(180.0)

        self._arrow_1 = StraightArrow(self, scale)
        self._arrow_2 = StraightArrow(self, scale)

        a1 = self._arrow_1.model
        a2 = self._arrow_2.model

        a1_verts, a1_faces = self._convert_model_to_mesh(a1)
        a2_verts, a2_faces = self._convert_model_to_mesh(a2)

        a1_tris, a1_nrmls, a1_count = self._compute_vertex_normals(a1_verts, a1_faces)
        a2_tris, a2_nrmls, a2_count = self._compute_vertex_normals(a2_verts, a2_faces)
        a1_tris @= angle
        a1_nrmls @= angle

        a2_tris @= opposite_angle
        a2_nrmls @= opposite_angle

        tris = np.array([a1_tris, a2_tris], dtype=np.float64).reshape(-1, 3, 3)
        nrmls = np.array([a1_nrmls, a2_nrmls], dtype=np.float64).reshape(-1, 3)
        count = a1_count + a2_count

        tris += center

        p1, p2 = self._compute_rect(tris)
        bb = self._compute_bb(p1, p2)

        self._rect.append([p1, p2])
        self._bb.append(bb)

        self._position = center
        self._parent_pos = parent.position
        self._o_parent_pos = self._parent_pos.copy()

        self._parent_pos.bind(self._update_position)

        self._material = _gl_materials.Metallic(color)
        self._press_material = _gl_materials.Metallic(press_color)

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

        self._color = color
        self._press_color = press_color

        self.canvas.add_object(self)

    def set_selected(self, flag: bool):
        self._is_selected = flag
        if flag:
            self._triangles[0].material = self._press_material
        else:
            self._triangles[0].material = self._material

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def _update_position(self, point: _point.Point):
        delta = point - self._o_parent_pos
        self._o_parent_pos = point.copy()

        data = self._triangles[0].data

        tris = data[0][0]
        tris += delta
        data[0][0] = tris
        self._triangles[0].data = data

        p1, p2 = self._compute_rect(tris)
        self._rect = [[p1, p2]]
        self._bb = [self._compute_bb(p1, p2)]

    @property
    def position(self) -> _point.Point:
        return self._position

    def delete(self):
        self.canvas.remove_object(self)

    @property
    def triangles(self):
        return self._triangles

    def start_angle(self, flag=True):
        if flag:
            self.canvas.add_object(self)
        else:
            try:
                self.canvas.remove_object(self)
            except:  # NOQA
                pass

    def move(self, candidate, start_obj_pos, last_pos):
        return self._real_parent.move(candidate, start_obj_pos, last_pos)


class MoveMixin:
    mainframe: "_ui.MainFrame" = None
    parent: "_ObjectBase" = None
    canvas: "_canvas.Canvas" = None

    _rect: list[list[_point.Point, _point.Point]] = []

    _x_arrow: "ArrowMove" = None
    _y_arrow: "ArrowMove" = None
    _z_arrow: "ArrowMove" = None

    _o_position: _point.Point = None
    _position: _point.Point = None
    _triangles: list[_base3d.TriangleRenderer | _base3d.LineRenderer] = []
    _bb: list = []

    @staticmethod
    def _compute_bb(p1, p2):
        raise RuntimeError

    @staticmethod
    def _compute_rect(tris):
        raise RuntimeError

    def _update_position(self, point: _point.Point):
        delta = point - self._o_position
        self._o_position = point.copy()

        for i, renderer in enumerate(self._triangles):
            data = renderer.data

            for j, (tris, _, __) in enumerate(data):
                tris += delta
                data[i][0] = tris

                p1, p2 = self._compute_rect(tris)

                try:
                    self._rect[i] = [p1, p2]
                except IndexError:
                    pass

                try:
                    self._bb[i] = self._compute_bb(p1, p2)
                except IndexError:
                    pass

            renderer.data = data

    def move(self, candidate, start_obj_pos, last_pos):
        raise NotImplementedError

    @_debug.timeit
    def start_move(self):
        p1, p2 = self._rect[0]
        offset = p2 - p1

        scale = max(offset.x, offset.y, offset.z) / _decimal(20.0)
        center = self.position

        x_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        x_center = center.copy()
        x_center.y = p2.y + offset.y / _decimal(4.0)

        y_angle = _angle.Angle.from_euler(90.0, 0.0, 90.0)
        y_center = center.copy()
        y_center.x = p2.x + offset.x / _decimal(4.0)

        z_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)
        z_center = center.copy()
        z_center.x = p1.x - offset.x / _decimal(4.0)

        with self.canvas:

            self._x_arrow = ArrowMove(self, x_center, x_angle, scale,
                                      [0.8, 0.2, 0.2, 0.45],
                                      [1.0, 0.3, 0.3, 1.0])

            self._y_arrow = ArrowMove(self, y_center, y_angle, scale,
                                      [0.2, 0.8, 0.2, 0.45],
                                      [0.3, 1.0, 0.3, 1.0])

            self._z_arrow = ArrowMove(self, z_center, z_angle, scale,
                                      [0.2, 0.2, 0.8, 0.45],
                                      [0.3, 0.3, 1.0, 1.0])

        self.canvas.Refresh(False)

    def stop_move(self):
        self._x_arrow.delete()
        self._y_arrow.delete()
        self._z_arrow.delete()

        self._x_arrow = None
        self._y_arrow = None
        self._z_arrow = None

    @property
    def is_move_shown(self) -> bool:
        return self._x_arrow is not None

    @_debug.timeit
    def move(self, candidate: _point.Point,
             start_pos: _point.Point, last_pos: _point.Point):

        if self._x_arrow.is_selected:
            new_pos = _point.Point(candidate.x, start_pos.y, start_pos.z)
        elif self._y_arrow.is_selected:
            new_pos = _point.Point(start_pos.x, candidate.y, start_pos.z)
        elif self._z_arrow.is_selected:
            new_pos = _point.Point(start_pos.x, start_pos.y, candidate.z)
        else:
            return

            # compute incremental delta to move things (arrows and object)
        delta = new_pos - last_pos

        position = self._position
        position += delta

        return new_pos

    @property
    def bb(self):
        return self._bb

    @property
    def position(self) -> _point.Point:
        return self._position
