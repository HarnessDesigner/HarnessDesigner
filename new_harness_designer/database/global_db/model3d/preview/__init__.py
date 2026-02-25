import wx

import numpy as np
from wx import glcanvas
from OpenGL import GL
from OpenGL import GLU

from ..... import config as _config


Config = _config.Config.editor3d
MOUSE_REVERSE_Y_AXIS = _config.MOUSE_REVERSE_Y_AXIS
MOUSE_REVERSE_X_AXIS = _config.MOUSE_REVERSE_X_AXIS


class Preview(glcanvas.GLCanvas):

    def __init__(self, parent, size=wx.DefaultSize, pos=wx.DefaultPosition):
        glcanvas.GLCanvas.__init__(self, parent, -1, size=size, pos=pos)

        from . import context as _context
        from . import camera as _camera

        self._triangles = []

        self._init = False
        self.size = None

        self.context = _context.GLContext(self)
        self.camera = _camera.Camera(self)

        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self._on_erase_background)

        from . import key_handler as _key_handler
        from . import mouse_handler as _mouse_handler

        self._key_handler = _key_handler.KeyHandler(self)
        self._mouse_handler = _mouse_handler.MouseHandler(self)

        self._axis_planes = False
        self._plane_quads = []
        self._plane_normals = []
        self._plane_colors = []
        self._plane_edges = []
        self._plane_size = 10.0

    def show_axis_planes(self, flag):
        if flag:
            self.build_quads()
            self.build_plane_edges()
        else:
            del self._plane_quads[:]
            del self._plane_normals[:]
            del self._plane_colors[:]
            del self._plane_edges[:]
            
        self._axis_planes = flag
        
        self.refresh(False)
    
    def build_quads(self):
        """Build all quads for the three planes"""
        # XY Plane (perpendicular to Z axis) - Red
        # Split into 4 quadrants

        size = self._plane_size / 2.0
        
        xy_color = (1.0, 0.0, 0.0, 0.3)
        xy_normal = np.array([0.0, 0.0, 1.0])
        xy_quads = [np.array([[-size, -size, 0.0], [0.0, -size, 0.0],
                              [0.0, 0.0, 0.0], [-size, 0.0, 0.0]]),
                    np.array([[0.0, -size, 0.0], [size, -size, 0.0],
                              [size, 0.0, 0.0], [0.0, 0.0, 0.0]]),
                    np.array([[0.0, 0.0, 0.0], [size, 0.0, 0.0],
                              [size, size, 0.0], [0.0, size, 0.0]]),
                    np.array([[-size, 0.0, 0.0], [0.0, 0.0, 0.0],
                              [0.0, size, 0.0], [-size, size, 0.0]])]        

        # XZ Plane (perpendicular to Y axis) - Green
        xz_color = (0.0, 1.0, 0.0, 0.3)
        xz_normal = np.array([0.0, 1.0, 0.0])
        xz_quads = [np.array([[-size, 0.0, -size], [0.0, 0.0, -size],
                              [0.0, 0.0, 0.0], [-size, 0.0, 0.0]]),
                    np.array([[0.0, 0.0, -size], [size, 0.0, -size],
                              [size, 0.0, 0.0], [0.0, 0.0, 0.0]]),
                    np.array([[0.0, 0.0, 0.0], [size, 0.0, 0.0],
                              [size, 0.0, size], [0.0, 0.0, size]]),
                    np.array([[-size, 0.0, 0.0], [0.0, 0.0, 0.0],
                              [0.0, 0.0, size], [-size, 0.0, size]])]

        # YZ Plane (perpendicular to X axis) - Blue
        yz_color = (0.0, 0.0, 1.0, 0.3)
        yz_normal = np.array([1.0, 0.0, 0.0])
        yz_quads = [np.array([[0.0, -size, -size], [0.0, 0.0, -size],
                              [0.0, 0.0, 0.0], [0.0, -size, 0.0]]),
                    np.array([[0.0, 0.0, -size], [0.0, size, -size],
                              [0.0, size, 0.0], [0.0, 0.0, 0.0]]),
                    np.array([[0.0, 0.0, 0.0], [0.0, size, 0.0],
                              [0.0, size, size], [0.0, 0.0, size]]),
                    np.array([[0.0, -size, 0.0], [0.0, 0.0, 0.0],
                              [0.0, 0.0, size], [0.0, -size, size]])]

        self._plane_quads = [xy_quads, xz_quads, yz_quads]
        self._plane_normals = [xy_normal, xz_normal, yz_normal]
        self._plane_colors = [xy_color, xz_color, yz_color]

    def build_plane_edges(self):
        """Build edge data for the outer perimeter of each plane"""
        # XY Plane edges (outer boundary) - Red
        del self._plane_edges[:]

        size = self._plane_size / 2.0
        
        self._plane_edges.append({
            'edges': [
                np.array([[-size, -size, 0.0], [size, -size, 0.0]]),  # Bottom
                np.array([[size, -size, 0.0], [size, size, 0.0]]),    # Right
                np.array([[size, size, 0.0], [-size, size, 0.0]]),    # Top
                np.array([[-size, size, 0.0], [-size, -size, 0.0]]),  # Left
            ],
            'color': (1.0, 0.3, 0.3),  # Bright red for glow
            'name': 'XY'
        })

        # XZ Plane edges (outer boundary) - Green
        self._plane_edges.append({
            'edges': [
                np.array([[-size, 0.0, -size], [size, 0.0, -size]]),  # Back
                np.array([[size, 0.0, -size], [size, 0.0, size]]),    # Right
                np.array([[size, 0.0, size], [-size, 0.0, size]]),    # Front
                np.array([[-size, 0.0, size], [-size, 0.0, -size]]),  # Left
            ],
            'color': (0.3, 1.0, 0.3),  # Bright green for glow
            'name': 'XZ'
        })

        # YZ Plane edges (outer boundary) - Blue
        self._plane_edges.append({
            'edges': [
                np.array([[0.0, -size, -size], [0.0, size, -size]]),  # Back
                np.array([[0.0, size, -size], [0.0, size, size]]),    # Top
                np.array([[0.0, size, size], [0.0, -size, size]]),    # Front
                np.array([[0.0, -size, size], [0.0, -size, -size]]),  # Bottom
            ],
            'color': (0.3, 0.3, 1.0),  # Bright blue for glow
            'name': 'YZ'
        })

    @staticmethod
    def draw_edge_glow(edge_start, edge_end, color, glow_width=0.02, num_layers=5):
        """Draw a glowing edge effect with multiple layers"""
        # Draw multiple lines with decreasing alpha for glow effect
        for i in range(num_layers, 0, -1):
            alpha = (i / num_layers) * 0.8  # Outer layers more transparent
            width = glow_width * i * 2.0

            GL.glLineWidth(width)
            GL.glColor4f(color[0], color[1], color[2], alpha)

            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(*edge_start)
            GL.glVertex3f(*edge_end)
            GL.glEnd()

        # Draw the bright core
        GL.glLineWidth(1.0)
        GL.glColor4f(color[0], color[1], color[2], 1.0)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex3f(*edge_start)
        GL.glVertex3f(*edge_end)
        GL.glEnd()

    def draw_plane_edges(self):
        """Draw glowing edges for all planes"""

        saved_emission = GL.glGetMaterialfv(GL.GL_FRONT, GL.GL_EMISSION)

        GL.glDisable(GL.GL_LIGHTING)
        GL.glDepthMask(GL.GL_FALSE)

        for plane_edge in self._plane_edges:
            for edge in plane_edge['edges']:
                GL.glMaterialfv(GL.GL_FRONT, GL.GL_EMISSION, plane_edge['color'])
                self.draw_edge_glow(edge[0], edge[1], plane_edge['color'])

        GL.glDepthMask(GL.GL_TRUE)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_EMISSION, saved_emission)

    def set_model(self, triangles: list[list[np.ndarray, np.ndarray, int]], plane_size=0):
        self._triangles = triangles

        self._plane_size = plane_size
        if plane_size != 0:
            self.show_axis_planes(True)
        else:
            self.show_axis_planes(False)

        self.Refresh(False)

    def TruckPedestal(self, dx: float, dy: float) -> None:
        if Config.truck_pedestal.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.truck_pedestal.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.truck_pedestal.sensitivity
        dx *= sens
        dy *= sens

        self.camera.TruckPedestal(dx, dy, Config.truck_pedestal.speed)

    def Zoom(self, dx: float, _):
        dx *= Config.zoom.sensitivity
        self.camera.Zoom(dx)

    def Rotate(self, dx: float, dy: float) -> None:
        if Config.rotate.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.rotate.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.rotate.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Rotate(dx, dy)

    def Walk(self, dx: float, dy: float) -> None:
        if dy == 0.0:
            self.PanTilt(dx * 6.0, 0.0)
            return

        look_dx = dx

        if Config.walk.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.walk.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.walk.sensitivity
        dx *= sens
        dy *= sens

        self.camera.Walk(dx, dy, Config.walk.speed)
        self.PanTilt(look_dx * 2.0, 0.0)

    def PanTilt(self, dx: float, dy: float) -> None:
        if Config.pan_tilt.mouse & MOUSE_REVERSE_X_AXIS:
            dx = -dx

        if Config.pan_tilt.mouse & MOUSE_REVERSE_Y_AXIS:
            dy = -dy

        sens = Config.pan_tilt.sensitivity

        dx *= sens
        dy *= sens
        self.camera.PanTilt(dx, dy)

    def _on_erase_background(self, _):
        pass

    def _on_size(self, event):
        wx.CallAfter(self.DoSetViewport, event.GetSize())
        event.Skip()

    def DoSetViewport(self, size):
        width, height = self.size = size * self.GetContentScaleFactor()
        with self.context:
            GL.glViewport(0, 0, width, height)

    def _on_paint(self, _):
        _ = wx.PaintDC(self)

        with self.context:
            if not self._init:
                self.InitGL()
                self._init = True

            self.OnDraw()

    def InitGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glClearColor(0.20, 0.20, 0.20, 1.0)

        GL.glEnable(GL.GL_LIGHTING)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_BLEND)
        GL.glEnable(GL.GL_DITHER)
        GL.glEnable(GL.GL_MULTISAMPLE)
        GL.glDepthMask(GL.GL_TRUE)
        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glColorMaterial(GL.GL_FRONT, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glEnable(GL.GL_RESCALE_NORMAL)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.5, 0.5, 0.5, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])

        GL.glMaterialfv(GL.GL_FRONT, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_DIFFUSE, [0.5, 0.5, 0.5, 1.0])
        GL.glMaterialfv(GL.GL_FRONT, GL.GL_SPECULAR, [0.8, 0.8, 0.8, 1.0])
        GL.glMaterialf(GL.GL_FRONT, GL.GL_SHININESS, 80.0)

        GL.glEnable(GL.GL_LIGHT0)
        self.camera.Set()

        w, h = self.GetSize()

        aspect = w / float(h)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GLU.gluPerspective(45, aspect, 0.1, 1000.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        def _do():
            self.camera.Zoom(1.0)

        wx.CallAfter(_do)

    def OnDraw(self):
        with self.context:
            w, h = self.GetSize()
            aspect = w / float(h)

            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()
            GLU.gluPerspective(65, aspect, 0.1, 1000.0)

            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glLoadIdentity()

            self.camera.Set()

            GL.glPushMatrix()

            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

            for tris, nrmls, count in self._triangles:
                GL.glVertexPointer(3, GL.GL_DOUBLE, 0, tris)
                GL.glNormalPointer(GL.GL_DOUBLE, 0, nrmls)
                GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)

            if self._axis_planes:
                sorted_quad_indices = self.sort_quads_by_depth()

                # Disable depth writing for transparent objects
                GL.glDepthMask(GL.GL_FALSE)

                for axis_index, quad_index in sorted_quad_indices:
                    self.draw_quad(axis_index, quad_index)

                self.draw_plane_edges()

                # Re-enable depth writing
                GL.glDepthMask(GL.GL_TRUE)

            GL.glPopMatrix()

            self.SwapBuffers()
