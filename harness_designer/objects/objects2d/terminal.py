from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import math

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus
from ...geometry import angle as _angle


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


class Terminal(_base2d.Base2D):
    """
    2D representation of a terminal for schematic view

    Renders as a straight line with circle for wire attachment using OpenGL.
    Supports rotation using the Angle class.
    """
    _parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal"

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        _base2d.Base2D.__init__(self, parent, db_obj)

        # Pull data from database
        self._part = db_obj.part

        # Get position from database (Point instance)
        if hasattr(db_obj, 'position2d') and db_obj.position2d:
            self._position = db_obj.position2d.point
        else:
            from ...geometry import point as _point
            self._position = _point.Point(0.0, 0.0, 0.0)

        # Get angle from database (Angle instance) - for rotation
        if hasattr(db_obj, 'angle2d') and db_obj.angle2d:
            self._angle = db_obj.angle2d
        else:
            self._angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        # Terminal visual properties
        self._radius = 3.0  # mm - circle radius
        self._line_length = 10.0  # mm - length of the line

        # Bind to position and angle changes for automatic refresh
        self._position.bind(self._on_position_changed)
        self._angle.bind(self._on_angle_changed)

    def _on_position_changed(self, *args):
        """Called when terminal position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()

    def _on_angle_changed(self, *args):
        """Called when terminal angle changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()

    def render_gl(self):
        """Render terminal using OpenGL with rotation - straight line with circle for wire attachment"""
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

        # Draw terminal line (horizontal in local space)
        GL.glColor4f(0.6, 0.4, 0.1, 1.0)  # Bronze/gold color
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(-self._line_length/2, 0.0)
        GL.glVertex2f(self._line_length/2, 0.0)
        GL.glEnd()

        # Draw connection point circle (filled) at center
        GL.glColor4f(0.8, 0.6, 0.2, 1.0)  # Lighter gold/bronze
        self._draw_circle(0.0, 0.0, self._radius, filled=True)

        # Draw circle outline
        GL.glColor4f(0.6, 0.4, 0.1, 1.0)  # Darker outline
        GL.glLineWidth(1.5)
        self._draw_circle(0.0, 0.0, self._radius, filled=False)

        # Restore transformation matrix
        GL.glPopMatrix()

    def render_selection(self):
        """Render selection highlight with rotation"""
        if self._position is None:
            return

        x = self._position.x
        y = self._position.y

        # Draw selection ring (rotation doesn't affect circular selection)
        GL.glPushMatrix()
        GL.glTranslatef(x, y, 0.0)

        GL.glColor4f(1.0, 1.0, 0.0, 0.8)  # Yellow
        GL.glLineWidth(2.5)
        self._draw_circle(0.0, 0.0, self._radius + 2.0, filled=False)

        GL.glPopMatrix()

    def _draw_circle(self, x, y, radius, filled=True, segments=16):
        """Draw a circle using OpenGL"""
        if filled:
            GL.glBegin(GL.GL_TRIANGLE_FAN)
            GL.glVertex2f(x, y)  # Center
        else:
            GL.glBegin(GL.GL_LINE_LOOP)

        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            cx = x + radius * math.cos(angle)
            cy = y + radius * math.sin(angle)
            GL.glVertex2f(cx, cy)

        GL.glEnd()

    def hit_test(self, world_x: float, world_y: float) -> bool:
        """
        Test if point is inside terminal

        For circular terminals, rotation doesn't affect hit testing
        """
        if self._position is None:
            return False

        distance = math.sqrt((world_x - self._position.x)**2 + (world_y - self._position.y)**2)
        return distance <= self._radius

    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None

        x = self._position.x
        y = self._position.y

        return (x - self._radius, y - self._radius,
                x + self._radius, y + self._radius)

    def move_to(self, world_x: float, world_y: float):
        """Move terminal to new position (use context manager)"""
        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.y = world_y


class TerminalMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire Service Loop')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire_service_loop, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Seal')
        canvas.Bind(wx.EVT_MENU, self.on_add_seal, id=item.GetId())

        self.AppendSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)

        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

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

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire_service_loop(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_seal(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
