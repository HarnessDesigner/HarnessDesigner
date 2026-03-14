from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import math

from . import base2d as _base2d

if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


class Splice(_base2d.Base2D):
    """
    2D representation of a splice for schematic view
    
    Renders as a diamond-shaped junction point using OpenGL.
    """
    _parent: "_splice.Splice"
    db_obj: "_pjt_splice.PJTSplice"

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):

        _base2d.Base2D.__init__(self, parent, db_obj)
        
        self._position = db_obj.position2d.point if hasattr(db_obj, 'position2d') else None
        
        # Splice visual properties
        self._size = 6.0  # mm (half-width of diamond)
        
        # Bind to position changes
        if self._position:
            self._position.bind(self._on_position_changed)
            
    def _on_position_changed(self, *args):
        """Called when splice position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()
            
    def render_gl(self):
        """Render splice using OpenGL"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        
        # Draw splice as filled diamond
        GL.glColor4f(0.9, 0.9, 0.0, 1.0)  # Yellow
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(x, y - self._size)  # Top
        GL.glVertex2f(x + self._size, y)  # Right
        GL.glVertex2f(x, y + self._size)  # Bottom
        GL.glVertex2f(x - self._size, y)  # Left
        GL.glEnd()
        
        # Draw outline
        GL.glColor4f(0.6, 0.6, 0.0, 1.0)  # Darker yellow
        GL.glLineWidth(2.0)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x, y - self._size)  # Top
        GL.glVertex2f(x + self._size, y)  # Right
        GL.glVertex2f(x, y + self._size)  # Bottom
        GL.glVertex2f(x - self._size, y)  # Left
        GL.glEnd()
        
    def render_selection(self):
        """Render selection highlight"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        size = self._size + 2.0
        
        # Draw selection outline
        GL.glColor4f(1.0, 1.0, 0.0, 0.8)  # Bright yellow
        GL.glLineWidth(3.0)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x, y - size)  # Top
        GL.glVertex2f(x + size, y)  # Right
        GL.glVertex2f(x, y + size)  # Bottom
        GL.glVertex2f(x - size, y)  # Left
        GL.glEnd()
        
    def hit_test(self, world_x: float, world_y: float) -> bool:
        """Test if point is inside splice (diamond shape)"""
        if self._position is None:
            return False
            
        # Diamond hit test: |dx| + |dy| <= size
        dx = abs(world_x - self._position.x)
        dy = abs(world_y - self._position.y)
        
        return (dx + dy) <= self._size
        
    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None
            
        x = self._position.x
        y = self._position.y
        
        return (x - self._size, y - self._size,
                x + self._size, y + self._size)
                
    def move_to(self, world_x: float, world_y: float):
        """Move splice to new position"""
        if self._position is None:
            return
            
        with self._position:
            self._position.x = world_x
            self._position.y = world_y


class SpliceMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

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