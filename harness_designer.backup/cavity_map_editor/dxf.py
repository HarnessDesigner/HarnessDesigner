import wx
import math
from scipy.interpolate import BSpline
import numpy as np
import ezdxf.entities
import ezdxf


from ..geometry import line as _line
from ..geometry import point as _point
from ..wrappers.decimal import Decimal as _decimal
from .. import image_utils


def point_on_circle(radius, center, angle):
    x = center[0] + (radius * math.cos(math.radians(angle)))
    y = center[1] + (radius * math.sin(math.radians(angle)))

    return x, y


class Spline:

    def __init__(self, entity: ezdxf.entities.Spline, start_x: int, start_y: int):
        cpts = entity.control_points
        x = cpts[:, 0]
        y = cpts[:, 1]

        t_values = np.linspace(0, 1, len(x) * 10)
        spline_x = BSpline(entity.knots, x, 3)
        spline_y = BSpline(entity.knots, y, 3)

        curve_x = spline_x(t_values)
        curve_y = spline_y(t_values)

        self.coords = list(zip([int(item) - start_x for item in curve_x.tolist()], [int(item) - start_y for item in curve_y.tolist()]))

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        pl = []

        for x, y in self.coords:
            if x1 <= x <= x2 and y1 <= y <= y2:
                pl.append((x - x1, y - y1))

        gcdc.DrawPointList(pl)


class Ellipse:
    def __init__(self, entity: ezdxf.entities.Ellipse, start_x: int, start_y: int):
        start_x = _decimal(start_x)
        start_y = _decimal(start_y)

        center = _point.Point(_decimal(entity.dxf.center[0]) - start_x,
                              _decimal(entity.dxf.center[1]) - start_y,
                              _decimal(0.0))

        major = _point.Point(_decimal(entity.dxf.major_axis[0]) - start_x,
                             _decimal(entity.dxf.major_axis[1]) - start_y,
                             _decimal(0.0))

        minor = _point.Point(_decimal(entity.dxf.minor_axis[0]) - start_x,
                             _decimal(entity.dxf.minor_axis[1]) - start_y,
                             _decimal(0.0))

        semi_major_line1 = _line.Line(major, center)
        semi_minor_line1 = _line.Line(minor, center)

        major_angle = semi_major_line1.get_z_angle()
        minor_angle = semi_major_line1.get_z_angle()

        semi_major_line2 = semi_major_line1.copy()
        semi_minor_line2 = semi_minor_line1.copy()

        semi_major_line2.set_z_angle(_decimal(180.0), semi_minor_line2.p2)
        semi_minor_line2.set_z_angle(_decimal(180.0), semi_minor_line2.p2)

        major_line = _line.Line(semi_major_line1.p1, semi_major_line2.p1)
        minor_line = _line.Line(semi_minor_line1.p1, semi_minor_line2.p1)

        major_line.set_z_angle(-major_angle)
        minor_line.set_z_angle(-minor_angle + _decimal(90.0))

        start_point = _point.Point(_decimal(entity.start_point[0]) - start_x,
                                   _decimal(entity.start_point[1]) - start_y,
                                   _decimal(0.0))

        end_point = _point.Point(_decimal(entity.end_point[0]) - start_x,
                                 _decimal(entity.end_point[1]) - start_y,
                                 _decimal(0.0))

        start_point.set_z_angle(-major_angle, center)
        end_point.set_z_angle(-major_angle, center)

        start_line = _line.Line(center, start_point)
        end_line = _line.Line(center, end_point)

        w = int(major_line.length())
        h = int(minor_line.length())
        buf = bytearray([0] * (w * h * 4))
        bmp = wx.Bitmap.FromBufferRGBA(w, h, buf)

        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        gcdc = wx.GCDC(dc)

        gcdc.SetPen(wx.Pen(wx.Colour(0, 0, 0, 255), 2))
        gcdc.SetBrush(wx.TRANSPARENT_BRUSH)

        gcdc.DrawEllipticArc(0, 0, w, h, float(start_line.get_z_angle()),
                             float(end_line.get_z_angle()))

        self.bmp = image_utils.rotate_wx_bitmap(bmp, float(major_angle))

        w, h = self.bmp.GetSize()

        self.x1 = int(center.x) - int(w / 2)
        self.y1 = int(center.y) - int(w / 2)
        self.x2 = int(center.x) + int(w / 2)
        self.y2 = int(center.y) + int(w / 2)

        dc.SelectObject(wx.NullBitmap)
        gcdc.Destroy()
        del gcdc

        dc.Destroy()
        del dc

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        if (
            (x1 <= self.x1 <= x2 and y1 <= self.y1 <= y2) or
            (x1 <= self.x2 <= x2 and y1 <= self.y2 <= y2)
        ):
            gcdc.DrawBitmap(self.bmp, self.x1 - x1, self.y1 - y1)


class Line:
    def __init__(self, entity: ezdxf.entities.Line, start_x: int, start_y: int):
        self.x1 = int(entity.dxf.start[0] - start_x)
        self.y1 = int(entity.dxf.start[1] - start_y)

        self.x2 = int(entity.dxf.end[0] - start_x)
        self.y2 = int(entity.dxf.end[1] - start_y)

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        if (
            (x1 <= self.x1 <= x2 and y1 <= self.y1 <= y2) or
            (x1 <= self.x2 <= x2 and y1 <= self.y2 <= y2)
        ):
            gcdc.DrawLine((self.x1 - x1, self.y1 - y1), (self.x2 - x1, self.y2 - y1))


class LWPolyline:

    def __init__(self, entity: ezdxf.entities.LWPolyline, start_x: int, start_y: int):

        vertices = list(entity.dxf.get_points('xy'))

        for i, vert in enumerate(vertices):
            vertices[i] = [int(vert[0] - start_x), int(vert[1] - start_y)]

        lines = []
        for i in range(len(vertices)):
            lines.append((vertices[i], vertices[i - 1]))

        self.lines = lines

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        for p1, p2 in self.lines:

            if (
                (x1 <= p1[0] <= x2 and y1 <= p1[2] <= y2) or
                (x1 <= p2[0] <= x2 and y1 <= p2[1] <= y2)
            ):
                gcdc.DrawLine((p1[0] - x1, p1[2] - y1), (p2[0] - x1, p2[1] - y1))


class Circle:

    def __init__(self, entity: ezdxf.entities.Circle, start_x: int, start_y: int):
        self.x = int(entity.dxf.center[0] - start_x)
        self.y = int(entity.dxf.center[1] - start_y)
        self.radius = int(round(entity.dxf.radius))

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        xl = self.x - self.radius
        xh = self.x + self.radius
        yl = self.y - self.radius
        yh = self.y + self.radius

        for x, y in (
            (xl, yl),
            (xh, yl),
            (xh, yh),
            (xl, yh)
        ):
            if x1 <= x <= x2 and y1 <= y <= y2:
                gcdc.DrawCircle(self.x - x1, self.y - y1, self.radius)


class Arc:

    def __init__(self, entity: ezdxf.entities.Arc, start_x: int, start_y: int):
        self.x = int(entity.dxf.center[0] - start_x)
        self.y = int(entity.dxf.center[1] - start_y)

        self.radius = entity.dxf.radius
        self.start_angle = entity.dxf.start_angle
        self.end_angle = entity.dxf.end_angle

        self.start_point = self.point_on_circle(self.start_angle)
        self.end_point = self.point_on_circle(self.end_angle)

    def point_on_circle(self, angle):
        return point_on_circle(self.radius, (self.x, self.y), angle)

    def draw(self, gcdc: wx.GCDC, x1: int, y1: int, x2: int, y2: int) -> None:
        p1x, p1y = self.start_point
        p2x, p2y = self.end_point
        if (
            (x1 <= p1x <= x2 and y1 <= p1y <= y2) or
            (x1 <= p2x <= x2 and y1 <= p2y <= y2)
        ):
            p1x -= x1
            p1y -= y1
            p2x -= x1
            p2y -= y1
            gcdc.DrawArc((p2x, p2y), (p1x, p1y), (self.x - x1, self.y - y1))


class DXF:

    def __init__(self, dxf_file):
        if isinstance(dxf_file, str):
            doc = ezdxf.readfile(dxf_file)
        else:
            doc = ezdxf.read(dxf_file)

        msp = doc.modelspace()

        min_x = float('inf')
        min_y = float('inf')

        max_x = 0
        max_y = 0

        for entity in msp:
            if entity.dxftype() == 'SPLINE':
                tmp = Spline(entity, 0, 0)

                for x, y in tmp.coords:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)

                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
            elif entity.dxftype() == 'ARC':
                p1 = point_on_circle(entity.dxf.radius, entity.dxf.center,
                                     entity.dxf.start_angle)
                p2 = point_on_circle(entity.dxf.radius, entity.dxf.center,
                                     entity.dxf.end_angle)

                min_x = min(min_x, p1[0], p2[0], entity.dxf.center[0])
                min_y = min(min_y, p1[1], p2[1], entity.dxf.center[1])

                max_x = max(max_x, p1[0], p2[0], entity.dxf.center[0])
                max_y = max(max_y, p1[1], p2[1], entity.dxf.center[1])

            if entity.dxftype() == 'LINE':
                min_x = min(min_x, entity.dxf.start[0], entity.dxf.end[0])
                min_y = min(min_y, entity.dxf.start[1], entity.dxf.end[1])

                max_x = max(max_x, entity.dxf.start[0], entity.dxf.end[0])
                max_y = max(max_y, entity.dxf.start[1], entity.dxf.end[1])
            elif entity.dxftype() == 'CIRCLE':
                min_x = min(min_x, entity.dxf.center[0] - entity.dxf.radius)
                min_y = min(min_y, entity.dxf.center[1] - entity.dxf.radius)

                max_x = max(max_x, entity.dxf.center[0] + entity.dxf.radius)
                max_y = max(max_y, entity.dxf.center[1] + entity.dxf.radius)
            elif entity.dxftype() == 'LWPOLYLINE':
                vertices = list(entity.dxf.get_points('xy'))
                for vertex in vertices:
                    min_x = min(min_x, vertex[0])
                    min_y = min(min_y, vertex[1])

                    max_x = max(max_x, vertex[0])
                    max_y = max(max_y, vertex[1])

            elif entity.dxftype() == 'ELLIPSE':
                tmp = Ellipse(entity, 0, 0)

                min_x = min(min_x, tmp.x1, tmp.x2)
                min_y = min(min_y, tmp.y1, tmp.y2)

                max_x = max(max_x, tmp.x1, tmp.x2)
                max_y = max(max_y, tmp.y1, tmp.y2)

        if min_x < 1:
            min_x = 1
        if min_y < 1:
            min_y = 1

        min_x = int(round(min_x))
        min_y = int(round(min_y))

        max_x = int(round(max_x))
        max_y = int(round(max_y))

        render_objs = []
        for entity in msp:
            if entity.dxftype() == 'SPLINE':
                render_objs.append(Spline(entity, min_x, min_y))
            elif entity.dxftype() == 'ARC':
                render_objs.append(Arc(entity, min_x, min_y))
            elif entity.dxftype() == 'LINE':
                render_objs.append(Line(entity, min_x, min_y))
            elif entity.dxftype() == 'CIRCLE':
                render_objs.append(Circle(entity, min_x, min_y))
            elif entity.dxftype() == 'LWPOLYLINE':
                render_objs.append(LWPolyline(entity, min_x, min_y))
            elif entity.dxftype() == 'ELLIPSE':
                render_objs.append(Ellipse(entity, min_x, min_y))
        self.width = max_x
        self.height = max_y
        self.render_objs = render_objs

    def draw(self, gcdc, start_x, start_y, stop_x, stop_y):
        for obj in self.render_objs:
            obj.draw(gcdc, start_x, start_y, stop_x, stop_y)
