
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

from OpenGL.GLU import *
from OpenGL.GLUT import *
from OCP.gp import *
from OCP.TopAbs import *
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopLoc import TopLoc_Location
from wx import glcanvas
import json


import threading


# Set the line below to export the model as a stl.
EXPORT_MODEL = False


# data that is used to build the model
TRANSITION1 = [
    {
        "min": 13.0,
        "max": 26.9,
        "length": 51.8,
        "bulb_length": 25.7,
        "bulb_offset": "[2.0, 0.0]",
        "angle": -180.0
    },
    {
        "min": 6.9,
        "max": 13.2,
        "length": 45.0,
        "bulb_length": 27.0,
        "angle": -45.0
    },
    {
        "min": 6.9,
        "max": 13.2,
        "length": 49.3,
        "bulb_length": 29.9,
        "angle": -15.0
    },
    {
        "min": 6.9,
        "max": 13.2,
        "length": 49.3,
        "bulb_length": 29.9,
        "angle": 15.0
    },
    {
        "min": 6.9,
        "max": 13.2,
        "length": 45.0,
        "bulb_length": 27.0,
        "angle": 45.0
    }
]

TRANSITION2 = [
    {
        "min": 15.2,
        "max": 30.5,
        "length": 47.5,
        "bulb_length": 23.8,
        "bulb_offset": "[1.0, 0.0]",
        "angle": -180.0
    },
    {
        "min": 8.9,
        "max": 17.8,
        "length": 33.8,
        "bulb_length": 16.9,
        "angle": 0.0
    },
    {
        "min": 8.9,
        "max": 17.8,
        "length": 38.1,
        "bulb_length": 19.1,
        "angle": 90.0
    }
]


TRANSITION3 = [
    {
        "min": 6.3,
        "max": 26.0,
        "length": 34.0,
        "bulb_length": 32.5,
        "bulb_offset": "[26.0, 0.0]",
        "angle": -180.0,
        "flange_height": 5.5,
        "flange_width": 5.0
    },
    {
        "min": 5.5,
        "max": 16.0,
        "length": 56.0,
        "bulb_length": 38.0,
        "angle": 0.0
    },
    {
        "min": 5.5,
        "max": 16.0,
        "length": 56.0,
        "bulb_length": 38.0,
        "angle": 30.0
    }
]


import json

used_series = []

allowed_parts = [
    # '322A012-25-0',
    # '322A112-25-0',
    # '322A315-25-0',
    # '322A412-25/225-0',
    # '322A514-25-0',
    # '341A015-25-0',
    # '342A012-25-G05/225-0',
    # '462A011-25-G05/225-0',
    # '342A112-25-0',
    # '342A215-25-0',
    # '362A014-25/225-0',
    # '382A012-25-0',
    '382W042-25/225-0',
    '462A011-25-0',
    '462A214-25/225-0',
    '462W013-25/225-0',
    '562A011-25-0'
]

with open(r'C:\Users\drsch\PycharmProjects\harness_designer\harness_designer\database\setup_db\data\transitions.json', 'r') as f:
    transition_data = f.read()

transition_data = json.loads(transition_data)


transitions = []

for transition in transition_data:
    if transition['series'] in used_series:
        continue

    if transition['part_number'] not in allowed_parts:
        continue

    used_series.append(transition['series'])

    for branch in transition['branches']:
        if 'length' not in branch:
            print(transition['part_number'])
            break
        if 'flange_height' in branch:
            print(transition['part_number'])
            break
    else:
        transitions.append(transition)

print()
print()


from decimal import Decimal as _Decimal


class Decimal(_Decimal):

    def __new__(cls, value, *args, **kwargs):
        value = str(float(value))

        return super().__new__(cls, value, *args, **kwargs)


def build_model(b_data, pos):
    model = None

    print(b_data['part_number'])

    for branch in b_data['branches']:
        print('  ', branch)
        min_dia = branch['min']
        max_dia = branch['max']
        length = branch['length']
        bulb_len = branch['bulb_length']
        angle = branch['angle']

        plane = build123d.Plane(origin=(0, 0, 0), z_dir=(1, 0, 0))

        if bulb_len:
            if 'bulb_offset' in branch:
                bulb_offset = eval(branch['bulb_offset'])
                pl = build123d.Plane(origin=(bulb_offset[0], 0, 0), z_dir=(1, 0, 0)).rotated((0, 0, angle))
            else:
                if 'offset' in branch:
                    offset = eval(branch['offset'])[0]
                    pl = build123d.Plane(origin=(offset, 0, 0), z_dir=(1, 0, 0)).rotated((0, 0, angle))
                else:
                    pl = plane.rotated((0, 0, angle))

            if model is None:
                model = pl * build123d.extrude(build123d.Circle(max_dia / 2), bulb_len)
            else:
                model += pl * build123d.extrude(build123d.Circle(max_dia / 2), bulb_len)

            if 'bulb_offset' in branch:
                bulb_offset = eval(branch['bulb_offset'])
                pl = build123d.Plane(origin=(bulb_offset[0], 0, 0), z_dir=(1, 0, 0))
                model += pl * build123d.Sphere(max_dia / 2)
                pl = build123d.Plane(origin=(bulb_offset[0] - bulb_len, 0, 0), z_dir=(1, 0, 0))
                model += pl * build123d.Sphere(max_dia / 2)
            else:
                r = math.radians(angle)
                x_pos = bulb_len * math.cos(r)
                y_pos = bulb_len * math.sin(r)

                if 'offset' in branch:
                    x_pos += eval(branch['offset'])[0]

                pl = build123d.Plane(origin=(x_pos, y_pos, 0), z_dir=(1, 0, 0))
                model += pl * build123d.Sphere(max_dia / 2).rotate(build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle)

        # if 'flange_width' in branch:
        #     fw = branch['flange_width']
        #     fh = branch['flange_height']
        #
        #     pl = plane.rotated((0, 0, angle)).move(build123d.Location(position=(-length + 11, 0, 0)))
        #     model += (pl * build123d.extrude(build123d.Circle(min_dia / 2 + 15), fw))# .rotate(build123d.Axis(origin=(0, 0, 0), direction=(0, 1, 0)), angle)
        if 'offset' in branch:
            offset = eval(branch['offset'])[0]
            pl = build123d.Plane(origin=(offset, 0, 0), z_dir=(1, 0, 0)).rotated((0, 0, angle))
        else:
            pl = plane.rotated((0, 0, angle))
        if model is None:
            model = pl * build123d.extrude(build123d.Circle(min_dia / 2), length)
        else:
            model += pl * build123d.extrude(build123d.Circle(min_dia / 2), length)

        if angle in (-180, 0):
            length += branch['length']

    model.move(build123d.Location(pos))

    return model


import python_utils


def get_angles(p1: list[Decimal, Decimal, Decimal],
               p2: list[Decimal, Decimal, Decimal]) -> tuple[Decimal, Decimal, Decimal]:

    # Convert to numpy arrays
    p1 = np.array(p1, dtype=np.dtypes.Float64DType)
    p2 = np.array(p2, dtype=np.dtypes.Float64DType)

    # create direction vector with y+ axis being "up"
    dir_vector = np.array([0.0, 1.0, 0.0], dtype=np.dtypes.Float64DType)

    # Direction vector (main axis)
    forward = p2 - p1
    forward /= np.linalg.norm(forward)

    # Temporary "up" vector
    up_temp = dir_vector - p1

    up_temp /= np.linalg.norm(up_temp)

    # Right vector (perpendicular to forward and up_temp)
    right = np.cross(up_temp, forward)  # NOQA

    right /= np.linalg.norm(right)

    # True up vector (recomputed to ensure orthogonality)
    up = np.cross(forward, right)  # NOQA

    # Build rotation matrix
    matrix = np.array([right, up, forward]).T  # 3x3 rotation matrix

    # Extract Euler angles (XYZ order)
    pitch = np.arctan2(-matrix[2, 1], matrix[2, 2])
    roll = np.arctan2(matrix[2, 0], np.sqrt(matrix[2, 1] ** 2 + matrix[2, 2] ** 2))
    yaw = np.arctan2(matrix[1, 0], matrix[0, 0])

    # convert radiant to degrees
    pitch, roll, yaw = np.degrees([pitch, roll, yaw])

    print(pitch, roll, yaw)
    return Decimal(pitch), Decimal(roll), Decimal(yaw)




# wires are constructed along the positive Z axis
#             y+
#             |  Z+
#             | /
# x+ ------ center ------ x-
#           / |
#         Z-  |
#             Y-


def create_wire(wires: list["Wire"]):
    models = []
    stripes = []

    for i, wire in enumerate(wires):
        if i > 0:
            # if there are more than 2 sections of wire we create a sphere the same diameter as the wire
            # to create a seamless connection between sections. we add the sphere to the previous wire section
            sphere = build123d.Sphere(float(wire.diameter / Decimal(2)))
            sphere.move(build123d.Location([float(item) for item in wire.p1]))
            models[-1] += sphere

        length = wire.length
        wire_r = wire.diameter / Decimal(2)

        # Create the wire
        cyl = build123d.Cylinder(float(wire_r), float(length), align=build123d.Align.NONE)

        if wire.stripe_color is None:
            stripes.append(None)
        else:
            # Extract the axis of rotation from the wire to create the stripe
            wire_axis = cyl.faces().filter_by(build123d.GeomType.CYLINDER)[0].axis_of_rotation

            # the stripe is actually a separate 3D object and it carries with it a thickness. The the stripe is not thick enough
            # the wire color will show through it. We don't want to use a hard coded thickness because the threshold
            # for for this happpening causes the stripe thickness to increaseto keep the "bleed through" from happening.
            # so a remap of the diameter to a thickness range is done to get a thickness where the bleed through will not occur
            # while keeping the stripe from looking like it is not apart of the wire.
            stripe_thickness = python_utils.remap(wire.diameter, old_min=0.5, old_max=5.0, new_min=0.005, new_max=0.015)

            stripe_arc = build123d.Face(
                (
                    cyl.edges()
                    .filter_by(build123d.GeomType.CIRCLE)
                    .sort_by(lambda e: e.distance_to(wire_axis.position))[0]
                )
                .trim_to_length(0, float(wire.diameter / Decimal(3) * Decimal(build123d.MM)))
                .offset_2d(float(stripe_thickness * Decimal(build123d.MM)), side=build123d.Side.RIGHT)
            )

            # Define the twist path to follow the wire
            twist = build123d.Helix(
                pitch=float(length / Decimal(2)),
                height=float(length),
                radius=float(wire_r),
                center=wire_axis.position,
                direction=wire_axis.direction,
            )

            # Sweep the arc to create the stripe
            stripe = build123d.sweep(
                stripe_arc, build123d.Line(wire_axis.position, float(length) * wire_axis.direction), binormal=twist
            )

            stripes.append(stripe)

        models.append(cyl)

    return models, stripes


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

        t = threading.Thread(target=self.run)
        t.daemon = True
        t.start()

    def run(self):
        count = 0

        print('loading models')
        self.make_wires()
        return

        sphere = build123d.Sphere(0.5)
        normals, triangles, triangle_count = get_triangles(sphere)
        self.triangles.append((normals, triangles, triangle_count))
        self.colors.append((1.0, 0.0, 0.0))


        for transition in transitions:
            model = build_model(transition, (125 * count + 125, 0.0, 0.0))

            if isinstance(model, build123d.topology.three_d.Solid):
                models = [model]
            else:
                models = [item for item in model if isinstance(item, build123d.topology.three_d.Solid)]

            for model in models:
                normals, triangles, triangle_count = get_triangles(model)
                self.triangles.append((normals, triangles, triangle_count))
                self.colors.append((0.2, 0.2, 0.2))
                count += 1
                wx.CallAfter(self.Refresh, False)


        print('finished loading models')

    # y axis rotation is counter clockwise

    def make_wires(self):
        wires = [
            [
                Wire((Decimal(0.0), Decimal(0.0), Decimal(0.0)),
                     (Decimal(20.0), Decimal(20.0), Decimal(0.0)),
                     Decimal(5.0), (0.55, 0.0, 0.55), (1.0, 0.65, 0.0)),
                Wire((Decimal(20.0), Decimal(20.0), Decimal(0.0)),
                     (Decimal(60.0), Decimal(20.0), Decimal(0.0)),
                     Decimal(5.0), (0.55, 0.0, 0.55), (1.0, 0.65, 0.0)),
                Wire((Decimal(60.0), Decimal(20.0), Decimal(0.0)),
                     (Decimal(10.0), Decimal(40.0), Decimal(0.0)),
                     Decimal(5.0), (0.55, 0.0, 0.55), (1.0, 0.65, 0.0))
            ],
            [Wire((Decimal(-100.0), Decimal(0.0), Decimal(-100.0)),
                  (Decimal(-100.0), Decimal(50.0), Decimal(-100)),
                  Decimal(1.0), (0.1, 0.1, 0.1), (1.0, 0.0, 0.0))]
        ]
        triangles = []
        colors = []
        models = []

        for items in wires:
            model, stripes = create_wire(items)
            models.append(model)
            models.append(stripes)

            if isinstance(model, build123d.ShapeList):
                normals = None
                tris = None
                tris_count = 0

                for item in model:
                    if not isinstance(item, build123d.Shape):
                        continue

                    n, t, tc = get_triangles(item)

                    if normals is None:
                        normals = n
                        tris = t
                    else:
                        normals = np.concatenate((normals, n))
                        tris = np.concatenate((tris, t))

                    tris_count += tc
            else:
                normals, tris, tris_count = get_triangles(model)

            triangles.append((normals, tris, tris_count))

            if isinstance(stripes, build123d.ShapeList):
                normals = None
                tris = None
                tris_count = 0

                for item in stripes:
                    if not isinstance(item, build123d.Shape):
                        continue

                    n, t, tc = get_triangles(item)

                    if normals is None:
                        normals = n
                        tris = t
                    else:
                        normals = np.concatenate((normals, n))
                        tris = np.concatenate((tris, t))

                    tris_count += tc
            else:
                normals, tris, tris_count = get_triangles(stripes)

            triangles.append((normals, tris, tris_count))

            colors.extend((items[0].color, items[0].stripe_color))

        self.triangles.extend(triangles)
        self.colors.extend(colors)
        self.models.extend(models)

        wx.CallAfter(self.Refresh, False)

    def get_world_coords(self, mx, my):
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        depth = glReadPixels(mx, my, 1.0, 1.0, GL_DEPTH_COMPONENT, GL_FLOAT, None)
        return gluUnProject(mx, my, depth, modelview, projection, viewport)

    def build_model(self):
        if self.models is None:
            self.models = [
                build_model(TRANSITION1),
                build_model(TRANSITION2),
                build_model(TRANSITION3)
            ]
            self.triangles = [get_triangles(model) for model in self.models]

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
                new_x = self.last_left_x - x
                new_y = self.last_left_y - y

                self.left_mouse_pos = [new_x, new_y]
                self.last_left_x, self.last_left_y = x, y
                self.Refresh(False)

            elif event.RightIsDown():
                factor = self.zoom

                if factor > 0.20:
                    factor = 0.20

                new_x = (self.last_right_x - x) - (factor * 4.9 * (self.last_right_x - x))
                new_y = (self.last_right_y - y) - (factor * 4.9 * (self.last_right_y - y))

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

        # glLightfv(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 100.0)
        glLightModeli(GL_LIGHT_MODEL_LOCAL_VIEWER, GL_FALSE)
        # GL_CONSTANT_ATTENUATION, GL_LINEAR_ATTENUATION, and GL_QUADRATIC_ATTENUATION
        glEnable(GL_LIGHT0)

        glMatrixMode(GL_PROJECTION)
        gluPerspective(45, w / float(h), 0.1, 1000.0)

        glMatrixMode(GL_MODELVIEW)
        gluLookAt(0.0, 2.0, -16.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)

    def OnDraw(self):

        glLoadIdentity()

        if self.left_mouse_pos is not None:
            self.right_left_angle += self.left_mouse_pos[0] * 0.1
            self.up_down_angle += self.left_mouse_pos[1] * 0.1

        glRotatef(self.up_down_angle, 1.0, 0.0, 0.0)
        glRotatef(self.right_left_angle, 0.0, 1.0, 0.0)

        glPushMatrix()
        glLoadIdentity()

        # if self.zoom is not None:
        #     glTranslatef(0, 0, self.zoom / 10.0)
        #     self.zoom = None

        if self.right_mouse_pos is not None:
            print(-self.right_mouse_pos[0] * 0.1, self.right_mouse_pos[1] * 0.1)
            glTranslatef(-self.right_mouse_pos[0] * 0.1, 0, 0)
            glTranslatef(0, self.right_mouse_pos[1] * 0.1, 0)

        glMultMatrixf(self.viewMatrix)
        self.viewMatrix = glGetFloatv(GL_MODELVIEW_MATRIX)
        #
        glPopMatrix()
        glMultMatrixf(self.viewMatrix)

        glScalef(self.zoom, self.zoom, self.zoom)

        # Clear color and depth buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glPushMatrix()
        # set the scale, "zooming"
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)

        for i, (normals, triangles, triangle_count) in enumerate(self.triangles):
            glColor3f(*self.colors[i])

            glVertexPointer(3, GL_DOUBLE, 0, triangles)
            glNormalPointer(GL_DOUBLE, 0, normals)
            glDrawArrays(GL_TRIANGLES, 0, triangle_count * 3)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glPopMatrix()

        if self.size is None:
            self.size = self.GetClientSize()

            # w, h = self.size
            # w = max(w, 1.0)
            # h = max(h, 1.0)
            # xScale = 180.0 / w
            # yScale = 180.0 / h
            #
            # x_angle = 0.0
            # y_angle = -(self.y - self.lasty) * yScale
            # z_angle = (self.x - self.lastx) * xScale
            #
            # x_rot, y_rot, z_rot = self.last_rotations
            #
            # y_rot += y_angle
            # z_rot += z_angle
            #
            # if y_rot < 0:
            #     y_rot += 360.0
            #
            # elif y_rot > 360:
            #     y_rot -= 360.0
            #
            # if z_rot < 0:
            #     z_rot += 360.0
            #
            # elif z_rot > 360:
            #     z_rot -= 360.0
            #
            # if 90.0 >= z_rot or z_rot >= 270.0:
            #     x_angle, y_angle, z_angle = y_angle, z_angle, x_angle
            #
            # glRotatef(x_angle, 1.0, 0.0, 0.0)
            # glRotatef(y_angle, 0.0, 1.0, 0.0)
            # glRotatef(z_angle, 0.0, 0.0, 1.0)
            #
            # # glRotatef((self.x / self.y) * xScale * yScale, 1.0, 0.0, 0.0)
            #
            # self.last_rotations[0] += x_angle
            # self.last_rotations[1] += y_angle
            # self.last_rotations[2] += z_angle
            #
            # for i, item in enumerate(self.last_rotations):
            #     if item < 0:
            #         self.last_rotations[i] += 360.0
            #     elif item > 360:
            #         self.last_rotations[i] -= 360.0

            # print([round(item, 2) for item in self.last_rotations])
        self.SwapBuffers()


class App(wx.App):
    _frame = None
    _canvas: Canvas = None

    def OnInit(self):
        self._frame = wx.Frame(None, wx.ID_ANY, size=(1280, 1024))
        self._canvas = Canvas(self._frame)
        self._frame.Show()

        wx.BeginBusyCursor()
        self._canvas.build_model()
        wx.EndBusyCursor()

        return True


if __name__ == '__main__':
    app = App()
    app.MainLoop()

