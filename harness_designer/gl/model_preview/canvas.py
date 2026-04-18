import wx
from wx import glcanvas
from OpenGL import GL
from OpenGL import GLU
import numpy as np
from ... import utils as _utils


def _calculate_obb(vertices):
    # Calculate center
    center = np.mean(vertices, axis=0)

    # Center the points
    centered = vertices - center

    # Calculate covariance matrix
    cov = np.cov(centered.T)

    # Get eigenvectors (principal axes) and eigenvalues
    eigenvalues, eigenvectors = np.linalg.eig(cov)

    # Sort by eigenvalues (descending)
    idx = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    axes = eigenvectors[:, idx]

    # Ensure right-handed coordinate system
    if np.linalg.det(axes) < 0:
        axes[:, 2] = -axes[:, 2]

    # Project vertices onto principal axes to find extents
    projected = centered @ axes
    min_proj = np.min(projected, axis=0)
    max_proj = np.max(projected, axis=0)

    # Half-extents along each axis
    extents = (max_proj - min_proj) / 2.0

    # Adjust center to the actual OBB center
    center_offset = (max_proj + min_proj) / 2.0
    center = center + axes @ center_offset

    # Calculate 8 corners of the OBB
    corners = []
    for i in [-1, 1]:
        for j in [-1, 1]:
            for k in [-1, 1]:
                corner = center + axes @ (np.array([i, j, k]) * extents)
                corners.append(corner)

    return center, extents, np.array(corners)


def _find_best_corner_view(center, corners):
    """
    Find the best corner to view the model from (the corner that's farthest from center
    and provides a good viewing angle).

    Args:
        center: Center of the OBB
        corners: 8 corners of the OBB

    Returns:
        corner_position: The chosen corner position
        view_direction: Normalized direction from corner to center
    """
    # Find the corner that's farthest from the center
    # This will be one of the corners with all positive or all negative offsets
    distances = np.linalg.norm(corners - center, axis=1)
    farthest_idx = np.argmax(distances)
    chosen_corner = corners[farthest_idx]

    # Calculate view direction (from corner to center)
    view_direction = center - chosen_corner
    view_direction = view_direction / np.linalg.norm(view_direction)

    return chosen_corner, view_direction


def _calculate_camera_distance(extents, fov_degrees, aspect_ratio, padding_factor=1.15):
    """
    Calculate the distance the camera needs to be from the center along the corner direction
    to fit the entire model in the viewport.

    Args:
        extents: Half-extents of the OBB
        fov_degrees: Field of view in degrees
        aspect_ratio: Viewport aspect ratio (width/height)
        padding_factor: Factor to add some padding (1.15 = 15% padding)

    Returns:
        distance: Distance from center to camera position
    """
    # Calculate the diagonal of the bounding box for worst case
    diagonal = np.linalg.norm(extents * 2)

    # Convert FOV to radians
    fov_rad = np.radians(fov_degrees)

    # Calculate required distance based on vertical FOV
    distance_vertical = (diagonal / 2.0) / np.tan(fov_rad / 2.0)

    # Calculate horizontal FOV and required distance
    fov_horizontal = 2 * np.arctan(np.tan(fov_rad / 2.0) * aspect_ratio)
    distance_horizontal = (diagonal / 2.0) / np.tan(fov_horizontal / 2.0)

    # Use the larger distance to ensure the model fits
    distance = max(distance_vertical, distance_horizontal)

    # Apply padding factor
    distance *= padding_factor

    return distance


class Canvas(glcanvas.GLCanvas):

    def __init__(self, parent):
        # Request OpenGL context attributes
        attribList = [
            glcanvas.WX_GL_RGBA,
            glcanvas.WX_GL_DOUBLEBUFFER,
            glcanvas.WX_GL_DEPTH_SIZE, 24
        ]
        super().__init__(parent, attribList=attribList)

        self.context = glcanvas.GLContext(self)
        self.init = False

        self.center = None
        self.extents = None
        self.corners = None

        self.corner_pos = None
        self.view_dir = None

        self.vertices = None
        self.faces = None
        self.data = None
        self.color = None
        
        # Bind paint event
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        
    def set_model(self, color, vertices, faces):
        self.color = color
        self.vertices = vertices
        self.faces = faces
        
        if vertices is None:
            self.center = None
            self.extents = None
            self.corners = None

            self.corner_pos = None
            self.view_dir = None

            self.data = None
            
        else:
            # Calculate OBB
            self.center, self.extents, self.corners = _calculate_obb(vertices)
            self.corner_pos, self.view_dir = _find_best_corner_view(self.center, self.corners)
            self.data = _utils.compute_smoothed_vertex_normals(vertices, faces)
    
    def init_gl(self):
        self.SetCurrent(self.context)

        # Enable depth testing
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)

        # Enable lighting for better visualization
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)

        # Set light position (from corner view)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])

        # Enable smooth shading
        GL.glShadeModel(GL.GL_SMOOTH)

        # Set background color
        GL.glClearColor(0.2, 0.2, 0.2, 1.0)

        # Enable backface culling
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glCullFace(GL.GL_BACK)

        self.init = True

    def on_size(self, event):
        if not self.IsShownOnScreen():
            return

        self.SetCurrent(self.context)
        size = self.GetClientSize()
        GL.glViewport(0, 0, size.width, size.height)
        self.Refresh(False)
        event.Skip()

    def setup_projection(self):
        size = self.GetClientSize()
        if size.height == 0:
            size.height = 1

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        # Calculate aspect ratio
        aspect = size.width / float(size.height)

        # Field of view
        fov = 45.0

        # Calculate required camera distance
        distance = _calculate_camera_distance(
            self.extents, fov, aspect, padding_factor=1.15)

        # Set perspective
        near_plane = distance * 0.1
        far_plane = distance * 10.0
        GLU.gluPerspective(fov, aspect, near_plane, far_plane)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        # Camera position: move from center along the direction to the corner
        camera_eye = self.center + self.view_dir * distance

        # Calculate up vector (perpendicular to view direction, prefer world up)
        world_up = np.array([0.0, 1.0, 0.0])

        # If view direction is too close to world up, use different up vector
        if abs(np.dot(self.view_dir, world_up)) > 0.99:
            world_up = np.array([0.0, 0.0, 1.0])

        # Calculate right vector
        right = np.cross(world_up, self.view_dir)
        right = right / np.linalg.norm(right)

        # Recalculate up vector
        up = np.cross(self.view_dir, right)
        up = up / np.linalg.norm(up)

        # Set up the camera
        GLU.gluLookAt(
            camera_eye[0], camera_eye[1], camera_eye[2],      # Camera position (eye)
            self.center[0], self.center[1], self.center[2],   # Look at center (model center)
            up[0], up[1], up[2])                              # Up vector

    def render_model(self):

        if self.data is not None:
            verts, nrmls, count = self.data

            self.setup_projection()

            # Set model color
            GL.glColor4f(*self.color)

            GL.glEnableVertexAttribArray(1)

            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, verts)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, nrmls)

            GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

            GL.glDisableVertexAttribArray(0)

    def on_paint(self, event):
        """Handle paint event"""
        if not self.IsShownOnScreen():
            return

        _ = wx.PaintDC(self)
        self.SetCurrent(self.context)

        if not self.init:
            self.init_gl()

        # Clear buffers
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        # Render the model
        self.render_model()

        # Uncomment to see OBB visualization
        # self.render_obb_debug()

        # Swap buffers
        self.SwapBuffers()


# class ModelViewerFrame(wx.Frame):
#     """Main frame containing the model viewer"""
#
#     def __init__(self, vertices, faces, size=(800, 600)):
#         super().__init__(None, title="3D Model Viewer - OBB Corner View", size=size)
#
#         # Create panel
#         panel = wx.Panel(self)
#
#         # Create the OpenGL canvas as a child of the panel
#         self.canvas = ModelViewerCanvas(panel, vertices, faces)
#
#         # Create sizer
#         sizer = wx.BoxSizer(wx.VERTICAL)
#
#         sizer.Add(self.canvas, 1, wx.EXPAND)
#
#         button_sizer = wx.BoxSizer(wx.HORIZONTAL)
#
#         save_btn = wx.Button(panel, label="Save as Image")
#         save_btn.Bind(wx.EVT_BUTTON, self.on_save_image)
#         button_sizer.Add(save_btn, 0, wx.ALL, 5)
#
#         info_btn = wx.Button(panel, label="Show OBB Info")
#         info_btn.Bind(wx.EVT_BUTTON, self.on_show_info)
#         button_sizer.Add(info_btn, 0, wx.ALL, 5)
#
#         sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)
#         panel.SetSizer(sizer)
#
#         self.Center()
#
#     def on_save_image(self, event):
#         """Save the current view as an image file"""
#         with wx.FileDialog(
#             self,
#             "Save image",
#             wildcard="PNG files (*.png)|*.png",
#             style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
#         ) as fileDialog:
#
#             if fileDialog.ShowModal() == wx.ID_CANCEL:
#                 return
#
#             pathname = fileDialog.GetPath()
#             bitmap = self.canvas.get_bitmap()
#             bitmap.SaveFile(pathname, wx.BITMAP_TYPE_PNG)
#             wx.MessageBox(f"Image saved to {pathname}", "Success", wx.OK | wx.ICON_INFORMATION)
