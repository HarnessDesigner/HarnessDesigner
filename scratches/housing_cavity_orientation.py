import opengl_framework_for_scratches
import wx

import build123d
import numpy as np

from scratches.opengl_framework_for_scratches import Point


# wrapper classes to make moving code from this scratch into the production code
# easier to do

class _point:

    class Point(opengl_framework_for_scratches.Point):
        pass


class _line:

    class Line(opengl_framework_for_scratches.Line):
        pass


class _angle:

    class Angle(opengl_framework_for_scratches.Angle):
        pass


class _decimal(opengl_framework_for_scratches.Decimal):
    pass


class GLObject(opengl_framework_for_scratches.GLObject):

    def __init__(self):
        super().__init__()

    def adjust_hit_points(self):

        p1, p2 = self.hit_test_rect

        xmin = min(p1.x, p2.x)
        ymin = min(p1.y, p2.y)
        zmin = min(p1.z, p2.z)
        xmax = max(p1.x, p2.x)
        ymax = max(p1.y, p2.y)
        zmax = max(p1.z, p2.z)

        p1 = _point.Point(xmin, ymin, zmin)
        p2 = _point.Point(xmax, ymax, zmax)

        self.hit_test_rect = [p1, p2]


class Canvas(opengl_framework_for_scratches.Canvas):

    def __init__(self, parent, size):
        self.parent = parent

        self.refresh_count = 0
        self._last_selected = None
        self.last_mouse_move = [0, 0]
        self.selected_arrow_obj = None

        opengl_framework_for_scratches.Canvas.__init__(self, parent, size)

    def on_mouse_motion(self, evt: wx.MouseEvent):
        if evt.LeftIsDown():
            print('on_mouse_motion self.selected_arrow_obj:', self.selected_arrow_obj)

            if self.selected_arrow_obj is not None:
                new_x, new_y = evt.GetPosition()
                old_x, old_y = self.last_mouse_move
                self.last_mouse_move = [new_x, new_y]

                new_pos = _point.Point(_decimal(new_x), _decimal(new_y), _decimal(new_x))
                old_pos = _point.Point(_decimal(old_x), _decimal(old_y), _decimal(old_x))

                delta = new_pos - old_pos
                delta.y = -delta.y

                self.selected_arrow_obj.move(delta)
                evt.Skip()
                return

        opengl_framework_for_scratches.Canvas.on_mouse_motion(self, evt)

    def on_left_down(self, evt: wx.MouseEvent):
        import pick_full_pipeline

        x, y = evt.GetPosition()

        selected = pick_full_pipeline.handle_click_cycle(x, y, self.objects)
        print('on_left_down selected:', selected)
        print('on_left_down self.selected_arrow_obj:', self.selected_arrow_obj)
        if selected is not None:
            if self.selected_arrow_obj is not None and selected != self.selected_arrow_obj:
                self.selected_arrow_obj.is_selected = False
                self.selected_arrow_obj = None
                self.Refresh(False)

            if isinstance(selected, (ArrowMove, )):
                self.last_mouse_move = [x, y]
                self.selected_arrow_obj = selected
                self.selected_arrow_obj.is_selected = True

                if not self.HasCapture():
                    self.CaptureMouse()

                evt.Skip()
                self.Refresh(False)

                return

        elif self.selected_arrow_obj is not None:
            self.selected_arrow_obj.is_selected = False
            self.selected_arrow_obj = None
            self.Refresh(False)

        opengl_framework_for_scratches.Canvas.on_left_down(self, evt)

    def on_left_up(self, evt: wx.MouseEvent):
        if self.selected_arrow_obj is not None:
            self.selected_arrow_obj.is_selected = False
            self.selected_arrow_obj = None

            if self.HasCapture():
                self.ReleaseMouse()

            evt.Skip()
            self.Refresh(False)
            return

        opengl_framework_for_scratches.Canvas.on_left_up(self, evt)

        if self.selected != self._last_selected:
            self.parent.cp.set_selected(self.selected)
            self._last_selected = self.selected

    def __enter__(self):
        self.refresh_count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.refresh_count -= 1

    def Refresh(self, *args):
        if self.refresh_count:
            return

        opengl_framework_for_scratches.Canvas.Refresh(self, *args)

    def add_object(self, obj):
        self.objects.insert(0, obj)
        self.Refresh(False)


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

        self.pos_x = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.pos_y = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)
        self.pos_z = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="0.0", initial=0.0, min=-999.0, max=999.0, inc=0.1)

        self.length = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="1.0", initial=1.0, min=1.0, max=99.0, inc=0.1)
        self.terminal_size = wx.SpinCtrlDouble(self, wx.ID_ANY, size=(100, -1), value="1.5", initial=1.5, min=0.1, max=99.0, inc=0.1)
        self.use_cylinder = wx.CheckBox(self, wx.ID_ANY, label='')

        _add('X Angle:', self.angle_x)
        _add('Y Angle:', self.angle_y)
        _add('Z Angle:', self.angle_z)

        _add('X Position:', self.pos_x)
        _add('Y Position:', self.pos_y)
        _add('Z Position:', self.pos_z)

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

        self.pos_x.Enable(False)
        self.pos_y.Enable(False)
        self.pos_z.Enable(False)

        self.length.Enable(False)
        self.terminal_size.Enable(False)
        self.use_cylinder.Enable(False)

        self.angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_x)
        self.angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_y)
        self.angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_z)

        self.pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_x)
        self.pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_y)
        self.pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_z)

        self.length.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_length)
        self.terminal_size.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_terminal_size)
        self.use_cylinder.Bind(wx.EVT_CHECKBOX, self.on_use_cylinder)

        self.selected = None

    def on_button(self, evt):
        self.parent.housing.add_cavity()
        evt.Skip()

    def on_angle_x(self, evt):
        _, y, z = self.selected.get_angles()
        x = self.angle_x.GetValue()

        self.selected.set_angles(x, y, z)

        evt.Skip()

    def on_angle_y(self, evt):
        x, _, z = self.selected.get_angles()
        y = self.angle_y.GetValue()

        self.selected.set_angles(x, y, z)

        evt.Skip()

    def on_angle_z(self, evt):
        x, y, _ = self.selected.get_angles()
        z = self.angle_z.GetValue()

        self.selected.set_angles(x, y, z)

        evt.Skip()

    def on_pos_x(self, evt):
        _, y, z = self.selected.get_position()
        x = self.pos_x.GetValue()

        self.selected.set_position(x, y, z)

        evt.Skip()

    def on_pos_y(self, evt):
        x, _, z = self.selected.get_position()
        y = self.pos_y.GetValue()

        self.selected.set_position(x, y, z)

        evt.Skip()

    def on_pos_z(self, evt):
        x, y, _ = self.selected.get_position()
        z = self.pos_z.GetValue()

        self.selected.set_position(x, y, z)

        evt.Skip()

    def on_length(self, evt):
        length = self.length.GetValue()
        self.selected.set_length(length)
        evt.Skip()

    def on_terminal_size(self, evt):
        terminal_size = self.terminal_size.GetValue()
        self.selected.set_terminal_size(terminal_size)
        evt.Skip()

    def on_use_cylinder(self, evt):
        evt.Skip()
        value = self.use_cylinder.GetValue()
        self.selected.use_cylinder(value)

    def set_selected(self, obj):
        self.selected = obj

        if obj is None:
            self.angle_x.Enable(False)
            self.angle_y.Enable(False)
            self.angle_z.Enable(False)

            self.pos_x.Enable(False)
            self.pos_y.Enable(False)
            self.pos_z.Enable(False)

            self.length.Enable(False)
            self.terminal_size.Enable(False)
            self.use_cylinder.Enable(False)
        else:
            self.angle_x.Enable(True)
            self.angle_y.Enable(True)
            self.angle_z.Enable(True)

            self.pos_x.Enable(True)
            self.pos_y.Enable(True)
            self.pos_z.Enable(True)

            x, y, z = obj.get_angles()

            self.angle_x.SetValue(x)
            self.angle_y.SetValue(y)
            self.angle_z.SetValue(z)

            x, y, z = obj.get_position()

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


stl_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15397578.stl'

import math


# TODO: figure out the clickable region for the move arrows not being correct.
#       the region is centered like it should be but it is not wide enough to
#       cover the directional arrows.

class MoveObject:

    def __init__(self, parent, obj):
        p1, p2 = obj.hit_test_rect
        offset = p2 - p1

        scale = max(offset.x, offset.y, offset.z) / _decimal(20.0)
        offset /= _decimal(2.0)
        center = p1 + offset

        self.obj = obj
        self.parent = parent

        x_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        x_center = center.copy()
        x_center.y = p2.y + (offset.y / _decimal(2.0))
        self.x_arrow = ArrowMove(self.on_x, parent, x_center, x_angle, scale,
                                 [0.8, 0.2, 0.2, 0.45],
                                 [1.0, 0.3, 0.3, 1.0])

        y_angle = _angle.Angle.from_euler(90.0, 0.0, 90.0)

        y_center = center.copy()
        y_center.x = p2.x + (offset.x / _decimal(2.0))
        self.y_arrow = ArrowMove(self.on_y, parent, y_center, y_angle, scale,
                                 [0.2, 0.8, 0.2, 0.45],
                                 [0.3, 1.0, 0.3, 1.0])

        z_angle = _angle.Angle.from_euler(0.0, 90.0, 0.0)
        z_center = center.copy()
        z_center.x = p1.x - (offset.x / _decimal(2.0))
        self.z_arrow = ArrowMove(self.on_z, parent, z_center, z_angle, scale,
                                 [0.2, 0.2, 0.8, 0.45],
                                 [0.3, 0.3, 1.0, 1.0])

        self.x_selected = False
        self.y_selected = False
        self.z_selected = False

    def move(self, delta: _point.Point):
        # calculate the center of the object we are going to move
        p1, p2 = self.obj.hit_test_rect
        offset = p2 - p1
        offset /= _decimal(2.0)
        center = p1 + offset

        # We use the distance between the camera and the object as the
        # variable input to control how fast we want to move the object.
        # the closer the camera is to the object the smaller the distance
        # we want to move it. If we don't do this the object is going to end
        # up moving to fast at close distances and too slow at further distances
        line = _line.Line(self.parent.canvas.camera_eye, center)
        distance = line.length()
        # The 800 seems to be the sweet spot to get the object to move at the
        # same speed the mouse does no matter how close or how far away you are.
        factor = distance / _decimal(800)

        delta.z = delta.x * factor
        delta.x *= factor
        delta.y *= factor

        angle = _angle.Angle.from_points(center, self.parent.canvas.camera_pos)
        delta @= angle

        if self.x_selected:
            p = _point.Point(delta.x, _decimal(0.0), _decimal(0.0))
        elif self.y_selected:
            p = _point.Point(_decimal(0.0), delta.y, _decimal(0.0))
        elif self.z_selected:
            p = _point.Point(_decimal(0.0), _decimal(0.0), delta.z)
        else:
            return

        self.x_arrow._move(p)
        self.y_arrow._move(p)
        self.z_arrow._move(p)
        self.obj.move(p)
        self.parent.canvas.Refresh(False)

    def remove(self):
        self.x_arrow.remove()
        self.y_arrow.remove()
        self.z_arrow.remove()

    def on_x(self, obj, value, p=None):
        print('on_x', obj, p)
        if p is not None:
            self.move(p)
            return

        self.x_selected = value

    def on_y(self, obj, value, p=None):
        print('on_y', obj, p)

        if p is not None:
            self.move(p)
            return

        self.y_selected = value

    def on_z(self, obj, value, p=None):
        print('on_z', obj, p)

        if p is not None:
            self.move(p)
            return

        self.z_selected = value


class ArrowMove(GLObject):

    def __init__(self, handler, parent, center: _point.Point, angle: _angle.Angle, scale,
                 color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        self.parent = parent
        self.handler = handler
        self._color = color
        self._press_color = press_color

        super().__init__()

        opposite_angle = angle.copy()

        if angle.y:
            # opposite_angle.x += _decimal(180.0)
            opposite_angle.y += _decimal(180.0)
        elif angle.x and angle.z:
            opposite_angle.y += _decimal(180)
        else:
            opposite_angle.y = _decimal(180.0)

        arrow_1 = StraightArrow(parent, center, angle, scale, color, press_color)
        arrow_2 = StraightArrow(parent, center, opposite_angle, scale, color, press_color)

        parent.canvas.objects.remove(arrow_1)
        parent.canvas.objects.remove(arrow_2)

        self.hit_test_rect = [
            arrow_1.hit_test_rect[0],
            arrow_2.hit_test_rect[1]
        ]
        self.adjust_hit_points()

        self.triangles = [arrow_1.triangles[0], arrow_2.triangles[0]]
        parent.canvas.add_object(self)

    def move(self, delta: _point.Point):
        print('ArrowMove.move:', delta)
        self.handler(self, None, delta)

    def _move(self, delta):
        self.triangles[0][1] += delta
        self.triangles[1][1] += delta

        self.hit_test_rect[0] += delta
        self.hit_test_rect[1] += delta
        self.adjust_hit_points()

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value

        print('ArrowMove.is_selected:', value)
        self.handler(self, value)

    @property
    def colors(self):
        if self.is_selected:
            return [self._press_color, self._press_color]

        else:
            return [self._color, self._color]

    def get_triangles(self):
        return self.triangles[0][1]

    def remove(self):
        try:
            self.parent.canvas.objects.remove(self)
        except:  # NOQA
            pass


class StraightArrow(GLObject):
    _arrow: tuple[np.ndarray, np.ndarray, int] = None
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    def __init__(self, parent, center: _point.Point, angle: _angle.Angle, scale,
                 color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        self._color = color
        self._pressed_color = press_color
        self.parent = parent

        GLObject.__init__(self)

        if StraightArrow._arrow is None:
            edge = build123d.Edge.extrude(build123d.Vertex(2.0, 0.0, 0.0), (6.0, 0.0, 0.0))
            wire = build123d.Wire(edge)

            wire_angle = wire.tangent_angle_at(0) - 20.0

            # build123d.HeadType.FILLETED

            # Create the arrow head
            arrow_head = build123d.ArrowHead(size=2.0, rotation=wire_angle,
                                             head_type=build123d.HeadType.CURVED)

            polygon = build123d.Polygon((7.5, 0.20), (6.5, -0.125), (8.50, -0.125), align=None)

            arrow_head = arrow_head.move(build123d.Location((8.50, -0.125, 0.0)))

            # Trim the path so the tip of the arrow isn't lost
            trim_amount = 1.0 / wire.length
            shaft_path = wire.trim(trim_amount, 1.0)

            # Create a perpendicular line to sweep the tail path
            shaft_pen = shaft_path.perpendicular_line(0.25, 0)
            shaft = build123d.sweep(shaft_pen, shaft_path)

            arrow = arrow_head + shaft
            arrow += polygon

            arrow = build123d.extrude(arrow, 0.25, (0, 0, 1))

            bb = arrow.bounding_box()
            StraightArrow._boundingbox = [
                _point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z)),
                _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))
            ]
            StraightArrow._arrow = self.get_wire_triangles(arrow)
            StraightArrow._model = arrow

        self.models = [StraightArrow._model]
        normals, triangles, count = StraightArrow._arrow

        normals = normals.copy()
        triangles = triangles.copy()

        triangles *= float(scale)
        triangles @= angle
        normals @= angle
        triangles += center

        self.triangles = [[normals, triangles, count]]

        p1 = StraightArrow._boundingbox[0].copy()
        p2 = StraightArrow._boundingbox[1].copy()

        p1 *= scale
        p2 *= scale

        p1 *= _decimal(1.20)
        p2 *= _decimal(1.20)

        p1 @= angle
        p2 @= angle

        p1 += center
        p2 += center

        self.hit_test_rect = [p1, p2]
        self.adjust_hit_points()

        parent.canvas.add_object(self)

    def remove(self):
        try:
            self.parent.canvas.objects.remove(self)
        except:  # NOQA
            pass

    @property
    def colors(self):
        if self.is_selected:
            return [self._pressed_color]
        else:
            return [self._color]

    def get_triangles(self):
        return self.triangles[0][1]


class ArrowRing(GLObject):

    def __init__(self, handler, parent, center: _point.Point, radius: _decimal, angle: _angle.Angle,
                 color: list[float, float, float, float], press_color: list[float, float, float, float]):
        super().__init__()
        self.parent = parent
        self.handler = handler

        opposite_angle = angle.copy()

        if angle.x:
            opposite_angle.z = 180.0

        elif angle.y:
            opposite_angle.y += 180

        else:
            opposite_angle.y = 180.0

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

        self.parent.canvas.add_object(self)

        top_arrow_1 = CurvedArrow(self.on_arrow, parent, center, radius, 270 + radius,
                                  angle, color, press_color)

        top_arrow_2 = CurvedArrow(self.on_arrow, parent, center, radius, 270 + radius,
                                  opposite_angle, color, press_color)

        bot_arrow_1 = CurvedArrow(self.on_arrow, parent, center, radius, 90 + radius,
                                  mirrored_angle, color, press_color)

        bot_arrow_2 = CurvedArrow(self.on_arrow, parent, center, radius, 90 + radius,
                                  mirrored_opposite_angle, color, press_color)

        self.dir_1_arrows = [top_arrow_1, bot_arrow_2]
        self.dir_2_arrows = [top_arrow_2, bot_arrow_1]

        arc = build123d.CenterArc((0.0, 0.0, 0.0),
                                  10.0, 0.0, 360.0)

        arc = build123d.Wire(arc.edges())
        pen = arc.perpendicular_line(0.10, 0)
        ring = build123d.sweep(pen, arc)

        self.hit_test_rect = [
            _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0)),
            _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        ]
        normals, triangles, count = self.get_wire_triangles(ring)

        triangles @= angle
        normals @= angle
        triangles += center

        self.triangles = [[normals, triangles, count]]
        self.models = [ring]

        self.colors = [color]

    def on_arrow(self, arrow, value):
        if arrow in self.dir_1_arrows:
            self.handler('right', value)
        elif arrow in self.dir_2_arrows:
            self.handler('left', value)

    def get_triangles(self):
        return self.triangles[0][1]

    def remove(self):
        try:
            self.parent.canvas.objects.remove(self)
        except:  # NOQA
            pass

        for obj in self.dir_1_arrows + self.dir_2_arrows:
            obj.remove()


class CurvedArrow(GLObject):
    _arrow: tuple[np.ndarray, np.ndarray, int]
    _model = None
    _boundingbox: list[_point.Point, _point.Point] = None

    def __init__(self, handler, parent, center: _point.Point, radius: float,
                 start_angle: float, angle: _angle.Angle,
                 color: list[float, float, float, float],
                 press_color: list[float, float, float, float]):

        GLObject.__init__(self)

        self.parent = parent
        self.handler = handler

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
            CurvedArrow._arrow = self.get_wire_triangles(arrow)
            CurvedArrow._model = arrow

        self.models = [CurvedArrow._model]
        normals, triangles, count = CurvedArrow._arrow

        normals = normals.copy()
        triangles = triangles.copy()

        x = _decimal(radius * math.cos(math.radians(start_angle)))
        y = _decimal(radius * math.sin(math.radians(start_angle)))

        p = _point.Point(x, y, _decimal(0.0))

        triangles += p
        triangles @= angle
        normals @= angle

        triangles += center
        self.triangles = [[normals, triangles, count]]

        p1 = CurvedArrow._boundingbox[0].copy()
        p2 = CurvedArrow._boundingbox[1].copy()

        p1 += p
        p2 += p

        p1 @= angle
        p2 @= angle

        p1 += center
        p2 += center
        self.hit_test_rect = [p1, p2]
        self.adjust_hit_points()
        self._color = color
        self._pressed_color = press_color

        parent.canvas.add_object(self)

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value
        self.handler(self, value)

    def remove(self):
        try:
            self.parent.canvas.objects.remove(self)
        except:  # NOQA
            pass

    @property
    def colors(self):
        if self.is_selected:
            return [self._pressed_color]
        else:
            return [self._color]

    def get_triangles(self):
        return self.triangles[0][1]


class Housing(GLObject):

    def __init__(self, parent):
        self.parent = parent

        super().__init__()

        self.arrow: MoveObject = None

        self.cavities = []

        model, rect = self._read_stl(stl_path)

        self.hit_test_rect = list(rect)
        self.models = [model]

        self.point = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        self.angle = _angle.Angle.from_points(self.point, _point.Point(_decimal(0.0), _decimal(0.0), _decimal(2.0)))

        cylz = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cylx = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)
        cyly = build123d.Cylinder(0.1, 50.0, align=build123d.Align.NONE)

        # cylz = cylz.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 180.0)
        cylx = cylx.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 90.0)
        cyly = cyly.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), -90.0)

        normals, triangles, count = self.get_housing_triangles(model)

        normals @= self.angle
        triangles @= self.angle

        self.triangles = [self.get_bundle_triangles(cylx), self.get_bundle_triangles(cyly), self.get_bundle_triangles(cylz), [normals, triangles, count]]

        self.model = model

        parent.canvas.add_object(self)

    def move(self, delta: _point.Point):
        p1, p2 = self.hit_test_rect
        p1 += delta
        p2 += delta
        self.triangles[3][1] += delta

    def get_triangles(self):
        return self.triangles[3][1]

    @property
    def colors(self):
        if self.is_selected:
            return [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0], [0.6, 0.6, 1.0, 0.45]]  # [0.2, 0.2, 0.2, 1.0]]
        else:
            return [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0], [0.6, 0.6, 1.0, 0.45]]

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
                angle = _angle.Angle.from_points(pos, _point.Point(_decimal(0.0), _decimal(0.0), _decimal(10.0)))
                length = _decimal(40.0)

            self.cavities.append(Cavity(self.parent, index, name, angle=angle, point=pos, length=length, terminal_size=_decimal(1.5)))

    def get_position(self):
        return float(self.point.x), float(self.point.y), float(self.point.z)

    def set_position(self, x: float, y: float, z: float):
        point = _point.Point(_decimal(x), _decimal(y), _decimal(z))

        diff = point - self.point

        self.triangles[3][1] += diff
        self.point += diff

        for p in self.hit_test_rect:
            p += diff

        self.adjust_hit_points()

        with self.parent.canvas:
            for cavity in self.cavities:
                position = cavity.point
                position += diff

        self.parent.canvas.Refresh(False)

    def get_angles(self):
        return float(self.angle.x), float(self.angle.y), float(self.angle.z)

    def set_angles(self, x, y, z):
        angle = _angle.Angle.from_euler(x, y, z)

        inverse = self.angle.inverse

        normals = self.triangles[3][0]
        triangles = self.triangles[3][1]

        triangles -= self.point
        triangles @= inverse
        triangles @= angle
        triangles += self.point

        normals @= inverse
        normals @= angle

        self.triangles[3][0] = normals
        self.triangles[3][1] = triangles

        for p in self.hit_test_rect:
            p -= self.point
            p @= inverse
            p @= angle
            p += self.point

        self.adjust_hit_points()

        with self.parent.canvas:
            for cavity in self.cavities:
                cavity.set_housing_angle(angle, inverse)

        self.angle = angle

        self.parent.canvas.Refresh(False)

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


class Cavity(GLObject):
    def __init__(self, parent, index: int, name: str, angle: _angle.Angle,
                 point: _point.Point, length: _decimal, terminal_size: _decimal):

        self.parent = parent
        self.index = index
        self.name = name
        self.angle = angle
        self.point = point
        self.length = length
        self.height = terminal_size
        self.width = terminal_size
        self.terminal_size = terminal_size
        self._use_cylinder = False
        super().__init__()

        self.build_model()
        parent.canvas.add_object(self)

    def move(self, delta: _point.Point):
        p1, p2 = self.hit_test_rect
        p1 += delta
        p2 += delta
        self.triangles[0][1] += delta

    @property
    def colors(self):
        if self.is_selected:
            return [[1.0, 0.2, 0.2, 0.45]]
        else:
            return [[1.0, 0.2, 0.2, 0.45]]

    def get_triangles(self):
        return self.triangles[0][1]

    def set_housing_angle(self, angle: _angle.Angle, inverse: _angle.Angle):

        p1 = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(0.0))
        p2 = _point.Point(_decimal(0.0), _decimal(0.0), _decimal(10.0))

        p2 @= self.angle
        p1 += self.point
        p2 += self.point

        p1 @= inverse
        p2 @= inverse

        p1 @= angle
        p2 @= angle

        p1 -= self.point
        p2 -= self.point

        new_angle = _angle.Angle.from_points(p1, p2)

        normals = self.triangles[0][0]
        normals @= inverse
        normals @= angle

        triangles = self.triangles[0][1]
        triangles @= inverse
        triangles @= angle

        for p in self.hit_test_rect:
            p @= inverse
            p @= angle

        self.adjust_hit_points()

        self.angle.x = new_angle.x
        self.angle.y = new_angle.y
        self.angle.z = new_angle.z

        self.point @= inverse
        self.point @= angle

        self.triangles[0][0] = normals
        self.triangles[0][1] = triangles

        self.parent.canvas.Refresh(False)

    def set_terminal_size(self, size):
        size = _decimal(size)

        self.terminal_size = size
        self.height = size
        self.width = size
        self.build_model()
        self.parent.canvas.Refresh()

    def get_terminal_size(self):
        return float(self.terminal_size)

    def use_cylinder(self, flag):
        self._use_cylinder = flag
        self.build_model()
        self.parent.canvas.Refresh()

    def build_model(self):
        if self._use_cylinder:
            model = build123d.Cylinder(float(self.height) / 2, float(self.length))
        else:
            model = build123d.Box(float(self.height), float(self.width), float(self.length))

        model = model.move(build123d.Location((0, 0, float(self.length) / 2), (0, 0, 1)))

        normals, triangles, count = self.get_terminal_triangles(model)

        normals @= self.angle
        triangles @= self.angle
        triangles += self.point

        self.triangles = [[normals, triangles, count]]
        self.models = [model]

        bb = model.bounding_box()

        corner1 = _point.Point(_decimal(bb.min.X), _decimal(bb.min.Y), _decimal(bb.min.Z))
        corner2 = _point.Point(_decimal(bb.max.X), _decimal(bb.max.Y), _decimal(bb.max.Z))

        corner1 *= _decimal(0.75)
        corner2 *= _decimal(1.25)

        corner1 @= self.angle
        corner2 @= self.angle
        corner1 += self.point
        corner2 += self.point

        self.hit_test_rect = [corner1, corner2]

        self.adjust_hit_points()

    def get_length(self):
        return float(self.length)

    def set_length(self, value):
        self.length = _decimal(value)
        self.build_model()
        self.parent.canvas.Refresh(False)

    def get_position(self):
        return float(self.point.x), float(self.point.y), float(self.point.z)

    def set_position(self, x, y, z):
        point = _point.Point(_decimal(x), _decimal(y), _decimal(z))
        diff = point - self.point

        self.triangles[0][1] += diff
        self.point += diff

        for p in self.hit_test_rect:
            p += diff

        self.adjust_hit_points()

        self.parent.canvas.Refresh(False)

    def get_angles(self):
        return float(self.angle.x), float(self.angle.y), float(self.angle.z)

    def set_angles(self, x, y, z):
        angle = _angle.Angle.from_euler(x, y, z)
        inverse = self.angle.inverse

        normals = self.triangles[0][0]
        triangles = self.triangles[0][1]

        normals @= inverse
        normals @= angle

        triangles -= self.point
        triangles @= inverse
        triangles @= angle
        triangles += self.point

        self.triangles[0][0] = normals
        self.triangles[0][1] = triangles

        for p in self.hit_test_rect:
            p -= self.point
            p @= inverse
            p @= angle
            p += self.point

        self.adjust_hit_points()

        self.angle = angle
        self.parent.canvas.Refresh(False)


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

        move_icon = wx.Bitmap('../harness_designer/image/icons/move.png')
        rotate_icon = wx.Bitmap('../harness_designer/image/icons/rotate.png')

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

    def get_rotate_tool_state(self):
        return self.rotate_tool.IsToggled()

    def get_move_tool_state(self):
        return self.move_tool.IsToggled()

    def on_rotate_tool(self, evt: wx.MenuEvent):
        state = self.rotate_tool.IsToggled()

        if state:
            self.move_tool.SetToggle(False)
            if self.move_object is not None:
                self.move_object.remove()
                self.move_object = None

            if self.canvas.selected is not None:
                self.rotate_object = RotateObject(self, self.canvas.selected)
                self.canvas.Refresh(False)

        elif self.rotate_object is not None:
            self.rotate_object.remove()
            self.rotate_object = None

            self.canvas.Refresh(False)

        evt.Skip()

    def on_move_tool(self, evt: wx.MenuEvent):
        state = self.move_tool.IsToggled()

        if state:
            self.rotate_tool.SetToggle(False)
            if self.rotate_object is not None:
                self.rotate_object.remove()
                self.rotate_object = None

            if self.canvas.selected is not None:
                self.move_object = MoveObject(self, self.canvas.selected)
                self.canvas.Refresh(False)

        elif self.move_object is not None:
            self.move_object.remove()
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
