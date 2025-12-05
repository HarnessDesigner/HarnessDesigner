
# mouse wheel zooms in and out and left click with drag rotates the model

import math
try:
    import wx
except ImportError:
    raise ImportError('the wxPython library is needed to run this code.  `pip install wxPython`')

try:
    import build123d
except ImportError:
    raise ImportError('the build123d library is needed to run this code.  `pip install build123d`')

try:
    from OpenGL.GL import *
except ImportError:
    raise ImportError('the PyOpenGL library is needed to run this code.  `pip install PyOpenGL`')

try:
    import numpy as np
except ImportError:
    raise ImportError('the numpy library is needed to run this code.  `pip install numpy`')

try:
    import python_utils
except ImportError:
    raise ImportError('the python-utils library is needed to run this code. `pip install python-utils`')


from OpenGL.GLU import *
from OpenGL.GLUT import *
from OCP.gp import *
from OCP.TopAbs import *
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from wx import glcanvas
import threading
from decimal import Decimal as _Decimal


# wrapper around decimal.Decimal that allows me to pass floats to the constructor
# instead if having to pass strings
class Decimal(_Decimal):

    def __new__(cls, value, *args, **kwargs):
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


# wires are constructed along the positive Z axis
#             y+
#             |  Z+
#             | /
# x+ ------ center ------ x-
#           / |
#         Z-  |
#             Y-
def create_wire(wire: "Wire"):
    length = wire.length
    wire_r = wire.diameter / Decimal(2)

    # Create the wire
    cyl = build123d.Cylinder(float(wire_r), float(length), align=build123d.Align.NONE)

    # Create helix path (centered at origin, offsets along Z)
    loop_helix = build123d.Helix(
        radius=float(wire.diameter), pitch=float(wire.diameter) + 0.13, height=float(wire.diameter) + 0.1, cone_angle=0, direction=(1, 0, 0)
    )

    loop_profile = build123d.Circle(float(wire_r) + 0.001)

    swept_cylinder = build123d.sweep(path=loop_helix, sections=(loop_helix ^ 0) * loop_profile)

    # rotate and position the loop so it align with the cylinder
    swept_cylinder = swept_cylinder.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), 90.0)
    swept_cylinder = swept_cylinder.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 8.93)
    swept_cylinder = swept_cylinder.move(build123d.Location((0.0, float(wire.diameter), 0.0), (0, 1, 0)))
    swept_cylinder = swept_cylinder.move(build123d.Location((0.0, 0.0, 0.002), (0, 0, 1)))

    # add the loop to the cylinder to make the part
    cyl += swept_cylinder

    cyl2 = build123d.Cylinder(float(wire_r), float(length) / 2, align=build123d.Align.NONE)
    cyl2 = cyl2.rotate(build123d.Axis((0.0, 0.0, 0.0), (0, 1, 0)), 179.0)
    cyl2 = cyl2.rotate(build123d.Axis((0.0, 0.0, 0.0), (1, 0, 0)), -11)

    cyl2 = cyl2.move(build123d.Location((float(wire.diameter) + (float(wire.diameter) * 0.113), 0.0, 0.0), (1, 0, 0)))
    cyl2 = cyl2.move(build123d.Location((0.0, float(wire.diameter) * 0.025, 0.0), (0, 1, 0)))
    cyl2 = cyl2.move(build123d.Location((0.0, 0.0, float(wire.diameter) * 0.035), (0, 0, 1)))

    cyl += cyl2

    wire_axis = cyl.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

    stripe_thickness = python_utils.remap(wire.diameter, old_min=1.25, old_max=5.0, new_min=0.005, new_max=0.015)
    edges = cyl.edges().filter_by(build123d.GeomType.CIRCLE)
    edges = edges.sort_by(lambda e: e.distance_to(wire_axis.position))[0]
    edges = edges.trim_to_length(0, float(wire.diameter / Decimal(3) * Decimal(build123d.MM)))

    stripe_arc = build123d.Face(edges.offset_2d(float(stripe_thickness * Decimal(build123d.MM)), side=build123d.Side.RIGHT))

    twist = build123d.Helix(
        pitch=float(length / Decimal(2)),
        height=float(length),
        radius=float(wire_r),
        center=wire_axis.position,
        direction=wire_axis.direction,
    )

    stripe = build123d.sweep(
        stripe_arc,
        build123d.Line(wire_axis.position, float(length) * wire_axis.direction),
        binormal=twist
    )

    return cyl, stripe


def get_triangles(ocp_mesh):
    loc = TopLoc_Location()  # Face locations
    mesh = BRepMesh_IncrementalMesh(
        theShape=ocp_mesh.wrapped,
        theLinDeflection=0.001,
        isRelative=True,
        theAngDeflection=0.1,
        isInParallel=True,
    )

    mesh.Perform()

    triangles = []
    normals = []
    triangle_count = 0

    for facet in ocp_mesh.faces():
        poly_triangulation = BRep_Tool.Triangulation_s(facet.wrapped, loc)  # NOQA
        trsf = loc.Transformation()

        if not facet:
            continue

        facet_reversed = facet.wrapped.Orientation() == TopAbs_REVERSED

        for tri in poly_triangulation.Triangles():
            id0, id1, id2 = tri.Get()

            if facet_reversed:
                id1, id2 = id2, id1

            aP1 = poly_triangulation.Node(id0).Transformed(trsf)
            aP2 = poly_triangulation.Node(id1).Transformed(trsf)
            aP3 = poly_triangulation.Node(id2).Transformed(trsf)

            triangles.append([[aP1.X(), aP1.Y(), aP1.Z()],
                              [aP2.X(), aP2.Y(), aP2.Z()],
                              [aP3.X(), aP3.Y(), aP3.Z()]])

            aVec1 = gp_Vec(aP1, aP2)
            aVec2 = gp_Vec(aP1, aP3)
            aVNorm = aVec1.Crossed(aVec2)

            if aVNorm.SquareMagnitude() > gp.Resolution_s():  # NOQA
                aVNorm.Normalize()
            else:
                aVNorm.SetCoord(0.0, 0.0, 0.0)

            for _ in range(3):
                normals.extend([aVNorm.X(), aVNorm.Y(), aVNorm.Z()])

            triangle_count += 3

    return (np.array(normals, dtype=np.dtypes.Float64DType),
            np.array(triangles, dtype=np.dtypes.Float64DType),
            triangle_count)


class Wire:

    def __init__(self, p1, p2, diameter, color, stripe_color):
        self.p1 = p1
        self.p2 = p2
        self.diameter = diameter
        self.color = color
        self.stripe_color = stripe_color

    @property
    def length(self):
        x = self.p2[0] - self.p1[0]
        y = self.p2[1] - self.p1[1]
        z = self.p2[2] - self.p1[2]

        return Decimal(math.sqrt(x * x + y * y + z * z))


class Canvas(glcanvas.GLCanvas):
    def __init__(self, parent):
        glcanvas.GLCanvas.__init__(self, parent, -1)
        self.init = False
        self.context = glcanvas.GLContext(self)

        self.last_left_x = 0
        self.last_left_y = 0
        self.last_right_x = 0
        self.last_right_y = 0

        self.right_mouse_pos = None
        self.left_mouse_pos = None
        self.up_down_angle = 0.0
        self.right_left_angle = 0.0
        self.viewMatrix = None
        self.zoom = 0.2

        self.size = None
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_RIGHT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.models = []
        self.normals = []
        self.triangles = []
        self.triangle_count = []
        self.colors = []
        self.loaded = False
        self.lastx = self.x = 30
        self.lasty = self.y = 30

        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def run(self):
        import time
        count = 0

        self.make_wires()
        time.sleep(3.0)

        return

    def make_wires(self):
        wire = Wire((Decimal(10.0), Decimal(0.0), Decimal(-10.0)),
                  (Decimal(-20.0), Decimal(50.0), Decimal(20.0)),
                  Decimal(1.0), (0.1, 0.1, 0.1), (1.0, 0.0, 0.0))
        
        model, stripe = create_wire(wire)

        normals, tris, tris_count = get_triangles(model)
        self.triangles.append((normals, tris, tris_count))
        
        normals, tris, tris_count = get_triangles(stripe)
        self.triangles.append((normals, tris, tris_count))

        self.colors.append(wire.color)
        self.colors.append(wire.stripe_color)

        self.loaded = True
        wx.CallAfter(self.Refresh, False)

    def get_world_coords(self, mx, my):
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        depth = glReadPixels(mx, my, 1.0, 1.0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
        return gluUnProject(mx, my, depth, modelview, projection, viewport)

    def OnEraseBackground(self, event):
        pass  # Do nothing, to avoid flashing on MSW.

    def OnSize(self, event):
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def OnMouseWheel(self, evt: wx.MouseEvent):
        if evt.GetWheelRotation() > 0:
            self.zoom += self.zoom * 0.10
        else:
            self.zoom -= self.zoom * 0.10

        self.Refresh(False)
        evt.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize() * self.GetContentScaleFactor()
        self.SetCurrent(self.context)
        glViewport(0, 0, size.width, size.height)

    def OnPaint(self, _):
        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnMouseDown(self, event: wx.MouseEvent):
        if self.HasCapture():
            self.ReleaseMouse()
        self.CaptureMouse()

        if event.LeftIsDown():
            self.left_mouse_pos = [0, 0]
            self.last_left_x, self.last_left_y = event.GetPosition()
        elif event.RightIsDown():
            self.right_mouse_pos = [0, 0]
            self.last_right_x, self.last_right_y = event.GetPosition()

    def OnMouseUp(self, _):
        if self.HasCapture():
            self.ReleaseMouse()

        self.right_mouse_pos = None
        self.left_mouse_pos = None

    def OnMouseMotion(self, event):
        if event.Dragging():
            x, y = event.GetPosition()

            if event.LeftIsDown():
                new_x = x - self.last_left_x
                new_y = y - self.last_left_y

                self.left_mouse_pos = [new_x, new_y]
                self.last_left_x, self.last_left_y = x, y
                self.Refresh(False)

            elif event.RightIsDown():
                new_x = x - self.last_right_x
                new_y = y - self.last_right_y

                self.right_mouse_pos = [new_x, new_y]
                self.last_right_x, self.last_right_y = x, y
                self.Refresh(False)

    def InitGL(self):
        w, h = self.GetSize()
        glClearColor(0.80, 0.80, 0.80, 0.0)
        glViewport(0, 0, w, h)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)
        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        # glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)

        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.1, 0.1, 0.1, 1.00])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.01, 0.01, 0.01, 1.00])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.80, 0.80, 0.80, 1.00])
        glMaterialf(GL_FRONT, GL_SHININESS, 10.0)

        glEnable(GL_LIGHT0)

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, w / float(h), 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        gluLookAt(0.0, 2.0, -16.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

    def OnDraw(self):
        glLoadIdentity()
        glMultMatrixf(self.viewMatrix)

        if self.size is None:
            self.size = self.GetClientSize()

        if self.left_mouse_pos is not None:
            dx, dy = self.left_mouse_pos
            modelView = (GLfloat * 16)()
            mvm = glGetFloatv(GL_MODELVIEW_MATRIX, modelView)

            temp = (GLfloat * 3)()
            temp[0] = mvm[0] * dy + mvm[1] * dx
            temp[1] = mvm[4] * dy + mvm[5] * dx
            temp[2] = mvm[8] * dy + mvm[9] * dx
            norm_xy = math.sqrt(temp[0] * temp[0] + temp[1] * temp[1] + temp[2] * temp[2])

            glRotatef(
                math.sqrt(dx * dx + dy * dy),
                temp[0] / norm_xy,
                temp[1] / norm_xy,
                temp[2] / norm_xy
            )

            self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

        glScalef(self.zoom, self.zoom, self.zoom)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        if self.loaded:
            for i, (normals, triangles, triangle_count) in enumerate(self.triangles):
                glColor3f(*self.colors[i])

                glVertexPointer(3, GL_DOUBLE, 0, triangles)
                glNormalPointer(GL_DOUBLE, 0, normals)
                glDrawArrays(GL_TRIANGLES, 0, triangle_count)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glPopMatrix()

        self.SwapBuffers()


class App(wx.App):
    _frame = None
    _canvas: Canvas = None

    def OnInit(self):
        self._frame = wx.Frame(None, wx.ID_ANY, size=(1280, 1024))
        self._canvas = Canvas(self._frame)
        self._frame.Show()

        wx.BeginBusyCursor()
        wx.EndBusyCursor()

        return True


if __name__ == '__main__':
    app = App()
    app.MainLoop()
