import opengl_framework_for_scratches
import wx

import build123d

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

        opengl_framework_for_scratches.Canvas.__init__(self, parent, size)

    def on_left_up(self, evt: wx.MouseEvent):
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

        _add('X Angle:', self.angle_x)
        _add('Y Angle:', self.angle_y)
        _add('Z Angle:', self.angle_z)

        _add('X Position:', self.pos_x)
        _add('Y Position:', self.pos_y)
        _add('Z Position:', self.pos_z)

        _add('Cavity Length:', self.length)

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

        self.angle_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_x)
        self.angle_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_y)
        self.angle_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_angle_z)

        self.pos_x.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_x)
        self.pos_y.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_y)
        self.pos_z.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_pos_z)

        self.length.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_length)

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
            else:
                self.length.Enable(True)
                self.length.SetValue(obj.get_length())


stl_path = r'C:\Users\drsch\PycharmProjects\harness_designer\scratches\15397578.stl'

'''
pins = 6
rows = 1
length = 34.3
height = 23.13
width = 41.66

terminal_size = 1.5
centerline = 4.5


cavity_length = 0.0

'''


class Housing(GLObject):

    def __init__(self, parent):
        self.parent = parent

        super().__init__()

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

        print(count, len(normals), normals.ndim)
        # without smoothing
        # 13008 39024

        # with smoothing
        # 13008 13008


        normals @= self.angle
        triangles @= self.angle

        self.triangles = [self.get_bundle_triangles(cylx), self.get_bundle_triangles(cyly), self.get_bundle_triangles(cylz), [normals, triangles, count]]

        self.model = model

        parent.canvas.add_object(self)

    @property
    def colors(self):
        if self.is_selected:
            return [[1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0, 1.0], [0.2, 0.2, 0.2, 1.0]]
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
        print(x, y, z)

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
        self.model = None
        super().__init__()

        self.colors = [[1.0, 0.0, 0.0, 1.0]]

        self.build_model()
        parent.canvas.add_object(self)

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

    def hit_test(self, point: Point) -> bool:
        print(point)
        print(self.hit_test_rect[0])
        print(self.hit_test_rect[1])
        print()
        return GLObject.hit_test(self, point)

    def build_model(self):
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

        print(corner1)
        print(corner2)

        corner1 @= self.angle
        corner2 @= self.angle
        corner1 += self.point
        corner2 += self.point

        print(corner1)
        print(corner2)

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

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(self.canvas, 6)
        sizer.Add(self.cp, 1)

        self.SetSizer(sizer)
        self.housing = None

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
