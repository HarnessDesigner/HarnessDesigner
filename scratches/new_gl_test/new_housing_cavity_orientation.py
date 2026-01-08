from typing import Self

import new_opengl_framework
import wx
import math

import build123d
import numpy as np


# wrapper classes to make moving code from this scratch into the production code
# easier to do

class _point:

    class Point(new_opengl_framework.Point):
        pass


class _line:

    class Line(new_opengl_framework.Line):
        pass


class _angle:

    class Angle(new_opengl_framework.Angle):
        pass


class _decimal(new_opengl_framework.Decimal):
    pass


class GLObject(new_opengl_framework.GLObject):
    pass


class Canvas(new_opengl_framework.Canvas):

    def __init__(self, parent, size):
        self.parent = parent

        new_opengl_framework.Canvas.__init__(self, parent, size)


class ControlPanel(wx.Panel):

    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, wx.ID_ANY, size=size)
        self.parent = parent

        sizer = wx.BoxSizer(wx.VERTICAL)

        def _add(label, ctrl):
            h_sizer = wx.BoxSizer(wx.HORIZONTAL)
            st = wx.StaticText(self, wx.ID_ANY, label=label)
            h_sizer.Add(st, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            h_sizer.Add(ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            sizer.Add(h_sizer, 0)

        self.angle_x = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)
        self.angle_y = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)
        self.angle_z = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.rel_angle_x = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)
        self.rel_angle_y = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)
        self.rel_angle_z = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=0.0, max=359.9, inc=0.1)

        self.pos_x = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.pos_y = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.pos_z = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        
        self.rel_pos_x = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.rel_pos_y = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.rel_pos_z = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.length = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="1.0", initial=1.0, min=1.0, max=99.0, inc=0.1)
        self.terminal_size = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="1.5", initial=1.5, min=0.1, max=99.0, inc=0.1)
        self.use_cylinder = wx.CheckBox(self, wx.ID_ANY, label='')

        _add('X Angle (abs):', self.angle_x)
        _add('Y Angle (abs):', self.angle_y)
        _add('Z Angle (abs):', self.angle_z)
        _add('X Position (abs):', self.pos_x)
        _add('Y Position (abs):', self.pos_y)
        _add('Z Position (abs):', self.pos_z)
        
        _add('X Angle (rel):', self.rel_angle_x)
        _add('Y Angle (rel):', self.rel_angle_y)
        _add('Z Angle (rel):', self.rel_angle_z)
        _add('X Position (rel):', self.rel_pos_x)
        _add('Y Position (rel):', self.rel_pos_y)
        _add('Z Position (rel):', self.rel_pos_z)
        
        _add('Cavity Length:', self.length)
        _add('Terminal (blade) Size:', self.terminal_size)
        _add('Cylinder Cavity:', self.use_cylinder)

        self.button = wx.Button(self, wx.ID_ANY, label='Add Cavity', size=(125, -1))

        self.button.Bind(wx.EVT_BUTTON, self.on_button)
        sizer.AddSpacer(1)
        sizer.Add(self.button, 0, wx.ALL, 5)

        self.SetSizer(sizer)

        self.angle_x.Enable(False)
        self.angle_y.Enable(False)
        self.angle_z.Enable(False)

        self.rel_angle_x.Enable(False)
        self.rel_angle_y.Enable(False)
        self.rel_angle_z.Enable(False)

        self.pos_x.Enable(False)
        self.pos_y.Enable(False)
        self.pos_z.Enable(False)
        
        self.rel_pos_x.Enable(False)
        self.rel_pos_y.Enable(False)
        self.rel_pos_z.Enable(False)
        
        self.length.Enable(False)
        self.terminal_size.Enable(False)
        self.use_cylinder.Enable(False)

        self.angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_x)
        self.angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_y)
        self.angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_z)
        
        self.rel_angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_x)
        self.rel_angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_y)
        self.rel_angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_angle_z)
        
        self.pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_x)
        self.pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_y)
        self.pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_z)

        self.rel_pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_x)
        self.rel_pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_y)
        self.rel_pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_rel_pos_z)

        self.length.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_length)
        self.terminal_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_terminal_size)
        self.use_cylinder.Bind(wx.EVT_CHECKBOX, self.on_use_cylinder)

        self.selected = None

    def on_button(self, evt):
        self.parent.housing.add_cavity()
        evt.Skip()

    def on_angle_x(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_x.GetValue()) - angle.x

        angle.unbind(self.on_obj_angle)
        angle.x += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()

        self.GetParent().Refresh(False)

    def on_angle_y(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_y.GetValue()) - angle.y

        angle.unbind(self.on_obj_angle)
        angle.y += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_angle_z(self, evt):
        angle = self.selected.angle
        delta = _decimal(self.angle_z.GetValue()) - angle.z

        angle.unbind(self.on_obj_angle)
        angle.z += delta
        angle.bind(self.on_obj_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_x(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_x.GetValue()) - angle.x

        angle.unbind(self.on_obj_rel_angle)
        angle.x += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_y(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_y.GetValue()) - angle.y

        angle.unbind(self.on_obj_rel_angle)
        angle.y += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_angle_z(self, evt):
        angle = self.selected.rel_angle
        delta = _decimal(self.rel_angle_z.GetValue()) - angle.z

        angle.unbind(self.on_obj_rel_angle)
        angle.z += delta
        angle.bind(self.on_obj_rel_angle)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_x(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_x.GetValue()) - position.x
        
        position.unbind(self.on_obj_position)
        position.x += delta
        position.bind(self.on_obj_position)
        
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_y(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_y.GetValue()) - position.y

        position.unbind(self.on_obj_position)
        position.y += delta
        position.bind(self.on_obj_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_pos_z(self, evt):
        position = self.selected.position
        delta = _decimal(self.pos_z.GetValue()) - position.z

        position.unbind(self.on_obj_position)
        position.z += delta
        position.bind(self.on_obj_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_x(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_x.GetValue()) - position.x

        position.unbind(self.on_obj_rel_position)
        position.x += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_y(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_y.GetValue()) - position.y

        position.unbind(self.on_obj_rel_position)
        position.y += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_rel_pos_z(self, evt):
        position = self.selected.rel_position
        delta = _decimal(self.rel_pos_z.GetValue()) - position.z

        position.unbind(self.on_obj_rel_position)
        position.z += delta
        position.bind(self.on_obj_rel_position)

        evt.Skip()
        self.GetParent().Refresh(False)

    def on_length(self, evt):
        length = self.length.GetValue()
        self.selected.set_length(length)
        evt.Skip()

    def on_terminal_size(self, evt):
        terminal_size = self.terminal_size.GetValue()
        self.selected.set_terminal_size(terminal_size)
        evt.Skip()
        self.GetParent().Refresh(False)

    def on_use_cylinder(self, evt):
        evt.Skip()
        value = self.use_cylinder.GetValue()
        self.selected.use_cylinder(value)

    def on_obj_angle(self, angle: _angle.Angle):
        x, y, z = angle.as_float
        self.angle_x.SetValue(x)
        self.angle_y.SetValue(y)
        self.angle_z.SetValue(z)

    def on_obj_position(self, point: _point.Point):
        x, y, z = point.as_float
        self.pos_x.SetValue(x)
        self.pos_y.SetValue(y)
        self.pos_z.SetValue(z)

    def on_obj_rel_angle(self, angle: _angle.Angle):
        x, y, z = angle.as_float
        self.rel_angle_x.SetValue(x)
        self.rel_angle_y.SetValue(y)
        self.rel_angle_z.SetValue(z)

    def on_obj_rel_position(self, point: _point.Point):
        x, y, z = point.as_float
        self.rel_pos_x.SetValue(x)
        self.rel_pos_y.SetValue(y)
        self.rel_pos_z.SetValue(z)

    def set_selected(self, obj):
        if obj is None:
            if self.selected is not None:
                self.selected.angle.unbind(self.on_obj_angle)
                self.selected.position.unbind(self.on_obj_position)

                if isinstance(self.selected, Cavity):
                    self.selected.rel_angle.unbind(self.on_obj_rel_angle)
                    self.selected.rel_position.unbind(self.on_obj_rel_position)

            self.angle_x.Enable(False)
            self.angle_y.Enable(False)
            self.angle_z.Enable(False)

            self.rel_angle_x.Enable(False)
            self.rel_angle_y.Enable(False)
            self.rel_angle_z.Enable(False)

            self.pos_x.Enable(False)
            self.pos_y.Enable(False)
            self.pos_z.Enable(False)

            self.rel_pos_x.Enable(False)
            self.rel_pos_y.Enable(False)
            self.rel_pos_z.Enable(False)

            self.length.Enable(False)
            self.terminal_size.Enable(False)
            self.use_cylinder.Enable(False)
        else:
            obj.angle.bind(self.on_obj_angle)
            obj.position.bind(self.on_obj_position)

            if isinstance(obj, Cavity):
                obj.rel_angle.bind(self.on_obj_rel_angle)
                obj.rel_position.bind(self.on_obj_rel_position)

                self.rel_angle_x.Enable(True)
                self.rel_angle_y.Enable(True)
                self.rel_angle_z.Enable(True)

                self.rel_pos_x.Enable(True)
                self.rel_pos_y.Enable(True)
                self.rel_pos_z.Enable(True)

                x, y, z = obj.rel_angle.as_float

                self.rel_angle_x.SetValue(x)
                self.rel_angle_y.SetValue(y)
                self.rel_angle_z.SetValue(z)

                x, y, z = obj.rel_position.as_float

                self.rel_pos_x.SetValue(x)
                self.rel_pos_y.SetValue(y)
                self.rel_pos_z.SetValue(z)

            self.angle_x.Enable(True)
            self.angle_y.Enable(True)
            self.angle_z.Enable(True)

            self.pos_x.Enable(True)
            self.pos_y.Enable(True)
            self.pos_z.Enable(True)

            x, y, z = obj.angle.as_float

            self.angle_x.SetValue(x)
            self.angle_y.SetValue(y)
            self.angle_z.SetValue(z)

            x, y, z = obj.position.as_float

            self.pos_x.SetValue(x)
            self.pos_y.SetValue(y)
            self.pos_z.SetValue(z)

            if isinstance(obj, Housing):
                self.length.Enable(False)
                self.terminal_size.Enable(False)
                self.use_cylinder.Enable(False)
            else:
                self.length.Enable(True)
                self.terminal_size.Enable(True)
                self.use_cylinder.Enable(True)
                self.length.SetValue(obj.get_length())
                self.terminal_size.SetValue(obj.get_terminal_size())

        self.selected = obj


stl_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15397578.stl'


# TODO: figure out the clickable region for the move arrows not being correct.
#       the region is centered like it should be but it is not wide enough to
#       cover the directional arrows.


class StraightArrow:
    _arrow: tuple[np.ndarray, np.ndarray, int] = None
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    def __init__(self, parent: "ArrowMove", center: _point.Point, angle: _angle.Angle, scale):
        self.parent = parent

        GLObject.__init__(self)

        if StraightArrow._arrow is None:
            edge = build123d.Edge.extrude(build123d.Vertex(2.0, 0.0, 0.0), (6.0, 0.0, 0.0))
            wire = build123d.Wire(edge)

            wire_angle = wire.tangent_angle_at(0) - 20.0

            # Create the arrow head
            arrow_head = build123d.ArrowHead(size=2.0, rotation=wire_angle,
                                             head_type=build123d.HeadType.CURVED)

            # because of the curved arrow head there is a small space that would
            # appear in the arrowhead at the bottom. This polygon is used to fill
            # in that space so the bottom edge of the arrow shaft and arrow head
            # is a straight line.
            polygon = build123d.Polygon((7.5, 0.20), (6.5, -0.125), (8.50, -0.125), align=None)

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

            # calculate the bounding box for the arrow
            bb = arrow.bounding_box()
            StraightArrow._boundingbox = [
                _point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z)),
                _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))
            ]
            # build the triangles for the arrow
            # we set the built arrow into a class variable so it only needs to
            # get built a single time. The same calculated trinagles gets used
            # for each instance of this class that gets made. The normals and triangles
            # get copied with each nw instance of this class. the normals and triangles
            # are then scaled to size for use with whatever the object is.
            StraightArrow._arrow = parent.get_wire_triangles(arrow)
            StraightArrow._model = arrow

        # collect and copy the model, triangles and normals from the class variables
        self.models = [StraightArrow._model]
        normals, triangles, count = StraightArrow._arrow

        normals = normals.copy()
        triangles = triangles.copy()

        # scale the triangles
        triangles *= float(scale)

        # because a single arrow gets used for all arrow locations it's orientation
        # to the object is going to differ based on the axis the arrow is being used on.
        # that orientation gets passed in when the instance of the arrow is being created
        # and we apply that orientation here.
        triangles @= angle
        normals @= angle

        # move the arrow into position
        triangles += center

        self.triangles = [[triangles, normals, count]]

        # copy the bounding box for the arrow
        p1 = StraightArrow._boundingbox[0].copy()
        p2 = StraightArrow._boundingbox[1].copy()

        # apply the scale to the bounding box
        p1 *= scale
        p2 *= scale

        # increase the area of the bounding box. this increases the size of
        # the clickable area
        p1 *= _decimal(1.20)
        p2 *= _decimal(1.20)

        # apply the orientation to the bounding box
        p1 @= angle
        p2 @= angle

        # move the bounding box
        p1 += center
        p2 += center

        # set the bounding box as the clickable rectangle
        self.hit_test_rect = [[p1, p2]]
        self.adjust_hit_points()

        obj_center = self.parent.get_parent_object().position
        obj_center.bind(self.on_obj_move)
        self._obj_center = obj_center.copy()

    def on_obj_move(self, center):
        delta = center - self._obj_center
        # self.triangles[0][0] += delta
        self.triangles[0][0] += delta
        self._obj_center = center.copy()

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


class ArrowMove(GLObject):

    def __init__(self, parent: "MoveMixin", center: _point.Point, angle: _angle.Angle, scale,
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
            opposite_angle.y += _decimal(180)
        else:
            opposite_angle.y = _decimal(180.0)

        self._arrow_1 = StraightArrow(self, center, angle, scale)
        self._arrow_2 = StraightArrow(self, center, opposite_angle, scale)

        self._center = center
        self._build_globject()
        self.parent.get_canvas().add_object(self)

    @property
    def position(self) -> _point.Point:
        return self._center

    def delete(self):
        self.parent.get_canvas().remove_object(self)

    def _build_globject(self):
        self.hit_test_rect = [
            self._arrow_1.hit_test_rect[0],
            self._arrow_2.hit_test_rect[0]
        ]

        self.adjust_hit_points()

        self._color_arr = [
            np.full((self._arrow_1.triangles[0][-1], 4), self._color, dtype=np.float32),
            np.full((self._arrow_1.triangles[0][-1], 4), self._press_color, dtype=np.float32)
        ]

        self._triangles = [self._arrow_1.triangles[0], self._arrow_2.triangles[0]]

    @property
    def triangles(self):
        triangles = []
        for tris, norms, count in self._triangles:
            color = self._color_arr[int(self._is_selected)]
            triangles.append([tris, norms, color, count, color[0][-1] < 1.0])

        return triangles

    def start_angle(self, flag=True):
        if flag:
            self.get_parent_object().parent.canvas.add_object(self)
        else:
            try:
                self.get_parent_object().parent.canvas.objects.remove(self)
            except:  # NOQA
                pass

    def angle(self, delta: _angle.Angle):
        self.get_parent_object().angle(delta)

    def get_parent_object(self) -> "MoveMixin":
        return self.parent

    def move(self, candidate, start_obj_pos, last_pos):
        return self.parent.move(candidate, start_obj_pos, last_pos)


class MoveMixin:
    parent: "Frame" = None
    hit_test_rect: list[list[_point.Point, _point.Point]] = []

    _x_arrow: "ArrowMove" = None
    _y_arrow: "ArrowMove" = None
    _z_arrow: "ArrowMove" = None

    def get_parent_object(self) -> GLObject:
        return self

    def get_canvas(self):
        raise NotImplementedError

    def start_move(self):
        p1, p2 = self.hit_test_rect[0]
        offset = p2 - p1

        scale = max(offset.x, offset.y, offset.z) / _decimal(20.0)
        center = self.position

        x_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        x_center = center.copy()
        x_center.y = p2.y + (offset.y / _decimal(2.0))

        y_angle = _angle.Angle.from_euler(90.0, 0.0, 90.0)
        y_center = center.copy()
        y_center.x = p2.x + (offset.x / _decimal(2.0))

        z_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)
        z_center = center.copy()
        z_center.x = p1.x - (offset.x / _decimal(2.0))

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

    def move(self, candidate: _point.Point, start_pos: _point.Point, last_pos: _point.Point):
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

        print('MoveMixin.move:', candidate, start_pos, last_pos, new_pos, delta)
        position = self.position
        position += delta

        return new_pos

    @property
    def position(self) -> _point.Point:
        raise NotImplementedError


class CurvedArrow:
    _arrow: tuple[np.ndarray, np.ndarray, int]
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    def __init__(self, parent: "ArrowRing", center: _point.Point, radius: float,
                 start_angle: float, angle: _angle.Angle):

        self.parent = parent

        if CurvedArrow._arrow is None:
            x = 10.0625 * math.cos(math.radians(58.333333))
            y = (10.0 + 0.25 / 4.0) * math.sin(math.radians(58.333333))

            arc = build123d.CenterArc((0.0, 0.0, 0.0),
                                      10.0, 85.0, -20.0)

            arc = build123d.Wire(arc.edges())

            arc_angle = arc.tangent_angle_at(0) - 20.0

            # build123d.HeadType.FILLETED

            # Create the arrow head
            arrow_head = build123d.ArrowHead(size=2.0, rotation=arc_angle,
                                             head_type=build123d.HeadType.CURVED)

            arrow_head = arrow_head.move(build123d.Location((x, y, 0.0)))

            # Trim the path so the tip of the arrow isn't lost
            trim_amount = 1.0 / arc.length
            shaft_path = arc.trim(trim_amount, 1.0)

            # Create a perpendicular line to sweep the tail path
            shaft_pen = shaft_path.perpendicular_line(0.25, 0)
            shaft = build123d.sweep(shaft_pen, shaft_path)
            arrow = arrow_head + shaft

            arrow = build123d.extrude(arrow, 0.25, (0, 0, 1))

            x = 10.0 * math.cos(math.radians(80))
            y = 10.0 * math.sin(math.radians(85.0 - ((85.0 - 65.0) / 4.0)))

            arrow = arrow.move(build123d.Location((-x, -y, 0.0)))

            bb = arrow.bounding_box()
            CurvedArrow._boundingbox = [
                _point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z)),
                _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))
            ]
            CurvedArrow._arrow = parent.get_wire_triangles(arrow)
            CurvedArrow._model = arrow

        self.models = [CurvedArrow._model]
        normals, triangles, count = CurvedArrow._arrow

        normals = normals.copy()
        triangles = triangles.copy()

        x = _decimal(radius * math.cos(math.radians(start_angle)))
        y = _decimal(radius * math.sin(math.radians(start_angle)))

        p = _point.Point(x, y, _decimal(0.0))

        triangles @= angle
        triangles += p

        normals @= angle
        # normals += p

        triangles += center
        # normals += center

        self.triangles = [[triangles, normals, count]]

        p1 = CurvedArrow._boundingbox[0].copy()
        p2 = CurvedArrow._boundingbox[1].copy()

        p1 += p
        p2 += p

        p1 @= angle
        p2 @= angle

        p1 += center
        p2 += center

        self.hit_test_rect = [[p1, p2]]


class ArrowRing(GLObject):

    def __init__(self, parent, center: _point.Point, radius: _decimal,
                 angle: _angle.Angle, color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        super().__init__()
        self.parent = parent

        opposite_angle = angle.copy()

        if angle.y:
            opposite_angle.y += _decimal(180.0)
        elif angle.x and angle.z:
            opposite_angle.y += _decimal(180)
        else:
            opposite_angle.y = _decimal(180.0)

        mirrored_angle = angle.copy()
        mirrored_opposite_angle = opposite_angle.copy()

        if angle.x:
            mirrored_angle.x += _decimal(180.0)
            mirrored_opposite_angle.x += _decimal(180.0)

        elif angle.y:
            mirrored_angle.z += _decimal(180.0)
            mirrored_opposite_angle.z += _decimal(180.0)
        else:
            mirrored_angle.z += _decimal(180.0)
            mirrored_opposite_angle.y += _decimal(180.0)

        top_arrow_1 = CurvedArrow(parent, center, radius, 270 + radius, angle)
        top_arrow_2 = CurvedArrow(parent, center, radius, 270 + radius, opposite_angle)
        bot_arrow_1 = CurvedArrow(parent, center, radius, 90 + radius, mirrored_angle)
        bot_arrow_2 = CurvedArrow(parent, center, radius, 90 + radius, mirrored_opposite_angle)

        self.dir_1_arrows = [top_arrow_1, bot_arrow_2]
        self.dir_2_arrows = [top_arrow_2, bot_arrow_1]

        arc = build123d.CenterArc((0.0, 0.0, 0.0),
                                  10.0, 0.0, 360.0)

        arc = build123d.Wire(arc.edges())
        pen = arc.perpendicular_line(0.10, 0)
        ring = build123d.sweep(pen, arc)

        self.hit_test_rect = [
            top_arrow_1.hit_test_rect[0],
            bot_arrow_1.hit_test_rect[0]
        ]

        self.adjust_hit_points()

        normals, triangles, count = self.get_wire_triangles(ring)

        triangles @= angle
        normals @= angle
        triangles += center

        self._triangles = [top_arrow_1.triangles[0], top_arrow_2.triangles[0],
                           bot_arrow_1.triangles[0], bot_arrow_2.triangles[0],
                           [triangles, normals, count]]

        self.models = [ring]
        self._color = color
        self._press_color = press_color

        self.parent.get_canvas().add_object(self)

        self._color_arr = [
            [
                np.full((top_arrow_1.triangles[0][-1], 4), color, dtype=np.float32),
                np.full((top_arrow_1.triangles[0][-1], 4), press_color, dtype=np.float32)
            ],
            np.full((count, 4), color, dtype=np.float32),
        ]

    @property
    def triangles(self):
        triangles = []
        for tris, norms, count in self._triangles[:-1]:
            color = self._color_arr[0][int(self._is_selected)]
            triangles.append([tris, norms, color, count, color[0][-1] < 1.0])

        tris, norms, count = self._triangles[-1]
        triangles.append([tris, norms, self._color_arr[1], count, self._color_arr[1][-1] < 1.0])
        return triangles

    @property
    def position(self) -> _point.Point:
        return self.parent.position

    def delete(self):
        self.parent.get_canvas().remove_object(self)

    def hit_test(self, point: _point.Point) -> bool:
        (p1, p2), (p3, p4) = self.hit_test_rect

        return p1 <= point <= p2 or p3 <= point <= p4


class AngleMixin:
    parent: "Frame" = None

    hit_test_rect: list[list[_point.Point, _point.Point]] = []

    _x_angle: "ArrowRing" = None
    _y_angle: "ArrowRing" = None
    _z_angle: "ArrowRing" = None

    @property
    def is_angle_shown(self) -> bool:
        return self._x_angle is not None

    @property
    def angle(self) -> _angle.Angle:
        raise NotImplementedError

    @property
    def position(self) -> _point.Point:
        raise NotImplementedError

    def stop_angle(self):
        self._x_angle.delete()
        self._y_angle.delete()
        self._z_angle.delete()

        self._x_angle = None
        self._y_angle = None
        self._z_angle = None

    def get_canvas(self):
        raise NotImplementedError

    def start_angle(self):
        p1, p2 = self.hit_test_rect[0]
        diameter = _line.Line(p1, p2).length()
        center = self.position
        radius = diameter / _decimal(1.50)

        x_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        y_angle = _angle.Angle.from_euler(90.0, 0.0, 90.0)
        z_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)

        with self.get_canvas():
            self._x_angle = ArrowRing(self, center, radius, x_angle,
                                      [0.8, 0.2, 0.2, 0.45],
                                      [1.0, 0.3, 0.3, 1.0])

            self._y_angle = ArrowRing(self, center, radius, y_angle,
                                      [0.8, 0.2, 0.2, 0.45],
                                      [1.0, 0.3, 0.3, 1.0])

            self._z_angle = ArrowRing(self, center, radius, z_angle,
                                      [0.8, 0.2, 0.2, 0.45],
                                      [1.0, 0.3, 0.3, 1.0])


class AxisIndicators(GLObject):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        cylz = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cylx = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cyly = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)

        # cylz = cylz.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 180.0)
        cylx = cylx.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 90.0)
        cyly = cyly.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), -90.0)

        xnormals, xtriangles, xcount = self.get_bundle_triangles(cylx)
        ynormals, ytriangles, ycount = self.get_bundle_triangles(cyly)
        znormals, ztriangles, zcount = self.get_bundle_triangles(cylz)

        xcolors = np.full((xcount, 4), [1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        ycolors = np.full((ycount, 4), [0.0, 1.0, 0.0, 1.0], dtype=np.float32)
        zcolors = np.full((zcount, 4), [0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        self._triangles = [
            [xtriangles, xnormals, xcolors, xcount, True],
            [ytriangles, ynormals, ycolors, ycount, True],
            [ztriangles, znormals, zcolors, zcount, True]
        ]

        self.hit_test_rect = [[new_opengl_framework.ZERO_POINT,
                               new_opengl_framework.ZERO_POINT]]

        self.parent.canvas.add_object(self)


class Housing(GLObject, MoveMixin, AngleMixin):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent

        self.cavities = []

        model, rect = self._read_stl(stl_path)

        self.hit_test_rect = [list(rect)]
        self.models = [model]

        self._point = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self._o_point = self._point.copy()
        self._point.bind(self._update_point)

        self._angle = _angle.Angle.from_points(self._point, _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.001)))
        self._o_angle = self._angle.copy()
        self._angle.bind(self._update_angle)

        normals, triangles, count = self.get_housing_triangles(model)

        self._colors = [
            np.full((count, 4), [0.4, 0.4, 0.4, 1.0], dtype=np.float32),
            np.full((count, 4), [0.6, 0.6, 1.0, 0.45], dtype=np.float32)
        ]

        normals @= self.angle
        triangles @= self.angle

        self._triangles = [[triangles, normals, count]]
        self.models = [model]

        parent.canvas.add_object(self)

    @property
    def triangles(self):
        color = self._colors[int(self._is_selected)]
        tris, norms, count = self._triangles[0]

        triangles = [[tris, norms, color, count, color[0] == 1.0]]
        return triangles

    def get_canvas(self):
        return self.parent.canvas

    @property
    def position(self) -> _point.Point:
        return self._point

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    def _update_point(self, point: _point.Point):
        delta = point - self._o_point
        self._o_point = point.copy()

        # self.triangles[3][0] += delta
        self.triangles[0][0] += delta

        for p in self.hit_test_rect[0]:
            p += delta

        self.adjust_hit_points()

    def _update_angle(self, angle: _angle.Angle):
        inverse = self._o_angle.inverse

        # self.triangles[3][0] -= self._point
        self.triangles[0][0] -= self._point

        self.triangles[0][0] @= inverse
        self.triangles[0][1] @= inverse

        self.triangles[0][0] @= angle
        self.triangles[0][1] @= angle

        # self.triangles[3][0] += self._point
        self.triangles[0][0] += self._point
        
        for p in self.hit_test_rect[0]:
            p -= self._point
            p @= inverse
            p @= angle
            p += self._point
        
        self._o_angle = angle.copy()

        self.adjust_hit_points()

    def add_cavity(self):
        if len(self.cavities) < 6:
            index = len(self.cavities)
            name = 'ABCDEF'[index]

            if self.cavities:
                pos = self.cavities[-1].point.copy()
                angle = self.cavities[-1].angle.copy()
                length = _decimal(self.cavities[-1].get_length())
            else:
                pos = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
                angle = _angle.Angle.from_euler(_decimal(0.0), _decimal(0.0), _decimal(0.0))
                length = _decimal(40.0)

            self.cavities.append(Cavity(self, index, name, angle=angle, point=pos, length=length, terminal_size=_decimal(1.5)))

    @staticmethod
    def _read_stl(path):
        model = build123d.import_stl(path)
        bb = model.bounding_box()

        center = bb.center()
        x = -center.X
        y = -center.Y
        z = -center.Z

        model = model.move(build123d.Location((x, y, z), (1, 1, 1)))

        bb = model.bounding_box()
        corner1 = _point.Point(*[_decimal(float(item)) for item in bb.min])
        corner2 = _point.Point(*[_decimal(float(item)) for item in bb.max])

        return model, (corner1, corner2)


class Cavity(GLObject, MoveMixin, AngleMixin):
    
    def __init__(self, parent: Housing, index: int, name: str, angle: _angle.Angle,
                 point: _point.Point, length: _decimal, terminal_size: _decimal):
        super().__init__()

        self.parent = parent
        self.index = index
        self.name = name
        self._rel_angle = angle
        self._o_rel_angle = angle.copy()
        self._rel_point = point
        self._o_rel_point = point.copy()
        self._test_point = point.copy()
        self._test_point.z -= _decimal(20)
        self._test_point @= angle

        self._triangles = []
        self._colors = []

        a_angle = parent.angle + angle
        a_point = parent.position + point

        self._abs_angle = a_angle
        self._o_abs_angle = a_angle.copy()

        self._abs_point = a_point
        self._o_abs_point = a_point.copy()

        self._rel_point.bind(self._update_rel_position)
        self._abs_point.bind(self._update_abs_position)

        self._rel_angle.bind(self._update_rel_angle)
        self._abs_angle.bind(self._update_abs_angle)

        self.length = length
        self.height = terminal_size
        self.width = terminal_size
        self.terminal_size = terminal_size
        self._use_cylinder = False

        point = parent.position
        self._h_point = point.copy() 
        point.bind(self._update_h_position)
        
        angle = parent.angle
        self._h_angle = angle.copy()
        angle.bind(self._update_h_angle)

        self.build_model()
        parent.parent.canvas.add_object(self)

    @property
    def position(self) -> _point.Point:
        return self._abs_point

    @property
    def rel_position(self) -> _point.Point:
        return self._rel_point

    @property
    def angle(self) -> _angle.Angle:
        return self._abs_angle

    @property
    def rel_angle(self) -> _angle.Angle:
        return self._rel_angle
    
    def _update_rel_angle(self, angle: _angle.Angle):
        inverse = self._o_rel_angle.inverse

        test_point = self._test_point.copy()
        test_point -= self._rel_point
        test_point @= inverse
        test_point @= angle
        test_point += self._rel_point

        delta = test_point - self._test_point
        self._test_point += delta

        delta = angle - self._o_rel_angle
        self._o_rel_angle += delta

        test_point += self._h_point

        new_angle = _angle.Angle.from_points(self._h_point, test_point)

        delta = new_angle - self._abs_angle

        inverse = self._abs_angle

        # self.triangles[0][0] -= self._h_point
        self._triangles[0][0] -= self._h_point

        self._triangles[0][0] @= inverse
        self._triangles[0][1] @= inverse

        self._triangles[0][0] @= new_angle
        self._triangles[0][1] @= new_angle

        # self.triangles[0][0] += self._h_point
        self._triangles[0][0] += self._h_point

        for p in self.hit_test_rect[0]:
            p -= self._h_point
            p @= inverse
            p @= new_angle
            p += self._h_point

        self._abs_angle.unbind(self._update_abs_angle)
        self._abs_angle += delta
        self._o_abs_angle += delta
        self._abs_angle.bind(self._update_abs_angle)

    def _update_abs_angle(self, angle: _angle.Angle):
        inverse = self._h_angle.inverse
        rel_inverse = self._rel_angle.inverse
        abs_inverse = self._abs_angle.inverse

        p1 = self._rel_point.copy()
        p2 = self._test_point.copy()

        p2 -= p1
        p2 @= rel_inverse
        p2 += p1
        p1 @= inverse
        p2 @= inverse
        p1 @= angle
        p2 @= angle
        p2 -= p1
        p2 @= self._rel_angle

        new_rel_angle = _angle.Angle.from_points(p1, p2)

        rel_angle_delta = new_rel_angle - self._rel_angle
        rel_point_delta = p1 - self._rel_point

        self._rel_angle.unbind(self._update_rel_angle)
        self._rel_point.unbind(self._update_rel_position)
        self._rel_angle += rel_angle_delta
        self._rel_point += rel_point_delta
        self._test_point += rel_point_delta
        self._rel_angle.bind(self._update_rel_angle)
        self._rel_point.bind(self._update_rel_position)

        normals = self._triangles[0][1]

        # normals -= self._h_point
        normals @= abs_inverse
        normals @= angle
        # normals += self._h_point

        triangles = self._triangles[0][0]
        triangles -= self._h_point
        triangles @= abs_inverse
        triangles @= angle
        triangles += self._h_point

        for p in self.hit_test_rect[0]:
            p -= self._h_point
            p @= abs_inverse
            p @= angle
            p += self._h_point

        self.adjust_hit_points()
        self._o_abs_angle = angle.copy()

        abs_point = self._abs_point.copy()
        abs_point -= self._h_point
        abs_point @= abs_inverse
        abs_point @= angle
        abs_point += self._h_point

        abs_point_delta = abs_point - self._abs_point
        self._abs_point += abs_point_delta
        self._o_abs_point += abs_point_delta

        self._triangles[0][0] = triangles
        self._triangles[0][1] = normals

    def _update_abs_position(self, point: _point.Point):
        delta = point - self._o_abs_point
        self._o_abs_point = point.copy()

        self._rel_point.unbind(self._update_rel_position)
        self._rel_point += delta
        self._o_rel_point += delta
        self._rel_point.bind(self._update_rel_position)

        self.triangles[0][0] += delta
        # self.triangles[0][0] += delta
        
        for p in self.hit_test_rect[0]:
            p += delta

        self.adjust_hit_points()

    def _update_rel_position(self, point: _point.Point):
        delta = point - self._o_rel_point
        self._o_rel_point = point.copy()

        self._abs_point.unbind(self._update_abs_position)
        self._abs_point += delta
        self._o_abs_point += delta
        self._abs_point.bind(self._update_abs_position)

        self._triangles[0][0] += delta
        # self.triangles[0][0] += delta

        for p in self.hit_test_rect[0]:
            p += delta

        self.adjust_hit_points()

    def _update_h_position(self, point: _point.Point):
        delta = point - self._h_point
        self._h_point = point.copy()
        self._abs_point += delta

    def _update_h_angle(self, angle: _angle.Angle):
        delta = angle - self._h_angle
        self._h_angle = angle.copy()
        self._abs_angle += delta

    def get_canvas(self):
        return self.parent.parent.canvas

    def set_terminal_size(self, size):
        size = _decimal(size)

        self.terminal_size = size
        self.height = size
        self.width = size
        self.build_model()
        self.get_canvas().Refresh()

    def get_terminal_size(self):
        return float(self.terminal_size)

    def use_cylinder(self, flag):
        self._use_cylinder = flag
        self.build_model()
        self.get_canvas().Refresh()

    def build_model(self):
        if self._use_cylinder:
            model = build123d.Cylinder(float(self.height) / 2, float(self.length))
        else:
            model = build123d.Box(float(self.height), float(self.width), float(self.length))

        model = model.move(build123d.Location((0, 0, float(self.length) / 2), (0, 0, 1)))

        normals, triangles, count = self.get_terminal_triangles(model)

        normals @= self.angle
        triangles @= self.angle
        triangles += self.position

        self._colors = [
            np.full((count, 4), [1.0, 0.2, 0.2, 1.0], dtype=np.float32),
            np.full((count, 4), [1.0, 0.2, 0.2, 0.45], dtype=np.float32),
        ]

        self._triangles = [[triangles, normals, count]]
        self.models = [model]

        bb = model.bounding_box()

        corner1 = _point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z))
        corner2 = _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))

        corner1 *= _decimal(0.75)
        corner2 *= _decimal(1.25)

        corner1 @= self.angle
        corner2 @= self.angle
        corner1 += self.position
        corner2 += self.position

        self.hit_test_rect = [[corner1, corner2]]

        self.adjust_hit_points()

    @property
    def triangles(self):
        color = self._colors[int(self._is_selected)]
        tris, norms, count = self._triangles[0]
        triangles = [[tris, norms, color, count, color[0][-1] == 1.0]]
        return triangles

    def get_length(self):
        return float(self.length)

    def set_length(self, value):
        self.length = _decimal(value)
        self.build_model()
        self.get_canvas().Refresh(False)


class Frame(wx.Frame):

    def __init__(self):
        w, h = wx.GetDisplaySize()
        w = (w // 3) * 2
        h = (h // 3) * 2

        wx.Frame.__init__(self, None, wx.ID_ANY, size=(w, h))
        self.CenterOnScreen()

        w, h = self.GetClientSize()

        w //= 6

        self.canvas = Canvas(self, size=(w * 5, h))
        self.cp = ControlPanel(self, size=(w, h))
        self.toolbar = wx.ToolBar(self, wx.ID_ANY)

        move_icon = wx.Bitmap('../../harness_designer/image/icons/move.png')
        rotate_icon = wx.Bitmap('../../harness_designer/image/icons/rotate.png')

        move_icon = move_icon.ConvertToImage().Scale(32, 32).ConvertToBitmap()
        rotate_icon = rotate_icon.ConvertToImage().Scale(32, 32).ConvertToBitmap()

        self.move_tool = self.toolbar.AddCheckTool(wx.ID_ANY, 'Move', move_icon)
        self.rotate_tool = self.toolbar.AddCheckTool(wx.ID_ANY, 'Rotate', rotate_icon)

        self.Bind(wx.EVT_TOOL, self.on_move_tool, id=self.move_tool.GetId())
        self.Bind(wx.EVT_TOOL, self.on_rotate_tool, id=self.rotate_tool.GetId())

        self.toolbar.Realize()

        self.SetToolBar(self.toolbar)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.canvas, 6, wx.EXPAND)
        hsizer.Add(self.cp, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(hsizer, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.housing = None
        self.rotate_object = None
        self.move_object = None

        self.axis = AxisIndicators(self)

    def get_rotate_tool_state(self):
        return self.rotate_tool.IsToggled()

    def get_move_tool_state(self):
        return self.move_tool.IsToggled()

    def on_rotate_tool(self, evt: wx.MenuEvent):
        state = self.rotate_tool.IsToggled()

        if state:
            self.move_tool.SetToggle(False)
            if self.move_object is not None:
                self.move_object.stop_move()
                self.move_object = None

            if self.canvas.selected is not None:
                self.rotate_object = self.canvas.selected
                self.rotate_object.start_angle()
                self.canvas.Refresh(False)

        elif self.rotate_object is not None:
            self.rotate_object.stop_angle()
            self.rotate_object = None

            self.canvas.Refresh(False)

        evt.Skip()

    def on_move_tool(self, evt: wx.MenuEvent):
        state = self.move_tool.IsToggled()

        if state:
            self.rotate_tool.SetToggle(False)
            if self.rotate_object is not None:
                self.rotate_object.stop_angle()
                self.rotate_object = None

            if self.canvas.selected is not None:
                self.move_object = self.canvas.selected
                self.move_object.start_move()
                self.canvas.Refresh(False)

        elif self.move_object is not None:
            self.move_object.stop_move()
            self.move_object = None

            self.canvas.Refresh(False)

        evt.Skip()

    def Show(self, flag=True):
        self.housing = Housing(self)

        wx.Frame.Show(self, flag)


if __name__ == '__main__':

    class App(wx.App):
        _frame = None

        def OnInit(self):
            self._frame = Frame()
            self._frame.Show()
            return True

    app = App()
    app.MainLoop()
