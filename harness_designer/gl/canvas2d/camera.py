"""
2D Camera for Schematic Editor

Manages camera position, zoom, and viewport transformations for 2D orthographic view.
Similar to the 3D camera but simplified for 2D orthographic projection.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point

if TYPE_CHECKING:
    from . import canvas as _canvas


class Camera2D:
    """
    2D Camera for orthographic schematic view
    
    Manages:
    - Camera position (center point in world coordinates)
    - Zoom level (1.0 = 1 pixel = 1 mm)
    - Viewport transformations
    """
    
    def __init__(self, canvas: "_canvas.Canvas2D"):
        self.canvas = canvas
        
        # Camera position in world coordinates
        self._position = _point.Point(0.0, 0.0, 0.0, db_id=None)
        
        # Zoom level (1.0 = 1:1 mapping, 2.0 = 2x zoom)
        self._zoom = 1.0
        
        # Zoom limits
        self._min_zoom = 0.01
        self._max_zoom = 100.0
        
        # Bind callbacks for automatic refresh
        self._position.bind(self._on_position_changed)
        
    def _on_position_changed(self, position: _point.Point):
        """Called when camera position changes"""
        self.canvas.Refresh()
        
    @property
    def x(self) -> float:
        """Get camera X position in world coordinates"""
        return self._position.x
    
    @x.setter
    def x(self, value: float):
        """Set camera X position"""
        with self._position:
            self._position.x = float(value)
        
    @property
    def y(self) -> float:
        """Get camera Y position in world coordinates"""
        return self._position.y
    
    @y.setter
    def y(self, value: float):
        """Set camera Y position"""
        with self._position:
            self._position.y = float(value)
            
    @property
    def zoom(self) -> float:
        """Get current zoom level"""
        return self._zoom
    
    @zoom.setter
    def zoom(self, value: float):
        """Set zoom level (clamped to min/max)"""
        self._zoom = max(self._min_zoom, min(self._max_zoom, float(value)))
        self.canvas.Refresh()
        
    def pan(self, dx: float, dy: float):
        """
        Pan the camera by delta in screen pixels
        
        Args:
            dx: Change in X (screen coordinates)
            dy: Change in Y (screen coordinates)
        """
        # Convert screen delta to world delta (accounting for zoom)
        world_dx = dx / self._zoom
        world_dy = -dy / self._zoom  # Invert Y for screen coordinates
        
        with self._position:
            self._position.x -= world_dx
            self._position.y -= world_dy
            
    def zoom_at_point(self, screen_x: int, screen_y: int, zoom_delta: int):
        """
        Zoom in/out centered on a specific screen point
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            zoom_delta: Amount to change zoom (positive = zoom in)
        """
        # Get world position before zoom
        world_pos_before = self.screen_to_world(screen_x, screen_y)
        
        # Apply zoom
        zoom_factor = 1.1 if zoom_delta > 0 else 0.9
        self.zoom = self._zoom * zoom_factor
        
        # Get world position after zoom (at same screen point)
        world_pos_after = self.screen_to_world(screen_x, screen_y)
        
        # Adjust camera to keep the point under cursor
        with self._position:
            self._position.x += world_pos_before[0] - world_pos_after[0]
            self._position.y += world_pos_before[1] - world_pos_after[1]
            
    def screen_to_world(self, screen_x: int, screen_y: int) -> tuple:
        """
        Convert screen coordinates to world coordinates
        
        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            
        Returns:
            tuple: (world_x, world_y)
        """
        size = self.canvas.size
        if size is None:
            return (0.0, 0.0)
            
        width, height = size
        
        # Screen center
        center_x = width / 2.0
        center_y = height / 2.0
        
        # Offset from center
        offset_x = screen_x - center_x
        offset_y = center_y - screen_y  # Invert Y
        
        # World coordinates
        world_x = self._position.x + (offset_x / self._zoom)
        world_y = self._position.y + (offset_y / self._zoom)
        
        return (world_x, world_y)
        
    def world_to_screen(self, world_x: float, world_y: float) -> tuple:
        """
        Convert world coordinates to screen coordinates
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            tuple: (screen_x, screen_y)
        """
        size = self.canvas.size
        if size is None:
            return (0, 0)
            
        width, height = size
        
        # Offset from camera
        offset_x = (world_x - self._position.x) * self._zoom
        offset_y = (world_y - self._position.y) * self._zoom
        
        # Screen coordinates
        screen_x = (width / 2.0) + offset_x
        screen_y = (height / 2.0) - offset_y  # Invert Y
        
        return (int(screen_x), int(screen_y))
        
    def reset(self):
        """Reset camera to origin with default zoom"""
        with self._position:
            self._position.x = 0.0
            self._position.y = 0.0
        self._zoom = 1.0
        self.canvas.Refresh()
        
    def zoom_to_fit(self, objects):
        """
        Zoom camera to fit all objects in view
        
        Args:
            objects: List of objects with get_bounds() method
        """
        if not objects:
            self.reset()
            return
            
        # Calculate bounding box of all objects
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for obj in objects:
            if hasattr(obj, 'obj2d') and hasattr(obj.obj2d, 'get_bounds'):
                bounds = obj.obj2d.get_bounds()
                if bounds is not None:
                    min_x = min(min_x, bounds[0])
                    min_y = min(min_y, bounds[1])
                    max_x = max(max_x, bounds[2])
                    max_y = max(max_y, bounds[3])
                    
        if min_x == float('inf'):
            self.reset()
            return
            
        # Calculate center and zoom
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        width_obj = max_x - min_x
        height_obj = max_y - min_y
        
        size = self.canvas.size
        if size:
            canvas_width, canvas_height = size
            zoom_x = canvas_width / width_obj if width_obj > 0 else 1.0
            zoom_y = canvas_height / height_obj if height_obj > 0 else 1.0
            zoom = min(zoom_x, zoom_y) * 0.9  # 90% to add padding
            
            with self._position:
                self._position.x = center_x
                self._position.y = center_y
            self._zoom = zoom
            self.canvas.Refresh()
