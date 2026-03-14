from typing import TYPE_CHECKING

import wx
from OpenGL import GL

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base2d.Base2D):
    """
    2D representation of a housing for schematic view
    
    Renders as a rectangle with cavity positions using OpenGL.
    """
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):

        _base2d.Base2D.__init__(self, parent, db_obj)

        self._part = db_obj.part
        self._position = db_obj.position2d.point if hasattr(db_obj, 'position2d') else None
        
        # Housing visual properties
        self._width = 40.0  # mm
        self._height = 30.0  # mm
        
        # Bind to position changes
        if self._position:
            self._position.bind(self._on_position_changed)
            
    def _on_position_changed(self, *args):
        """Called when housing position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()
            
    def render_gl(self):
        """Render housing using OpenGL"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        
        # Draw housing body
        GL.glColor4f(0.4, 0.4, 0.4, 1.0)  # Dark gray
        GL.glLineWidth(2.0)
        
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x - self._width/2, y - self._height/2)
        GL.glVertex2f(x + self._width/2, y - self._height/2)
        GL.glVertex2f(x + self._width/2, y + self._height/2)
        GL.glVertex2f(x - self._width/2, y + self._height/2)
        GL.glEnd()
        
        # Fill housing
        GL.glColor4f(0.3, 0.3, 0.3, 0.3)  # Semi-transparent gray
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(x - self._width/2, y - self._height/2)
        GL.glVertex2f(x + self._width/2, y - self._height/2)
        GL.glVertex2f(x + self._width/2, y + self._height/2)
        GL.glVertex2f(x - self._width/2, y + self._height/2)
        GL.glEnd()
        
    def render_selection(self):
        """Render selection highlight"""
        if self._position is None:
            return
            
        x = self._position.x
        y = self._position.y
        
        # Draw selection outline
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glLineWidth(3.0)
        
        offset = 2.0
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(x - self._width/2 - offset, y - self._height/2 - offset)
        GL.glVertex2f(x + self._width/2 + offset, y - self._height/2 - offset)
        GL.glVertex2f(x + self._width/2 + offset, y + self._height/2 + offset)
        GL.glVertex2f(x - self._width/2 - offset, y + self._height/2 + offset)
        GL.glEnd()
        
    def hit_test(self, world_x: float, world_y: float) -> bool:
        """Test if point is inside housing"""
        if self._position is None:
            return False
            
        x = self._position.x
        y = self._position.y
        
        return (abs(world_x - x) <= self._width/2 and
                abs(world_y - y) <= self._height/2)
                
    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None
            
        x = self._position.x
        y = self._position.y
        
        return (x - self._width/2, y - self._height/2,
                x + self._width/2, y + self._height/2)
                
    def move_to(self, world_x: float, world_y: float):
        """Move housing to new position"""
        if self._position is None:
            return
            
        with self._position:
            self._position.x = world_x
            self._position.y = world_y


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