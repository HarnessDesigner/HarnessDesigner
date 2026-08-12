# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
2D Camera for Schematic Editor

Manages camera position, zoom, and viewport transformations for 2D orthographic view.
Uses distance-based zoom similar to 3D camera, where zoom changes the distance between
the camera and the focal plane.
"""

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import canvas as _canvas


# Fixed camera basis for the locked straight-down 2D view -- same values
# gl.canvas3d.camera._LOCKED_FORWARD/_LOCKED_RIGHT/_LOCKED_UP use for the
# 3D editor's own locked top-down mode, reused here since Camera2D is
# *always* that same bird's-eye pose (world X -> screen X, world Z ->
# screen Y).
_FORWARD = np.array([0.0, -1.0, 0.0], dtype=np.float32)
_RIGHT = np.array([1.0, 0.0, 0.0], dtype=np.float32)
_UP = np.array([0.0, 0.0, 1.0], dtype=np.float32)


class Camera:
    """
    2D Camera for orthographic schematic view

    Similar to 3D camera but adapted for 2D orthographic projection:
    - Focal position: center point in world coordinates (what we're looking at)
    - Distance: camera distance from focal plane (controls zoom)
    - Pan: moves focal position
    - Zoom: changes distance (closer = more zoomed in, farther = more zoomed out)
    """

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):
        """Initialise the :class:`Camera2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas2D`
        """
        self.canvas = canvas
        self._context = canvas.context

        # Focal position - the point in world coordinates we're looking at (center of view)
        self._focal_position = _point.Point(0.0, 0.0, 0.0)

        # Distance from camera to focal plane (controls zoom level)
        # Higher distance = see more (zoomed out), lower distance = see less (zoomed in)
        self._distance = 1000.0  # Default distance in "units"

        # Distance limits (controls zoom range)
        self._min_distance = 10.0    # Max zoom in
        self._max_distance = 100000.0  # Max zoom out

        # gl.canvas3d.camera.Camera's .modelview/.projection/.viewport
        # contract, reused unchanged by gl.object_picker's ray-vs-
        # OBB/AABB picking math -- see _update_views(). Always the same
        # locked straight-down basis (_FORWARD/_RIGHT/_UP above), so unlike
        # Camera3D there's no _calculate_camera() step.
        self._is_dirty = True
        self._projection = None
        self._modelview = None
        self._viewport = None

        # Bind callbacks for automatic refresh
        self._focal_position.bind(self._on_focal_position_changed)

    @_check_types.do
    def _on_focal_position_changed(self, _: _point.Point):
        """Called when focal position changes"""
        self._is_dirty = True
        self.canvas.Refresh(False)

    @_check_types.do
    def _update_views(self):
        """(Re)read ``.projection``/``.modelview``/``.viewport`` from live
        GL state -- mirrors ``gl.canvas3d.camera.Camera._update_views()``
        exactly (same ``GL_PROJECTION_MATRIX``/``GL_MODELVIEW_MATRIX``/
        ``GL_VIEWPORT`` readback, same row-major reshape), so
        ``gl.object_picker.find_object`` works against this
        camera unchanged. Requires a current GL context; the legacy
        ``Canvas._setup_projection()`` path (``glOrtho``/``glMatrixMode``)
        must have already run this frame for these to reflect the current
        view -- called from ``Canvas.paintGL()`` right after that, not
        lazily, since (unlike Camera3D) nothing here triggers GL calls of
        its own to make the state current first.
        """
        if not self._is_dirty:
            return

        with self._context:
            self._is_dirty = False
            self._viewport = np.ascontiguousarray(GL.glGetIntegerv(GL.GL_VIEWPORT))

            self._projection = np.ascontiguousarray(np.array(
                GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)).reshape((4, 4), order="F").T)

            self._modelview = np.ascontiguousarray(np.array(
                GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)).reshape((4, 4), order="F").T)

    @property
    @_check_types.do
    def projection(self) -> np.ndarray | None:
        return self._projection

    @property
    @_check_types.do
    def modelview(self) -> np.ndarray | None:
        return self._modelview

    @property
    @_check_types.do
    def viewport(self) -> np.ndarray | None:
        return self._viewport

    @property
    @_check_types.do
    def forward(self) -> np.ndarray:
        """Unit vector the camera looks along -- always straight down."""
        return _FORWARD

    @property
    @_check_types.do
    def up(self) -> np.ndarray:
        return _UP

    @property
    @_check_types.do
    def right(self) -> np.ndarray:
        return _RIGHT

    @property
    @_check_types.do
    def position(self) -> _point.Point:
        """Camera "eye" position -- straight above :attr:`focal_position`
        by :attr:`distance`, matching the world-per-pixel convention every
        other method here already uses (mirrors
        ``gl.canvas3d.camera.Camera.position``'s role for
        ``object_picker``'s ray origin/``get_position_on_focal_plane``-
        style math, should it be needed).
        """
        return _point.Point(
            self._focal_position.x,
            self._distance,
            self._focal_position.z)

    @property
    @_check_types.do
    def x(self) -> float:
        """Get focal position X in world coordinates"""
        return float(str(self._focal_position.x))

    @x.setter
    @_check_types.do
    def x(self, value: float):
        """Set focal position X"""
        with self._focal_position:
            self._focal_position.x = float(value)

    @property
    @_check_types.do
    def y(self) -> float:
        """Get focal position Y (schematic-plane vertical, i.e. world Z --
        see the module-level ``world Z -> screen Y`` note) in world
        coordinates."""
        return float(str(self._focal_position.z))

    @y.setter
    @_check_types.do
    def y(self, value: float):
        """Set focal position Y (world Z -- see :meth:`y` getter)."""
        with self._focal_position:
            self._focal_position.z = float(value)

    @property
    @_check_types.do
    def focal_position(self) -> _point.Point:
        """Get the focal position (what the camera is looking at)"""
        return self._focal_position

    @property
    @_check_types.do
    def distance(self) -> float:
        """Get camera distance from focal plane"""
        return self._distance

    @distance.setter
    @_check_types.do
    def distance(self, value: float):
        """Set camera distance (clamped to min/max)"""
        self._distance = max(self._min_distance, min(self._max_distance, float(value)))
        self._is_dirty = True
        self.canvas.Refresh()

    @_check_types.do
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
        self._is_dirty = True
        self.canvas.Refresh(False)

    @_check_types.do
    def Pan(self, dx: float, dy: float):
        """
        Pan the camera by delta in screen pixels

        Moves the focal position in world coordinates.
        """
        # Calculate world units per pixel based on distance and screen size
        # For orthographic projection, visible width at focal plane depends on distance
        world_per_pixel = self._distance / 1000.0  # Scale factor

        world_delta = _point.Point(-dx * world_per_pixel, 0.0, dy * world_per_pixel)

        self._focal_position += world_delta

    @_check_types.do
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
        self._is_dirty = True

        # Get world position after zoom
        world_pos_after = self.screen_to_world(screen_pos)

        # Adjust focal position to keep the point under cursor fixed.
        # NOTE: intentionally NOT reusing the `delta` name here -- `delta` is
        # annotated `float` on the function signature, and Cython statically
        # types it as a C double from that annotation; reassigning it to a
        # Point (as this used to do) compiles fine under plain Python
        # (dynamic typing) but raises "must be real number, not Point" once
        # compiled, because Cython tries to coerce the Point into the
        # double-typed slot. Keep numeric and Point-typed values in
        # separate variables to avoid this class of bug.
        focal_delta = world_pos_before - world_pos_after
        self._focal_position += focal_delta

    @_check_types.do
    def screen_to_world(self, screen_pos: _point.Point) -> _point.Point:
        """
        Convert screen coordinates to world coordinates
        """
        size = self.canvas.size

        if size is None:
            return _point.Point(0.0, 0.0, 0.0)

        width, height = size

        # Screen center
        center_x = width / 2.0
        center_y = height / 2.0

        # Offset from center in pixels
        offset_x = screen_pos.x - center_x
        offset_y = center_y - screen_pos.y  # Invert Y (screen Y goes down, world Y goes up)

        # Convert to world units based on distance
        world_per_pixel = self._distance / 1000.0

        # World coordinates -- world_y lands in the returned Point's .z
        # (schematic-plane vertical axis, matching position2d/position_peg).
        world_x = self._focal_position.x + (offset_x * world_per_pixel)
        world_y = self._focal_position.z + (offset_y * world_per_pixel)

        return _point.Point(world_x, 0.0, world_y)

    @_check_types.do
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
        screen_y = (height / 2.0) - (offset.z * pixels_per_world)  # Invert Y

        return _point.Point(int(screen_x), int(screen_y))

    @property
    @_check_types.do
    def objects_in_view(self) -> list:
        """Objects (``ObjectBase`` wrappers) currently visible in the
        viewport rectangle.

        Backs ``ObjectBase.is_in_2dview``/``is_in_pegboardview`` (``self in
        editorX.camera.objects_in_view``) -- previously ``is_in_2dview``
        referenced this attribute before it existed, so any access raised
        ``AttributeError``. ``Camera2D`` is reused unchanged by both the 2D
        schematic canvas and the peg board canvas (deliberately not
        subclassed per Phase 1 of the peg board editor), and those two
        canvases hold their scene contents in different shapes -- real
        ``ObjectBase`` wrappers with ``objschematic.get_bounds()`` for the
        schematic canvas, ``objects.objects_pegboard.base_pegboard.BasePegboard``
        (``.obj``/``.position.x``/``.position.z``) for the peg board -- so this duck-types on
        which shape ``self.canvas``
        actually exposes rather than assuming one. Computed fresh on each
        access (no per-frame cache, unlike the 3D camera's
        GPU-culling-backed ``objects_in_view`` -- a 2D bounds/point test is
        cheap enough not to need one), using the exact same
        ``distance / 1000.0`` world-per-pixel convention as
        :meth:`screen_to_world`/:meth:`zoom_to_fit`.

        :returns: Objects currently visible in the viewport.
        :rtype: list
        """
        size = self.canvas.size
        if size is None:
            return []

        width, height = size
        world_per_pixel = self._distance / 1000.0
        half_width = (width / 2.0) * world_per_pixel
        half_height = (height / 2.0) * world_per_pixel

        left = self._focal_position.x - half_width
        right = self._focal_position.x + half_width
        bottom = self._focal_position.z - half_height
        top = self._focal_position.z + half_height

        result = []

        # 2D schematic canvas: real ObjectBase wrappers, bounds via objschematic.
        if hasattr(self.canvas, 'objects'):
            for obj in self.canvas.objects:
                if not hasattr(obj, 'objschematic') or not hasattr(obj.objschematic, 'get_bounds'):
                    continue

                bounds = obj.objschematic.get_bounds()
                if bounds is None:
                    continue

                min_x, min_y, max_x, max_y = bounds
                if max_x < left or min_x > right or max_y < bottom or min_y > top:
                    continue

                result.append(obj)

            return result

        # Peg board canvas: BasePegboard anchor point-containment (x/z world position).
        anchors = getattr(self.canvas, '_anchors', None)
        if anchors:
            for anchor in anchors:
                if left <= anchor.position.x <= right and bottom <= anchor.position.z <= top:
                    result.append(anchor.obj)

        return result

    @_check_types.do
    def Reset(self, *_, **__):
        """Reset camera to origin with default distance"""
        with self._focal_position:
            self._focal_position.x = 0.0
            self._focal_position.z = 0.0

        self._distance = 1000.0
        self._is_dirty = True
        self.canvas.Refresh()

    @_check_types.do
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
            if hasattr(obj, 'objschematic') and hasattr(obj.objschematic, 'get_bounds'):
                bounds = obj.objschematic.get_bounds()
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
                self._focal_position.z = center_y

            self._distance = max(self._min_distance, min(self._max_distance, required_distance))
            self._is_dirty = True
            self.canvas.Refresh(False)
