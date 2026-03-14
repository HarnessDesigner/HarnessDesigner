from typing import TYPE_CHECKING

import wx
from OpenGL import GL
import math

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire as _pjt_wire
    from .. import wire as _wire


FIVE_0 = 5.0
SIX_0 = 6.0

# Color mapping for wire colors and stripe colors
WIRE_COLOR_MAP = {
    'black': (0.0, 0.0, 0.0),
    'red': (1.0, 0.0, 0.0),
    'blue': (0.0, 0.0, 1.0),
    'green': (0.0, 1.0, 0.0),
    'yellow': (1.0, 1.0, 0.0),
    'white': (1.0, 1.0, 1.0),
    'orange': (1.0, 0.5, 0.0),
    'brown': (0.6, 0.3, 0.0),
    'purple': (0.5, 0.0, 0.5),
    'gray': (0.5, 0.5, 0.5),
    'grey': (0.5, 0.5, 0.5),
    'pink': (1.0, 0.75, 0.8),
}


class Wire(_base2d.Base2D):
    """
    2D representation of a wire for schematic view
    
    Renders as a colored line between two points using OpenGL.
    
    Wire Connection Rules:
    - Wire endpoints can ONLY attach to: Terminals, Splices, or WireLayouts (handles)
    - WireLayouts (handles) can be added along the wire for positioning
    - Wire visual width scales with wire gauge/size
    - Diagonal stripes are rendered if stripe color is available
    """
    _parent: "_wire.Wire" = None
    db_obj: "_pjt_wire.PJTWire"

    def __init__(self, parent: "_wire.Wire", db_obj: "_pjt_wire.PJTWire"):
        _base2d.Base2D.__init__(self, parent, db_obj)

        self._part = db_obj.part
        self._p1 = db_obj.start_point2d.point
        self._p2 = db_obj.stop_point2d.point
        
        # Bind to point changes to trigger re-render
        self._p1.bind(self._on_point_changed)
        self._p2.bind(self._on_point_changed)
        
        # Wire visual properties
        self._line_width = 3.0
        self._hit_tolerance = 5.0  # pixels for hit testing
        
    def _on_point_changed(self, *args):
        """Called when wire endpoints change"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.Refresh()
            
    def render_gl(self):
        """Render wire using OpenGL"""
        if self._p1 is None or self._p2 is None:
            return
            
        # Get wire properties
        color = self._get_wire_color()
        stripe_color = self._get_wire_stripe_color()
        line_width = self._get_wire_width()
        
        # Draw wire line
        GL.glLineWidth(line_width)
        GL.glColor4f(color[0], color[1], color[2], 1.0)
        
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(self._p1.x, self._p1.y)
        GL.glVertex2f(self._p2.x, self._p2.y)
        GL.glEnd()
        
        # Draw diagonal stripes if stripe color is available
        if stripe_color is not None:
            self._render_stripes(stripe_color, line_width)
            
    def _render_stripes(self, stripe_color, wire_width):
        """Render diagonal stripes on wire"""
        # Calculate wire angle and length
        dx = self._p2.x - self._p1.x
        dy = self._p2.y - self._p1.y
        wire_length = math.sqrt(dx*dx + dy*dy)
        
        if wire_length < 0.1:
            return
            
        wire_angle = math.atan2(dy, dx)
        
        # Stripe properties
        stripe_interval = 40.0  # mm between stripes
        stripe_angle = math.radians(45.0)  # 45 degrees from wire direction
        stripe_length = max(wire_width, 1.0)
        
        # Draw stripes along the wire
        GL.glColor4f(stripe_color[0], stripe_color[1], stripe_color[2], 1.0)
        GL.glLineWidth(max(wire_width / 3.0, 2.0))
        
        GL.glBegin(GL.GL_LINES)
        
        current_dist = 0.0
        while current_dist < wire_length - stripe_interval:
            current_dist += stripe_interval
            
            # Calculate position along wire
            t = current_dist / wire_length
            px = self._p1.x + t * dx
            py = self._p1.y + t * dy
            
            # Calculate stripe endpoints perpendicular to wire
            angle1 = wire_angle + stripe_angle
            angle2 = wire_angle - stripe_angle
            
            # First stripe line
            sx1 = px + stripe_length * math.cos(angle1)
            sy1 = py + stripe_length * math.sin(angle1)
            ex1 = px - stripe_length * math.cos(angle1)
            ey1 = py - stripe_length * math.sin(angle1)
            
            GL.glVertex2f(sx1, sy1)
            GL.glVertex2f(ex1, ey1)
            
        GL.glEnd()
        
    def _get_wire_width(self):
        """Get wire width based on wire gauge"""
        # Try to get wire gauge/size from part
        if self._part and hasattr(self._part, 'gauge'):
            # Map AWG gauge to visual width (smaller gauge = thicker wire)
            # AWG 10 = ~5mm, AWG 20 = ~2mm, AWG 30 = ~1mm
            gauge = float(self._part.gauge)
            # Approximate formula: diameter ≈ 0.127 * 92^((36-AWG)/39)
            # Simplified for visualization
            width = max(1.0, 10.0 - (gauge / 4.0))
            return width
        elif self._part and hasattr(self._part, 'outer_diameter'):
            # Use outer diameter if available
            return float(self._part.outer_diameter)
            
        # Default width
        return 3.0
        
    def render_selection(self):
        """Render selection highlight"""
        if self._p1 is None or self._p2 is None:
            return
            
        line_width = self._get_wire_width()
        
        # Draw thicker line in highlight color
        GL.glLineWidth(line_width + 4.0)
        GL.glColor4f(1.0, 1.0, 0.0, 0.5)  # Yellow with transparency
        
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(self._p1.x, self._p1.y)
        GL.glVertex2f(self._p2.x, self._p2.y)
        GL.glEnd()
        
        # Draw endpoint handles
        self._draw_endpoint_handle(self._p1.x, self._p1.y)
        self._draw_endpoint_handle(self._p2.x, self._p2.y)
        
    def _draw_endpoint_handle(self, x, y):
        """Draw a handle at an endpoint"""
        size = 4.0
        
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(x - size, y - size)
        GL.glVertex2f(x + size, y - size)
        GL.glVertex2f(x + size, y + size)
        GL.glVertex2f(x - size, y + size)
        GL.glEnd()
        
    def hit_test(self, world_x: float, world_y: float) -> bool:
        """Test if point is near the wire line"""
        if self._p1 is None or self._p2 is None:
            return False
            
        # Calculate distance from point to line segment
        distance = self._point_to_line_distance(
            world_x, world_y,
            self._p1.x, self._p1.y,
            self._p2.x, self._p2.y
        )
        
        # Get canvas to convert tolerance to world units
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            canvas = self.editor2d.editor.canvas
            tolerance_world = self._hit_tolerance / canvas.zoom
        else:
            tolerance_world = self._hit_tolerance
            
        return distance <= tolerance_world
        
    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate minimum distance from point to line segment"""
        # Vector from start to end
        dx = x2 - x1
        dy = y2 - y1
        
        # If line is actually a point
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
            
        # Parameter t for projection onto line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))
        
        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance to closest point
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
        
    def get_bounds(self):
        """Get bounding box"""
        if self._p1 is None or self._p2 is None:
            return None
            
        min_x = min(self._p1.x, self._p2.x)
        max_x = max(self._p1.x, self._p2.x)
        min_y = min(self._p1.y, self._p2.y)
        max_y = max(self._p1.y, self._p2.y)
        
        return (min_x, min_y, max_x, max_y)
        
    def move_to(self, world_x: float, world_y: float):
        """
        Move wire to new position
        
        Moves the wire's start point (p1) to the target position and maintains
        the wire's length and direction by moving the end point (p2) by the same offset.
        
        Args:
            world_x: New world X coordinate for p1
            world_y: New world Y coordinate for p1
        """
        # Calculate offset before modifying p1
        if self._p1 is None or self._p2 is None:
            return
            
        dx = world_x - self._p1.x
        dy = world_y - self._p1.y
        
        # Move both points by the same offset to maintain wire geometry
        with self._p1:
            self._p1.x = world_x
            self._p1.y = world_y
            
        with self._p2:
            self._p2.x += dx
            self._p2.y += dy
            
    def _get_wire_color(self):
        """Get wire color from part or default"""
        # Try to get color from part
        if self._part and hasattr(self._part, 'color'):
            color_name = self._part.color
            # Map color name to RGB using shared color map
            if color_name and color_name.lower() in WIRE_COLOR_MAP:
                return WIRE_COLOR_MAP[color_name.lower()]
                
        # Default color
        return (0.8, 0.8, 0.8)  # Light gray
        
    def _get_wire_stripe_color(self):
        """Get wire stripe color from part or None"""
        # Try to get stripe color from part
        if self._part and hasattr(self._part, 'stripe_color'):
            stripe_color_obj = self._part.stripe_color
            if stripe_color_obj is not None:
                if hasattr(stripe_color_obj, 'name'):
                    color_name = stripe_color_obj.name
                elif isinstance(stripe_color_obj, str):
                    color_name = stripe_color_obj
                else:
                    return None
                    
                # Map color name to RGB using shared color map
                if color_name and color_name.lower() in WIRE_COLOR_MAP:
                    return WIRE_COLOR_MAP[color_name.lower()]
                    
        return None
    #
    # def draw_selected(self, gc, selected):
    #     x1 = selected.p1.x
    #     y1 = selected.p1.y
    #     x2 = selected.p2.x
    #     y2 = selected.p2.y
    #
    #     path = gc.CreatePath()
    #     path.MoveToPoint(float(x1), float(y1))
    #     path.AddLineToPoint(float(x2), float(y2))
    #     path.CloseSubpath()
    #     gc.StrokePath(path)
    #
    # def draw(self, gc, mask_gc):
    #     p1 = self._p1
    #     p2 = self._p2
    #
    #     pixel_width = self._wire_info.pixel_width
    #     color = self._part.color.ui
    #
    #     pen1 = wx.Pen(color, pixel_width)
    #     pen1.SetJoin(wx.JOIN_MITER)
    #
    #     mask_pen = wx.Pen(wx.BLACK, pixel_width)
    #     mask_pen.SetJoin(wx.JOIN_MITER)
    #
    #     stripe_color = self._part.stripe_color
    #
    #     if stripe_color is not None:
    #         stripe_pen = wx.Pen(stripe_color.ui,
    #                             max(int(self._wire_info.pixel_width / 3.0), 2))
    #     else:
    #         stripe_pen = None
    #
    #     handle_pen = wx.Pen(wx.Colour(0, 0, 0, 255), 3.0)
    #
    #     path = gc.CreatePath()
    #     mask_path = mask_gc.CreatePath()
    #
    #     is_selected = self.is_selected
    #     mask_gc.SetPen(wx.TRANSPARENT_PEN)
    #
    #     mask_path.MoveToPoint(float(p1.x), float(p1.y))
    #     mask_path.AddLineToPoint(float(p2.x), float(p2.y))
    #
    #     path.MoveToPoint(float(p1.x), float(p1.y))
    #     path.AddLineToPoint(float(p2.x), float(p2.y))
    #
    #     if is_selected:
    #         for obj in p1.objects:
    #             if obj != self and isinstance(obj, Wire):
    #                 mask_path.drawEllipse(float(p1.x - SIX_0),
    #                                       float(p1.y - SIX_0),
    #                                       12.0, 12.0)
    #                 break
    #
    #         for obj in p2.objects:
    #             if obj != self and isinstance(obj, Wire):
    #                 mask_path.DrawEllipse(float(p2.x - SIX_0),
    #                                       float(p2.y - SIX_0),
    #                                       12.0, 12.0)
    #                 break
    #
    #     mask_path.CloseSubpath()
    #     mask_gc.SetPen(mask_pen)
    #     mask_gc.StrokePath(path)
    #
    #     gc.SetPen(pen1)
    #     path.CloseSubpath()
    #     gc.StrokePath(path)
    #
    #     gc.SetPen(wx.TRANSPARENT_PEN)
    #
    #     if stripe_color is not None:
    #         path = gc.CreatePath()
    #         for start, stop in self.stripe_lines():
    #             path.MoveToPoint(*start)
    #             path.AddLineToPoint(*stop)
    #
    #         path.CloseSubpath()
    #
    #         gc.SetPen(stripe_pen)
    #         gc.StrokePath(path)
    #
    #     path = gc.CreatePath()
    #
    #     if is_selected:
    #         for obj in self._p1.objects:
    #             if obj != self and isinstance(obj, Wire):
    #                 path.DrawEllipse(float(self._p1.x - SIX_0),
    #                                  float(self._p1.y - SIX_0),
    #                                  12.0, 12.0)
    #                 break
    #
    #         for obj in self._p2.objects:
    #             if obj != self and isinstance(obj, Wire):
    #                 path.DrawEllipse(float(self._p2.x - SIX_0),
    #                                  float(self._p2.y - SIX_0),
    #                                  12.0, 12.0)
    #                 break
    #
    #     path.CloseSubpath()
    #
    #     gc.SetPen(handle_pen)
    #     gc.StrokePath(path)
    #
    # def hit_test(self, p: _point.Point) -> bool:
    #     if self._hit_test_rect is None:
    #         return False
    #     p1, p2 = self._hit_test_rect
    #
    #     if not Config.lock_90:
    #         p1 = p1.copy()
    #         p2 = p2.copy()
    #         p = p.copy()
    #
    #         angle = _angle.Angle.from_points(p1, p2)
    #         angle.z = -angle.z
    #         p2 -= p1
    #         p2 @= angle
    #         p -= p1
    #         p @= angle
    #
    #     return p1 <= p <= p2

#
# class WireSection:
#
#     def __init__(self, parent, p1: _point.Point, p2: _point.Point):
#         self.parent: "Wire" = parent
#         self.p1 = p1
#         self.p2 = p2
#
#     def update_wire_info(self) -> None:
#         self.parent.update_wire_info()
#
#     def is_p1_end_grabbed(self, p: _point.Point) -> bool:
#         x, y = self.p1
#         x1 = x - FIVE_0
#         x2 = x + FIVE_0
#         y1 = y - FIVE_0
#         y2 = y + FIVE_0
#         x, y = p.x, p.y
#         return x1 <= x <= x2 and y1 <= y <= y2
#
#     def is_p2_end_grabbed(self, p: _point.Point) -> bool:
#         x, y = self.p2.x, self.p2.y
#         x1 = x - FIVE_0
#         x2 = x + FIVE_0
#         y1 = y - FIVE_0
#         y2 = y + FIVE_0
#         x, y = p.x, p.y
#         return x1 <= x <= x2 and y1 <= y <= y2
#
#     def __contains__(self, other: _point.Point) -> bool:
#         line1 = _line.Line(self.p1, self.p2)
#         half_size = _d(self.parent.wire_info.pixel_width) / _d(2.0) + _d(1)
#
#         line2 = line1.get_parallel_line(half_size)
#         line3 = line1.get_parallel_line(-half_size)
#
#         x1, y1, x2, y2 = line2.p1.x, line2.p1.y, line3.p2.x, line3.p2.y
#
#         x1, x2 = min(x1, x2), max(x1, x2)
#         y1, y2 = min(y1, y2), max(y1, y2)
#
#         return x1 <= other.x <= x2 and y1 <= other.y <= y2
#
#     def stripe_lines(self) -> list[list[tuple[float, float], tuple[float, float]]]:
#         line = _line.Line(self.p1, self.p2)
#         line_angle = _angle.Angle.from_points(self.p1, self.p2)
#
#         stripe_angle1 = _angle.Angle.from_points(_point.Point(68, 0), _point.Point(68 - 32, 24))
#         stripe_angle1 += line_angle
#
#         stripe_angle2 = stripe_angle1.copy()
#         stripe_angle2.z += _d(180.0)
#
#         line_len = len(line)
#         step = 40
#
#         wire_size = self.parent.wire_info.pixel_width
#
#         curr_dist = 0
#         points = []
#
#         while curr_dist < line_len - step:
#             curr_dist += step
#
#             p = line.point_from_start(curr_dist)
#             s1 = _line.Line(p, None, angle=stripe_angle1, length=max(wire_size, 1))
#             s2 = _line.Line(p, None, angle=stripe_angle2, length=max(wire_size, 1))
#
#             points.append([s1.p2.as_float[:-1], s2.p2.as_float[:-1]])
#
#         return points
#
#     def aslist(self) -> list[_d, _d, _d, _d]:
#         return list(self.p1) + list(self.p2)
#
#     def length(self) -> _d:
#         return _line.Line(self.p1, self.p2).length()
#
#     def get_angle(self) -> _angle.Angle:
#         return _angle.Angle.from_points(self.p1, self.p2)
#
#     @staticmethod
#     def _rotate_point(origin: _point.Point, point: _point.Point, angle: _angle.Angle):
#         ox, oy = origin.x, origin.y
#         px, py = point.x, point.y
#
#         z_angle = angle.z
#
#         cos = _d(math.cos(z_angle))
#         sin = _d(math.sin(z_angle))
#
#         x = px - ox
#         y = py - oy
#
#         qx = ox + (cos * x) - (sin * y)
#         qy = oy + (sin * x) + (cos * y)
#         return _point.Point(qx, qy)
#
#     def move_p2(self, p: _point.Point):
#         angle = _angle.Angle.from_points(self.p1, p)
#         z_angle = angle.z
#
#         if z_angle > 315:
#             offset = 360
#         elif z_angle > 225:
#             offset = 270
#         elif z_angle > 135:
#             offset = 180
#         elif z_angle > 45:
#             offset = 90
#         else:
#             offset = 0
#
#         angle.z = _d(offset) - z_angle
#         self.p2 -= p
#         self.p2 @= angle
#         self.p2 += p
#
#     def move(self, p):
#         p1 = self.p1.copy()
#         p2 = self.p2.copy()
#
#         p1 += p
#         p2 += p
#
#         p3 = None
#         p4 = None
#
#         for section in self.parent._sections:  # NOQA
#             if section == self:
#                 continue
#
#             if section.p2 == self.p1:
#                 p3 = section.p1
#
#             if section.p1 == self.p2:
#                 p4 = section.p2
#
#         if p3 is not None:
#             angle = _angle.Angle.from_points(p3, p1)
#             z_angle = angle.z
#
#             if z_angle > 315:
#                 offset = 360
#             elif z_angle > 225:
#                 offset = 270
#             elif z_angle > 135:
#                 offset = 180
#             elif z_angle > 45:
#                 offset = 90
#             else:
#                 offset = 0
#
#             angle.z = _d(offset) - z_angle
#             p1 -= p3
#             p1 @= angle
#             p1 += p3
#
#         if p4 is not None:
#             angle = _angle.Angle.from_points(p4, p2)
#             z_angle = angle.z
#
#             if z_angle > 315:
#                 offset = 360
#             elif z_angle > 225:
#                 offset = 270
#             elif z_angle > 135:
#                 offset = 180
#             elif z_angle > 45:
#                 offset = 90
#             else:
#                 offset = 0
#
#             angle.z = _d(offset) - z_angle
#             p2 -= p4
#             p2 @= angle
#             p2 += p4
#
#         angle = _angle.Angle.from_points(p1, p2).z
#
#         if angle in (0, 90, 180, 270, 360):
#             self.p1.x = p1.x
#             self.p1.y = p1.y
#             self.p2.x = p2.x
#             self.p2.y = p2.y
#         else:
#             print(angle)
#
#
# class Wire:
#
#     def __init__(self, parent, db_obj):
#         self.parent = parent
#         self.wire_info = _wire_info.WireInfo(db_obj)
#         self._sections: list[WireSection] = []
#         self._is_selected = False
#
#     def new_section(self, p):
#         if self._sections:
#             section = self._sections[-1]
#             new_section = WireSection(self, section.p2, p)
#         else:
#             new_section = WireSection(self, p.copy(), p)
#
#         self._sections.append(new_section)
#         return new_section
#
#     def remove_last_section(self):
#         self._sections.pop(-1)
#
#     def draw_selected(self, gc, selected):
#         x1 = selected.p1.x
#         y1 = selected.p1.y
#         x2 = selected.p2.x
#         y2 = selected.p2.y
#
#         path = gc.CreatePath()
#         path.MoveToPoint(float(x1), float(y1))
#         path.AddLineToPoint(float(x2), float(y2))
#         path.CloseSubpath()
#         gc.StrokePath(path)
#
#     def draw(self, gc, mask_gc, selected):
#         pen1 = wx.Pen(self.wire_info.color, self.wire_info.pixel_width)
#         pen1.SetJoin(wx.JOIN_MITER)
#
#         mask_pen = wx.Pen(wx.BLACK, self.wire_info.pixel_width)
#         mask_pen.SetJoin(wx.JOIN_MITER)
#
#         pen2 = wx.Pen(self.wire_info.stripe_color, max(int(self.wire_info.pixel_width / 3.0), 2))
#
#         path = gc.CreatePath()
#         mask_path = mask_gc.CreatePath()
#
#         is_selected = self.is_selected()
#         mask_gc.SetPen(wx.TRANSPARENT_PEN)
#
#         for i, section in enumerate(self._sections):
#             if section == selected:
#                 continue
#
#             mask_path.MoveToPoint(float(section.p1.x), float(section.p1.y))
#             mask_path.AddLineToPoint(float(section.p2.x), float(section.p2.y))
#
#             path.MoveToPoint(float(section.p1.x), float(section.p1.y))
#             path.AddLineToPoint(float(section.p2.x), float(section.p2.y))
#
#             if is_selected:
#
#                 if i == 0:
#                     mask_gc.DrawEllipse(float(section.p1.x - SIX_0),
#                                         float(section.p1.y - SIX_0),
#                                         12.0, 12.0)
#
#                 mask_gc.DrawEllipse(float(section.p2.x - SIX_0),
#                                     float(section.p2.y - SIX_0),
#                                     12.0, 12.0)
#
#         mask_path.CloseSubpath()
#         mask_gc.SetPen(mask_pen)
#         mask_gc.StrokePath(path)
#
#         gc.SetPen(pen1)
#         path.CloseSubpath()
#         gc.StrokePath(path)
#
#         path = gc.CreatePath()
#
#         gc.SetPen(wx.TRANSPARENT_PEN)
#
#         for i, section in enumerate(self._sections):
#             if section == selected:
#                 continue
#
#             for start, stop in section.stripe_lines():
#                 path.MoveToPoint(*start)
#                 path.AddLineToPoint(*stop)
#
#             if is_selected:
#                 if i == 0:
#                     gc.DrawEllipse(float(section.p1.x - SIX_0),
#                                    float(section.p1.y - SIX_0),
#                                    12.0, 12.0)
#
#                 gc.DrawEllipse(float(section.p2.x - SIX_0),
#                                float(section.p2.y - SIX_0),
#                                12.0, 12.0)
#
#         path.CloseSubpath()
#         gc.SetPen(pen2)
#         gc.StrokePath(path)
#
#     def is_selected(self, flag=None):
#         if flag is None:
#             return self._is_selected
#
#         self._is_selected = flag
#
#     def update_wire_info(self):
#         self.parent.wire_info_ctrl.update_wire_length()
#
#     def get_section(self, p):
#         for section in self._sections:
#             if p in section:
#                 return section
#
#     def __len__(self):
#         return len(self._sections)

class WireMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Handle')
        canvas.Bind(wx.EVT_MENU, self.on_add_handle, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Marker')
        canvas.Bind(wx.EVT_MENU, self.on_add_marker, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Splice')
        canvas.Bind(wx.EVT_MENU, self.on_add_splice, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire Service Loop')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire_service_loop, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Add to Bundle')
        canvas.Bind(wx.EVT_MENU, self.on_add_to_bundle, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_add_handle(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_marker(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_splice(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire_service_loop(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_to_bundle(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()