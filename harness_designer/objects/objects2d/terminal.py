from typing import TYPE_CHECKING

import wx
from OpenGL import GL

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


class Terminal(_base2d.Base2D):
    """
    2D representation of a terminal for schematic view
    
    Renders as a connection point (circle) using OpenGL.
    """
    _parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal"

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        _base2d.Base2D.__init__(self, parent, db_obj)
        
        self._part = db_obj.part
        self._position = db_obj.position2d.point if hasattr(db_obj, 'position2d') else None
        
        # Terminal visual properties
        self._radius = 3.0  # mm
        
        # Bind to position changes
        if self._position:
            self._position.bind(self._on_position_changed)
            
    def _on_position_changed(self, *args):
        """Called when terminal position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()
            
    def render_gl(self):
        """Render terminal using OpenGL"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        
        # Draw terminal as filled circle
        GL.glColor4f(0.8, 0.6, 0.2, 1.0)  # Gold/bronze color
        self._draw_circle(x, y, self._radius, filled=True)
        
        # Draw outline
        GL.glColor4f(0.6, 0.4, 0.1, 1.0)  # Darker outline
        GL.glLineWidth(1.5)
        self._draw_circle(x, y, self._radius, filled=False)
        
    def render_selection(self):
        """Render selection highlight"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        
        # Draw selection ring
        GL.glColor4f(1.0, 1.0, 0.0, 0.8)  # Yellow
        GL.glLineWidth(2.5)
        self._draw_circle(x, y, self._radius + 2.0, filled=False)
        
    def _draw_circle(self, x, y, radius, filled=True, segments=16):
        """Draw a circle using OpenGL"""
        import math
        
        if filled:
            GL.glBegin(GL.GL_TRIANGLE_FAN)
            GL.glVertex2f(x, y)  # Center
        else:
            GL.glBegin(GL.GL_LINE_LOOP)
            
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            cx = x + radius * math.cos(angle)
            cy = y + radius * math.sin(angle)
            GL.glVertex2f(cx, cy)
            
        GL.glEnd()
        
    def hit_test(self, world_x: float, world_y: float) -> bool:
        """Test if point is inside terminal"""
        if self._position is None:
            return False
            
        import math
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
        """Move terminal to new position"""
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