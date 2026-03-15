"""
2D Camera for Schematic Editor

Manages camera position, zoom, and viewport transformations for 2D orthographic view.
Uses distance-based zoom similar to 3D camera, where zoom changes the distance between
the camera and the focal plane.
"""

from typing import TYPE_CHECKING

from ...geometry import point as _point

if TYPE_CHECKING:
    from . import canvas as _canvas


class Camera2D:
    """
    2D Camera for orthographic schematic view

    Similar to 3D camera but adapted for 2D orthographic projection:
    - Focal position: center point in world coordinates (what we're looking at)
    - Distance: camera distance from focal plane (controls zoom)
    - Pan: moves focal position
    - Zoom: changes distance (closer = more zoomed in, farther = more zoomed out)
    """

    def __init__(self, canvas: "_canvas.Canvas2D"):
        self.canvas = canvas

        # Focal position - the point in world coordinates we're looking at (center of view)
        self._focal_position = _point.Point(0.0, 0.0, 0.0)

        # Distance from camera to focal plane (controls zoom level)
        # Higher distance = see more (zoomed out), lower distance = see less (zoomed in)
        self._distance = 1000.0  # Default distance in "units"

        # Distance limits (controls zoom range)
        self._min_distance = 10.0    # Max zoom in
        self._max_distance = 100000.0  # Max zoom out

        # Bind callbacks for automatic refresh
        self._focal_position.bind(self._on_focal_position_changed)

    def _on_focal_position_changed(self, _: _point.Point):
        """Called when focal position changes"""
        self.canvas.Refresh(False)

    @property
    def x(self) -> float:
        """Get focal position X in world coordinates"""
        return self._focal_position.x

    @x.setter
    def x(self, value: float):
        """Set focal position X"""
        with self._focal_position:
            self._focal_position.x = float(value)

    @property
    def y(self) -> float:
        """Get focal position Y in world coordinates"""
        return self._focal_position.y

    @y.setter
    def y(self, value: float):
        """Set focal position Y"""
        with self._focal_position:
            self._focal_position.y = float(value)

    @property
    def focal_position(self) -> _point.Point:
        """Get the focal position (what the camera is looking at)"""
        return self._focal_position

    @property
    def distance(self) -> float:
        """Get camera distance from focal plane"""
        return self._distance

    @distance.setter
    def distance(self, value: float):
        """Set camera distance (clamped to min/max)"""
        self._distance = max(self._min_distance, min(self._max_distance, float(value)))
        self.canvas.Refresh()

    def Zoom(self, delta: float):
        """
        Zoom in/out by changing the distance between camera and focal plane.

        Similar to 3D camera Zoom method. Positive delta zooms in (decreases distance),
        negative delta zooms out (increases distance).

        Args:
            delta: Signed value where positive = zoom in, negative = zoom out
        """
        # Apply delta to distance (positive delta = zoom in = decrease distance)
        # Use sensitivity to control how much distance changes per delta unit

        # Calculate new distance (negative delta to zoom in, like 3D camera)
        new_distance = self._distance - delta

        # Clamp to limits
        self._distance = max(self._min_distance, min(self._max_distance, new_distance))
        self.canvas.Refresh(False)

    def Pan(self, dx: float, dy: float):
        """
        Pan the camera by delta in screen pixels

        Moves the focal position in world coordinates.
        """
        # Calculate world units per pixel based on distance and screen size
        # For orthographic projection, visible width at focal plane depends on distance
        world_per_pixel = self._distance / 1000.0  # Scale factor

        world_delta = _point.Point(-dx * world_per_pixel, dy * world_per_pixel)

        self._focal_position += world_delta

    def zoom_at_point(self, screen_pos: _point.Point, delta: float):
        """
        Zoom in/out centered on a specific screen point.

        Changes the distance while keeping the point under cursor fixed.
        Similar to 3D camera but for 2D orthographic view.
        """
        # Get world position before zoom
        world_pos_before = self.screen_to_world(screen_pos)

        # Apply zoom using the Zoom method logic
        sensitivity = self.canvas.config.zoom.sensitivity
        new_distance = self._distance - (delta * sensitivity)
        self._distance = max(self._min_distance, min(self._max_distance, new_distance))

        # Get world position after zoom
        world_pos_after = self.screen_to_world(screen_pos)

        # Adjust focal position to keep the point under cursor fixed

        delta = world_pos_before - world_pos_after
        self._focal_position += delta

    def screen_to_world(self, screen_pos: _point.Point) -> _point.Point:
        """
        Convert screen coordinates to world coordinates
        """
        size = self.canvas.size

        if size is None:
            return _point.Point(0.0, 0.0)

        width, height = size

        # Screen center
        center_x = width / 2.0
        center_y = height / 2.0

        # Offset from center in pixels
        offset_x = screen_pos.x - center_x
        offset_y = center_y - screen_pos.y  # Invert Y (screen Y goes down, world Y goes up)

        # Convert to world units based on distance
        world_per_pixel = self._distance / 1000.0

        # World coordinates
        world_x = self._focal_position.x + (offset_x * world_per_pixel)
        world_y = self._focal_position.y + (offset_y * world_per_pixel)

        return _point.Point(world_x, world_y)

    def world_to_screen(self, world_pos: _point.Point) -> _point.Point:
        """
        Convert world coordinates to screen coordinates
        """
        size = self.canvas.size

        if size is None:
            return _point.Point(0, 0)

        width, height = size

        offset = world_pos - self._focal_position

        # Convert to pixels based on distance
        pixels_per_world = 1000.0 / self._distance

        # Screen coordinates
        screen_x = (width / 2.0) + (offset.x * pixels_per_world)
        screen_y = (height / 2.0) - (offset.y * pixels_per_world)  # Invert Y

        return _point.Point(int(screen_x), int(screen_y))

    def Reset(self, *_, **__):
        """Reset camera to origin with default distance"""
        with self._focal_position:
            self._focal_position.x = 0.0
            self._focal_position.y = 0.0

        self._distance = 1000.0
        self.canvas.Refresh()

    def zoom_to_fit(self, objects):
        """
        Zoom camera to fit all objects in view

        Args:
            objects: List of objects with get_bounds() method
        """
        if not objects:
            self.Reset()
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
            self.Reset()
            return

        # Calculate center and required distance
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        width_obj = max_x - min_x
        height_obj = max_y - min_y

        size = self.canvas.size
        if size:
            canvas_width, canvas_height = size

            # Calculate required distance to fit objects
            # Distance needed for width
            distance_for_width = (width_obj * 1000.0 / canvas_width) if width_obj > 0 else 1000.0
            # Distance needed for height
            distance_for_height = (height_obj * 1000.0 / canvas_height) if height_obj > 0 else 1000.0

            # Use the larger distance to fit both dimensions, then add padding
            required_distance = max(distance_for_width, distance_for_height) * 1.1  # 10% padding

            with self._focal_position:
                self._focal_position.x = center_x
                self._focal_position.y = center_y

            self._distance = max(self._min_distance, min(self._max_distance, required_distance))
            self.canvas.Refresh(False)
