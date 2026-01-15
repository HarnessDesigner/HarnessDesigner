from typing import TYPE_CHECKING

import build123d
import numpy as np

try:
    from ...geometry import point as _point
    from ...geometry import angle as _angle

    from ... import gl_object as _gl_object
    from ... import debug as _debug
    from ... import helpers
    from ...wrappers.wrap_decimal import Decimal as _decimal
except ImportError:
    from geometry import point as _point  # NOQA
    from geometry import angle as _angle  # NOQA

    import gl_object as _gl_object  # NOQA
    import debug as _debug  # NOQA
    import helpers  # NOQA
    from wrappers.wrap_decimal import Decimal as _decimal  # NOQA

if TYPE_CHECKING:
    from ... import mainframe as _mainframe


class StraightArrow:
    _arrow: tuple[np.ndarray, np.ndarray, int] = None
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    @_debug.timeit
    def __init__(self, parent: "ArrowMove",
                 center: _point.Point, angle: _angle.Angle, scale):

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

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), float(angle.x))

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), float(angle.y))

        arrow = arrow.rotate(
            build123d.Axis((0.0, 0.0, 0.0), (0, 0, 1)), float(angle.z))

        arrow = arrow.scale(float(scale))
        arrow = arrow.scale(1.20)

        arrow = arrow.move(build123d.Location(
            (float(center.x), float(center.y), float(center.z))))

        # calculate the bounding box for the arrow
        bb = arrow.bounding_box()
        # build the triangles for the arrow
        # we set the built arrow into a class variable so it only needs to
        # get built a single time. The same calculated trinagles gets used
        # for each instance of this class that gets made. The normals and
        # triangles get copied with each nw instance of this class. the normals
        # and triangles are then scaled to size for use with whatever the
        # object is.
        normals, triangles, count = parent.get_housing_triangles(arrow)

        # collect and copy the model, triangles and
        # normals from the class variables
        self.models = [arrow]

        self.triangles = [[triangles, normals, count]]

        # copy the bounding box for the arrow

        p1 = _point.Point(_decimal(bb.min.X),
                          _decimal(bb.min.Y), _decimal(bb.min.Z))

        p2 = _point.Point(_decimal(bb.max.X),
                          _decimal(bb.max.Y), _decimal(bb.max.Z))

        # set the bounding box as the clickable rectangle
        self.hit_test_rect = [[p1, p2]]
        self.adjust_hit_points()

        obj_center = self.parent.get_parent_object().position
        obj_center.bind(self.on_obj_move)
        self._obj_center = obj_center.copy()

    @_debug.timeit
    def on_obj_move(self, center):
        delta = center - self._obj_center
        # self.triangles[0][0] += delta
        self.triangles[0][0] += delta
        self._obj_center = center.copy()

    @_debug.timeit
    def adjust_angle(self, delta: _angle.Angle):
        triangles, normals = self.triangles[0][:-1]

        # normals -= self._obj_center
        triangles -= self._obj_center

        normals @= delta
        triangles @= delta

        # normals += self._obj_center
        triangles += self._obj_center

        self.triangles[0][0] = triangles
        self.triangles[0][1] = normals

        for p in self.hit_test_rect[0]:
            p -= self._obj_center
            p @= delta
            p += self._obj_center

        self.adjust_hit_points()

    def adjust_hit_points(self):
        for i, (p1, p2) in enumerate(self.hit_test_rect):

            xmin = min(p1.x, p2.x)
            ymin = min(p1.y, p2.y)
            zmin = min(p1.z, p2.z)
            xmax = max(p1.x, p2.x)
            ymax = max(p1.y, p2.y)
            zmax = max(p1.z, p2.z)

            p1 = _point.Point(xmin, ymin, zmin)
            p2 = _point.Point(xmax, ymax, zmax)

            self.hit_test_rect[i] = [p1, p2]


class ArrowMove(_gl_object.GLObject):

    @_debug.timeit
    def __init__(self, parent: "MoveMixin", center: _point.Point,
                 angle: _angle.Angle, scale,
                 color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        self.parent = parent
        self._color = color
        self._press_color = press_color

        super().__init__()

        opposite_angle = angle.copy()

        if angle.y:
            opposite_angle.y += _decimal(180.0)
        elif angle.x and angle.z:
            opposite_angle.y += _decimal(180.0)
        else:
            opposite_angle.y = _decimal(180.0)

        self._arrow_1 = StraightArrow(self, center, angle, scale)
        self._arrow_2 = StraightArrow(self, center, opposite_angle, scale)

        self.__angle = angle
        self._center = center
        self._build_globject()
        self.parent.get_canvas().add_object(self)

    @property
    def position(self) -> _point.Point:
        return self._center

    def delete(self):
        self.parent.get_canvas().remove_object(self)

    @_debug.timeit
    def _build_globject(self):

        if self.__angle.y:
            self.hit_test_rect = [
                [self._arrow_1.hit_test_rect[0][0],
                 self._arrow_2.hit_test_rect[0][1]]
            ]
        else:
            self.hit_test_rect = [
                [self._arrow_1.hit_test_rect[0][1],
                 self._arrow_2.hit_test_rect[0][0]]
            ]

        self.adjust_hit_points()

        self._color_arr = [
            np.full((self._arrow_1.triangles[0][-1], 4),
                    self._color, dtype=np.float32),

            np.full((self._arrow_1.triangles[0][-1], 4),
                    self._press_color, dtype=np.float32)
        ]

        self._triangles = [self._arrow_1.triangles[0],
                           self._arrow_2.triangles[0]]

    def get_first_points(self):
        points = []
        for i in range(2):
            tris = self._triangles[i][0]
            p = _point.Point(_decimal(tris[0][0]), _decimal(tris[0][1]),
                             _decimal(tris[0][2]))
            points.append(p)

        return points

    @property
    def triangles(self):
        triangles = []
        for tris, norms, count in self._triangles:
            color = self._color_arr[int(self._is_selected)]
            triangles.append([tris, norms, color, count, color[0][-1] >= 1.0])

        return triangles

    def start_angle(self, flag=True):
        if flag:
            self.get_parent_object().parent.canvas.add_object(self)
        else:
            try:
                self.get_parent_object().parent.canvas.objects.remove(self)
            except:  # NOQA
                pass

    def get_parent_object(self) -> "MoveMixin":
        return self.parent

    def move(self, candidate, start_obj_pos, last_pos):
        return self.parent.move(candidate, start_obj_pos, last_pos)


class MoveMixin:
    parent: "_mainframe.MainFrame" = None
    hit_test_rect: list[list[_point.Point, _point.Point]] = []

    _x_arrow: "ArrowMove" = None
    _y_arrow: "ArrowMove" = None
    _z_arrow: "ArrowMove" = None

    def get_parent_object(self) -> _gl_object.GLObject:
        return self

    def get_canvas(self):
        raise NotImplementedError

    @_debug.timeit
    def start_move(self):
        p1, p2 = self.hit_test_rect[0]
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

        with self.get_canvas():

            self._x_arrow = ArrowMove(self, x_center, x_angle, scale,
                                      [0.8, 0.2, 0.2, 0.45],
                                      [1.0, 0.3, 0.3, 1.0])

            self._y_arrow = ArrowMove(self, y_center, y_angle, scale,
                                      [0.2, 0.8, 0.2, 0.45],
                                      [0.3, 1.0, 0.3, 1.0])

            self._z_arrow = ArrowMove(self, z_center, z_angle, scale,
                                      [0.2, 0.2, 0.8, 0.45],
                                      [0.3, 0.3, 1.0, 1.0])

        self.get_canvas().Refresh(False)

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

        position = self.position
        position += delta

        return new_pos

    @property
    def position(self) -> _point.Point:
        raise NotImplementedError
