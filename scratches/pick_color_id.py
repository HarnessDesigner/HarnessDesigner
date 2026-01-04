"""
pick_color_id.py
Pixel-accurate color-ID picking using an offscreen FBO.

Requirements:
 - PyOpenGL
 - numpy

How it works:
 - Create an FBO with color texture + depth renderbuffer.
 - Render the scene with a flat shader where each selectable object writes a unique RGB id color.
 - Read the pixel at the mouse coordinate to get the nearest object's ID.
 - To get the 2nd/3rd object under the pixel, re-render while excluding previously found IDs (simple repeated-pass approach).

Important:
 - Mouse coordinates must be in framebuffer pixel space (match GL viewport / framebuffer size).
 - This is exact and ignores CPU-side ray intersection logic.
"""

from OpenGL.GL import *
import numpy as np

# Utility: pack an integer id into an RGB color (8-bit per channel)
def id_to_color(obj_id):
    """Map 1..(2^24-1) -> (r,g,b) 8-bit normalized color"""
    if obj_id <= 0 or obj_id >= 2**24:
        raise ValueError("obj_id must be in [1, 2^24-1]")
    r = (obj_id >> 16) & 0xFF
    g = (obj_id >> 8) & 0xFF
    b = obj_id & 0xFF
    return (r / 255.0, g / 255.0, b / 255.0)

def color_to_id(r, g, b):
    """Convert 3 bytes (0-255) -> integer id"""
    return (int(r) << 16) | (int(g) << 8) | int(b)

# FBO helper
class IDPickerFBO:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.fbo = glGenFramebuffers(1)
        self.tex = glGenTextures(1)
        self.depth_rb = glGenRenderbuffers(1)
        self._init_fbo()

    def _init_fbo(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)

        # Color texture
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.tex, 0)

        # Depth renderbuffer
        glBindRenderbuffer(GL_RENDERBUFFER, self.depth_rb)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, self.width, self.height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, self.depth_rb)

        # set draw buffer
        glDrawBuffers([GL_COLOR_ATTACHMENT0])

        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Incomplete FBO: 0x%X" % status)

        # unbind
        glBindTexture(GL_TEXTURE_2D, 0)
        glBindRenderbuffer(GL_RENDERBUFFER, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def resize(self, width, height):
        self.width = width
        self.height = height
        glDeleteTextures([self.tex])
        glDeleteRenderbuffers(1, [self.depth_rb])
        glDeleteFramebuffers(1, [self.fbo])
        self.fbo = glGenFramebuffers(1)
        self.tex = glGenTextures(1)
        self.depth_rb = glGenRenderbuffers(1)
        self._init_fbo()

    def bind(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0, 0, self.width, self.height)

    def unbind(self, restore_viewport=None):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        if restore_viewport is not None:
            glViewport(*restore_viewport)

    def read_pixel(self, x, y):
        """
        Read one pixel from color attachment. x,y in framebuffer pixels (origin is bottom-left).
        Returns (r,g,b,a) bytes.
        """
        buf = (GLubyte * 4)(0, 0, 0, 0)
        glReadPixels(int(x), int(y), 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, buf)
        return (buf[0], buf[1], buf[2], buf[3])


# High-level picker
class IDPicker:
    def __init__(self, width, height, render_scene_callback):
        """
        width,height: size of the FBO in pixels (match your GL framebuffer size)
        render_scene_callback: function(render_id_mode, exclude_ids_set)
            - If render_id_mode is True, the callback must draw each selectable object using the id color
              (use id_to_color(obj_id) to set the shader/uniform).
            - exclude_ids_set is a set of integer IDs to skip rendering (for cycling).
            - The callback must render with depth test enabled (GL_LESS or GL_LEQUAL).
        """
        self.fbo = IDPickerFBO(width, height)
        self.render_cb = render_scene_callback
        self.width = width
        self.height = height

    def pick_nearest(self, mouse_x, mouse_y, viewport=None):
        """
        Return nearest object id under the given mouse position.
        mouse_x, mouse_y are in the same pixel coords as the GL framebuffer.
        viewport: optional (vx, vy, vw, vh) if you want to restore after pick.
        If viewport is None, it will be queried and restored.
        """
        if viewport is None:
            viewport = glGetIntegerv(GL_VIEWPORT)
            restore_viewport = tuple(viewport)
        else:
            restore_viewport = None

        self.fbo.bind()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # callback draws all objects with their id colors
        self.render_cb(render_id_mode=True, exclude_ids=set())

        # GL origin for glReadPixels is bottom-left. If your mouse coords are top-left,
        # convert before calling this function.
        fb_x = int(mouse_x)
        fb_y = int(mouse_y)

        r, g, b, a = self.fbo.read_pixel(fb_x, fb_y)
        self.fbo.unbind(restore_viewport)
        if (r, g, b) == (0, 0, 0):
            return 0  # background / no object (we reserve id 0 as none)
        return color_to_id(r, g, b)

    def pick_nth(self, mouse_x, mouse_y, n=1, viewport=None, max_iterations=64):
        """
        Return the nth object under the pixel (1-indexed). n=1 => nearest.
        This works by repeated passes that exclude previously found ids.
        For n>1 this causes extra render passes (one per found id).
        max_iterations safety guard prevents infinite loops.
        """
        if n <= 0:
            raise ValueError("n must be >= 1")

        found_ids = []
        exclude = set()
        result = 0
        iterations = 0
        while len(found_ids) < n and iterations < max_iterations:
            iterations += 1
            obj_id = self.pick_nearest(mouse_x, mouse_y, viewport=viewport) if exclude == set() else self._pick_with_exclude(mouse_x, mouse_y, exclude, viewport)
            if obj_id == 0:
                break
            found_ids.append(obj_id)
            exclude.add(obj_id)

        if len(found_ids) >= n:
            return found_ids[n-1]
        return 0  # not found

    def _pick_with_exclude(self, mouse_x, mouse_y, exclude_ids, viewport):
        """Internal: one pass excluding some IDs."""
        if viewport is None:
            viewport = glGetIntegerv(GL_VIEWPORT)
            restore_viewport = tuple(viewport)
        else:
            restore_viewport = None

        self.fbo.bind()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.render_cb(render_id_mode=True, exclude_ids=exclude_ids)

        fb_x = int(mouse_x)
        fb_y = int(mouse_y)
        r, g, b, a = self.fbo.read_pixel(fb_x, fb_y)
        self.fbo.unbind(restore_viewport)
        if (r, g, b) == (0, 0, 0):
            return 0
        return color_to_id(r, g, b)

# Example usage notes (to integrate with your renderer):
# - Maintain a mapping of object -> integer id (1..2^24-1)
# - In your render_scene_callback, when render_id_mode==True:
#       - use a shader that outputs a uniform vec3 id_color (no lighting, just constant)
#       - for each object: if obj.id not in exclude_ids: set shader uniform id_color=id_to_color(obj.id); draw object
# - For standard rendering (render_id_mode==False) just render normally.
#
# Example skeleton:
#
# def my_render_scene(render_id_mode, exclude_ids):
#     for obj in scene_objects:
#         if render_id_mode:
#             if obj.id in exclude_ids: continue
#             color = id_to_color(obj.id)
#             shader_id_flat.use()
#             shader_id_flat.set_uniform_vec3("idColor", color)
#             obj.draw()
#         else:
#             obj.draw_normally()
#
# picker = IDPicker(fbo_width, fbo_height, my_render_scene)
# # on mouse click convert mouse to framebuffer coords (bottom-left)
# obj_id = picker.pick_nth(mouse_fb_x, mouse_fb_y, n=1)  # nearest
# obj_id2 = picker.pick_nth(mouse_fb_x, mouse_fb_y, n=2)  # second, etc.

