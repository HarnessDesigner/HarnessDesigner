from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import math
import numpy as np

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...geometry.decimal import Decimal as _d

if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base2d.Base2D):
    """
    2D representation of a housing for schematic view

    Renders as a rectangle with cavity positions using OpenGL.
    When moved, all child cavities move with it (hierarchical movement).
    Supports rotation using the Angle class.
    """
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):

        _base2d.Base2D.__init__(self, parent, db_obj)

        # Pull data from database
        self._part = db_obj.part

        # Get position from database (Point instance)

        self._position = db_obj.position2d

        # Get angle from database (Angle instance) - for rotation

        self._angle = db_obj.angle2d

        # Get dimensions from part if available
        self._width = float(self._part.width)
        self._height = float(self._part.height)

        # Track child cavities for hierarchical movement
        self._cavities = []

        # Bind to position and angle changes for automatic refresh
        self._position.bind(self._on_position_changed)
        self._angle.bind(self._on_angle_changed)

    def add_cavity(self, cavity):
        """
        Add a cavity to this housing

        Args:
            cavity: Cavity object to add
        """
        if cavity not in self._cavities:
            self._cavities.append(cavity)
            if hasattr(cavity, 'obj2d'):
                cavity.obj2d._housing = self

    def remove_cavity(self, cavity):
        """
        Remove a cavity from this housing

        Args:
            cavity: Cavity object to remove
        """
        try:
            self._cavities.remove(cavity)
            if hasattr(cavity, 'obj2d'):
                cavity.obj2d._housing = None
        except ValueError:
            pass

    def _on_position_changed(self, *args):
        """Called when housing position changes"""
        self.editor2d.editor.canvas.Refresh()

    def _on_angle_changed(self, *args):
        """Called when housing angle changes"""
        self.editor2d.editor.canvas.Refresh()

    def render_gl(self):
        """Render housing using OpenGL with rotation support"""
        if self._position is None:
            return

        x = self._position.x
        y = self._position.y

        # Get rotation angle (Z-axis for 2D)
        rotation_rad = self._angle.z  # Z component in radians

        # Save current transformation matrix
        GL.glPushMatrix()

        # Apply transformations: translate, then rotate
        GL.glTranslatef(x, y, 0.0)
        GL.glRotatef(math.degrees(rotation_rad), 0.0, 0.0, 1.0)

        # Draw housing body (filled) - centered at origin after translation
        GL.glColor4f(0.3, 0.3, 0.3, 0.4)  # Semi-transparent dark gray
        GL.glBegin(GL.GL_QUADS)
        h_width = self._width / 2
        h_height = self._height / 2

        GL.glVertex2f(-h_width, -h_height)
        GL.glVertex2f(h_width, -h_height)
        GL.glVertex2f(h_width, h_height)
        GL.glVertex2f(-h_width, h_height)
        GL.glEnd()

        # Draw housing outline
        GL.glColor4f(0.4, 0.4, 0.4, 1.0)  # Dark gray
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINE_LOOP)

        GL.glVertex2f(-h_width, -h_height)
        GL.glVertex2f(h_width, -h_height)
        GL.glVertex2f(h_width, h_height)
        GL.glVertex2f(-h_width, h_height)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def render_selection(self):
        """Render selection highlight with rotation"""
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

        # Draw selection outline
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glLineWidth(3.5)

        offset = 3.0
        GL.glBegin(GL.GL_LINE_LOOP)
        h_width = self._width / 2
        h_height = self._height / 2

        GL.glVertex2f(-h_width - offset, -h_height - offset)
        GL.glVertex2f(h_width + offset, -h_height - offset)
        GL.glVertex2f(h_width + offset, h_height + offset)
        GL.glVertex2f(-h_width - offset, h_height + offset)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def hit_test(self, world_pos: _point.Point) -> bool:
        """
        Test if point is inside housing (accounting for rotation)

        Uses inverse rotation to transform the point into housing's local space
        """
        if self._position is None:
            return False

        # Translate point to housing's local space
        local_pos = world_pos - self._position

        # Rotate point by negative angle (inverse rotation)
        rotation_rad = -self._angle.z
        cos_a = _d(math.cos(rotation_rad))
        sin_a = _d(math.sin(rotation_rad))

        rotated_x = local_pos.x * cos_a - local_pos.y * sin_a
        rotated_y = local_pos.x * sin_a + local_pos.y * cos_a

        # Check if within bounds
        return (abs(rotated_x) <= self._width / 2 and
                abs(rotated_y) <= self._height / 2)

    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None

        x = self._position.x
        y = self._position.y

        h_width = self._width / 2
        h_height = self._height / 2

        return (x - h_width, y - h_height,
                x + h_width, y + h_height)

    def move_to(self, world_x: float, world_y: float):
        """
        Move housing to new position

        This implements hierarchical movement - all child cavities move with the housing.
        Uses context manager to defer callbacks until all updates are complete.
        """
        if self._position is None:
            return

        # Calculate offset from current position
        dx = world_x - self._position.x
        dy = world_y - self._position.y

        # Move the housing (use context manager to defer callbacks)
        with self._position:
            self._position.x = world_x
            self._position.y = world_y

        # Move all child cavities by the same offset
        for cavity in self._cavities:
            if hasattr(cavity, 'obj2d') and hasattr(cavity.obj2d, '_position'):
                cavity_pos = cavity.obj2d._position
                if cavity_pos is not None:
                    with cavity_pos:
                        cavity_pos.x += dx
                        cavity_pos.y += dy


class HousingMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Seal')
        canvas.Bind(wx.EVT_MENU, self.on_add_seal, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Terminal')
        canvas.Bind(wx.EVT_MENU, self.on_add_terminal, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add CPA Lock')
        canvas.Bind(wx.EVT_MENU, self.on_add_cpa_lock, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add TPA Lock')
        canvas.Bind(wx.EVT_MENU, self.on_add_tpa_lock, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Cover')
        canvas.Bind(wx.EVT_MENU, self.on_add_cover, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Boot')
        canvas.Bind(wx.EVT_MENU, self.on_add_boot, id=item.GetId())

        self.AppendSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_add_seal(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_terminal(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_cpa_lock(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_tpa_lock(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_cover(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_boot(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
