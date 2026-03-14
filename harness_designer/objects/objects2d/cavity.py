from typing import TYPE_CHECKING

import wx
from OpenGL import GL

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base2d.Base2D):
    """
    2D representation of a cavity for schematic view
    
    Renders as a small square slot within a housing using OpenGL.
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):

        _base2d.Base2D.__init__(self, parent, db_obj)
        
        self._position = db_obj.position2d.point if hasattr(db_obj, 'position2d') else None
        
        # Cavity visual properties
        self._size = 4.0  # mm
        
        # Bind to position changes
        if self._position:
            self._position.bind(self._on_position_changed)
            
    def _on_position_changed(self, *args):
        """Called when cavity position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()
            
    def render_gl(self):
        """Render cavity using OpenGL"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        half = self._size / 2
        
        # Draw cavity as square
        GL.glColor4f(0.5, 0.5, 0.5, 0.5)  # Gray, semi-transparent
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(x - half, y - half)
        GL.glVertex2f(x + half, y - half)
        GL.glVertex2f(x + half, y + half)
        GL.glVertex2f(x - half, y + half)
        GL.glEnd()
        
        # Draw outline
        GL.glColor4f(0.3, 0.3, 0.3, 1.0)  # Dark gray
        GL.glLineWidth(1.0)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x - half, y - half)
        GL.glVertex2f(x + half, y - half)
        GL.glVertex2f(x + half, y + half)
        GL.glVertex2f(x - half, y + half)
        GL.glEnd()
        
    def render_selection(self):
        """Render selection highlight"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        half = self._size / 2 + 1.0
        
        # Draw selection outline
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glLineWidth(2.0)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x - half, y - half)
        GL.glVertex2f(x + half, y - half)
        GL.glVertex2f(x + half, y + half)
        GL.glVertex2f(x - half, y + half)
        GL.glEnd()
        
    def hit_test(self, world_x: float, world_y: float) -> bool:
        """Test if point is inside cavity"""
        if self._position is None:
            return False
            
        half = self._size / 2
        return (abs(world_x - self._position.x) <= half and
                abs(world_y - self._position.y) <= half)
                
    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None
            
        x = self._position.x
        y = self._position.y
        half = self._size / 2
        
        return (x - half, y - half, x + half, y + half)
                
    def move_to(self, world_x: float, world_y: float):
        """Move cavity to new position"""
        if self._position is None:
            return
            
        with self._position:
            self._position.x = world_x
            self._position.y = world_y
