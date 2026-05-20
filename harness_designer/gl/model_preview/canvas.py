# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Model preview canvas — wx.glcanvas.GLCanvas → QOpenGLWidget

The OBB calculation, camera setup, and all rendering logic are completely
unchanged.  Only the canvas host widget changes.
"""

import numpy as np
from OpenGL import GL
from OpenGL import GLU

from PySide6.QtCore import QSize
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from ... import utils as _utils


# ---------------------------------------------------------------------------
# Geometry helpers (unchanged)
# ---------------------------------------------------------------------------

def _calculate_obb(vertices):
    center   = np.mean(vertices, axis=0)
    centered = vertices - center
    cov      = np.cov(centered.T)

    eigenvalues, eigenvectors = np.linalg.eig(cov)
    idx        = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    axes       = eigenvectors[:, idx]

    if np.linalg.det(axes) < 0:
        axes[:, 2] = -axes[:, 2]

    projected    = centered @ axes
    min_proj     = np.min(projected, axis=0)
    max_proj     = np.max(projected, axis=0)
    extents      = (max_proj - min_proj) / 2.0
    center_offset = (max_proj + min_proj) / 2.0
    center        = center + axes @ center_offset

    corners = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            for k in [-1, 1]:
                corners.append(center + axes @ (np.array([i, j, k]) * extents))

    return center, extents, np.array(corners)


def _find_best_corner_view(center, corners):
    distances    = np.linalg.norm(corners - center, axis=1)
    farthest_idx = np.argmax(distances)
    chosen_corner = corners[farthest_idx]
    view_direction = center - chosen_corner
    view_direction /= np.linalg.norm(view_direction)
    return chosen_corner, view_direction


def _calculate_camera_distance(extents, fov_degrees, aspect_ratio, padding_factor=1.15):
    import math
    max_extent      = np.max(extents) * 2
    fov_rad         = math.radians(fov_degrees)
    dist_for_height = (max_extent / 2.0) / math.tan(fov_rad / 2.0)
    effective_fov_w = 2 * math.atan(math.tan(fov_rad / 2.0) * aspect_ratio)
    dist_for_width  = (max_extent / 2.0) / math.tan(effective_fov_w / 2.0)
    return max(dist_for_height, dist_for_width) * padding_factor


# ---------------------------------------------------------------------------
# Canvas
# ---------------------------------------------------------------------------

class Canvas(QOpenGLWidget):
    """
    Standalone 3D model preview widget.

    wx: subclassed glcanvas.GLCanvas with explicit attribList, GLContext,
        EVT_PAINT, EVT_SIZE, SetCurrent, SwapBuffers.
    Qt: subclasses QOpenGLWidget; initializeGL / resizeGL / paintGL
        override pattern; context managed automatically.
    """

    def __init__(self, parent=None):
        # Initialize parent first so setFormat() method is available
        super().__init__(parent)
        
        # Set compatibility profile to keep preview widget isolated
        # This widget uses fixed-function OpenGL for preview rendering
        from PySide6.QtGui import QSurfaceFormat
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        self.setFormat(fmt)

        self.initialized = False

        self.center     = None
        self.extents    = None
        self.corners    = None
        self.corner_pos = None
        self.view_dir   = None
        self.vertices   = None
        self.faces      = None
        self.data       = None
        self.color      = None

    # ------------------------------------------------------------------
    # Model loading (unchanged)
    # ------------------------------------------------------------------

    def set_model(self, color, vertices, faces):
        self.color    = color
        self.vertices = vertices
        self.faces    = faces

        if vertices is None:
            self.center = self.extents = self.corners = None
            self.corner_pos = self.view_dir = self.data = None
        else:
            self.center, self.extents, self.corners = _calculate_obb(vertices)
            self.corner_pos, self.view_dir = _find_best_corner_view(
                self.center, self.corners)
            self.data = _utils.compute_smoothed_vertex_normals(vertices, faces)

        self.update()

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # wx: init_gl() called lazily from on_paint; on_size; on_paint
    # Qt: initializeGL; resizeGL; paintGL
    # ------------------------------------------------------------------

    def initializeGL(self):
        """One-time GL setup (replaces init_gl called from on_paint)."""
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)

        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)

        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT,  [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE,  [0.8, 0.8, 0.8, 1.0])

        GL.glShadeModel(GL.GL_SMOOTH)
        GL.glClearColor(0.2, 0.2, 0.2, 1.0)

        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)

        self.initialized = True

    def resizeGL(self, width: int, height: int):
        """Called by Qt on resize (replaces on_size)."""
        if not self.isVisible():
            return
        GL.glViewport(0, 0, width, max(height, 1))

    def paintGL(self):
        """Render one frame (replaces on_paint)."""
        if not self.isVisible():
            return

        # wx: wx.PaintDC(self) + SetCurrent(self.context)  → not needed in Qt

        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self.render_model()
        # Qt handles SwapBuffers automatically.

    # ------------------------------------------------------------------
    # Rendering helpers (unchanged)
    # ------------------------------------------------------------------

    def setup_projection(self):
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        aspect = w / float(h)
        fov    = 45.0

        distance   = _calculate_camera_distance(self.extents, fov, aspect, 1.15)
        near_plane = distance * 0.1
        far_plane  = distance * 10.0

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(fov, aspect, near_plane, far_plane)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        camera_eye = self.center + self.view_dir * distance
        world_up   = np.array([0.0, 1.0, 0.0])

        if abs(np.dot(self.view_dir, world_up)) > 0.99:
            world_up = np.array([0.0, 0.0, 1.0])

        right = np.cross(world_up, self.view_dir)
        right /= np.linalg.norm(right)
        up    = np.cross(self.view_dir, right)
        up   /= np.linalg.norm(up)

        GLU.gluLookAt(
            camera_eye[0], camera_eye[1], camera_eye[2],
            self.center[0], self.center[1], self.center[2],
            up[0], up[1], up[2],
        )

    def render_model(self):
        if self.data is None:
            return

        verts, nrmls, count = self.data

        self.setup_projection()

        GL.glColor4f(*self.color)
        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, verts)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, nrmls)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)
        GL.glDisableVertexAttribArray(0)
