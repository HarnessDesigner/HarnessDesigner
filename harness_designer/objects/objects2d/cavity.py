
from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import math

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus
from ...geometry import angle as _angle


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity
    from ...geometry import point as _point


class Cavity(_base2d.Base2D):
    """
    2D representation of a cavity for schematic view

    Renders as a stippled (dashed) rectangular box within a housing using OpenGL.
    Cavities hold terminal pins within a housing.
    Supports rotation using the Angle class.
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):

        position = db_obj.position2d
        angle = self._angle = db_obj.angle2d

        _base2d.Base2D.__init__(self, parent, db_obj, position, angle)
        self._housing = None  # Reference to parent housing


    def _on_position_changed(self, *args):
        """Called when cavity position changes"""
        self.editor2d.editor.canvas.Refresh()

    def _on_angle_changed(self, *args):
        """Called when cavity angle changes"""
        self.editor2d.editor.canvas.Refresh()

    def render_gl(self):
        """Render cavity using OpenGL with rotation - stippled rectangular box"""
        if self._position is None:
            return

        x = self._position.x
        y = self._position.y
        rotation_rad = self._angle.z

        # Save current transformation matrix
        GL.glPushMatrix()

        # Apply transformations
        GL.glTranslatef(x, y, 0.0)
        GL.glRotatef(math.degrees(rotation_rad), 0.0, 0.0, 1.0)

        length = self.db_obj.part.length
        width = self.db_obj.part.width

        half_w = width / 2
        half_h = length / 2

        # Enable line stippling for dashed effect
        GL.glEnable(GL.GL_LINE_STIPPLE)
        GL.glLineStipple(2, 0xAAAA)  # Dashed pattern

        # Draw cavity outline as stippled rectangle (centered at origin)
        GL.glColor4f(0.5, 0.5, 0.5, 0.8)  # Gray
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(-half_w, -half_h)
        GL.glVertex2f(half_w, -half_h)
        GL.glVertex2f(half_w, half_h)
        GL.glVertex2f(-half_w, half_h)
        GL.glEnd()

        # Disable line stippling
        GL.glDisable(GL.GL_LINE_STIPPLE)

        # Draw very light fill to show the cavity area
        GL.glColor4f(0.4, 0.4, 0.4, 0.15)  # Very transparent gray
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(-half_w, -half_h)
        GL.glVertex2f(half_w, -half_h)
        GL.glVertex2f(half_w, half_h)
        GL.glVertex2f(-half_w, half_h)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def render_selection(self):
        x, y = self._position.as_float[:-1]

        rotation = self._angle.z

        # Save current transformation matrix
        GL.glPushMatrix()

        # Apply transformations
        GL.glTranslatef(x, y, 0.0)
        GL.glRotatef(rotation, 0.0, 0.0, 0.0)

        length = self.db_obj.part.length
        width = self.db_obj.part.width

        half_w = width / 2 + 1.5
        half_h = length / 2 + 1.5

        # Draw selection outline (solid, not stippled)
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(-half_w, -half_h)
        GL.glVertex2f(half_w, -half_h)
        GL.glVertex2f(half_w, half_h)
        GL.glVertex2f(-half_w, half_h)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def hit_test(self, world_pos: "_point.Point") -> bool

        if self._position is None:
            return False

        # Translate point to cavity's local space
        local_x = world_pos.x - self._position.x
        local_y = world_pos.y - self._position.y

        # Rotate point by negative angle (inverse rotation)
        rotation_rad = -self._angle.z
        cos_a = math.cos(rotation_rad)
        sin_a = math.sin(rotation_rad)

        rotated_x = local_x * cos_a - local_y * sin_a
        rotated_y = local_x * sin_a + local_y * cos_a

        length = self.db_obj.part.length
        width = self.db_obj.part.width
        
        half_w = width / 2
        half_h = length / 2
        return abs(rotated_x) <= half_w and abs(rotated_y) <= half_h

    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None

        x, y = self._position.as_float[:-1]

        length = self.db_obj.part.length
        width = self.db_obj.part.width

        half_w = width / 2
        half_h = length / 2

        return x - half_w, y - half_h, x + half_w, y + half_h

    def move_to(self, world_x: float, world_y: float):
        """Move cavity to new position (use context manager)"""
        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.y = world_y
