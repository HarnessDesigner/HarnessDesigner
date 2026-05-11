# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from OpenGL import GL

from . import base2d as _base2d


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


class WireLayout(_base2d.Base2D):
    """
    2D representation of a wire layout (grab handle) for schematic view

    Renders as a circular grab handle using OpenGL.
    """
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):

        _base2d.Base2D.__init__(self, parent, db_obj)

        self._position = db_obj.position2d.point if hasattr(db_obj, 'position2d') else None

        # Wire layout visual properties
        self._radius = 5.0  # mm

        # Bind to position changes
        if self._position:
            self._position.bind(self._on_position_changed)

    def _on_position_changed(self, *args):
        """Called when wire layout position changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.update()

    def render_gl(self):
        """Render wire layout using OpenGL"""
        if self._position is None:
            return

        x = self._position.x
        y = self._position.y

        # Draw handle as circle with crosshairs
        GL.glColor4f(0.2, 0.6, 0.9, 0.6)  # Blue, semi-transparent
        self._draw_circle(x, y, self._radius, filled=True)

        # Draw outline
        GL.glColor4f(0.1, 0.4, 0.7, 1.0)  # Darker blue
        GL.glLineWidth(2.0)
        self._draw_circle(x, y, self._radius, filled=False)

        # Draw crosshairs
        GL.glColor4f(1.0, 1.0, 1.0, 0.8)  # White
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINES)
        # Horizontal line
        GL.glVertex2f(x - self._radius * 0.6, y)
        GL.glVertex2f(x + self._radius * 0.6, y)
        # Vertical line
        GL.glVertex2f(x, y - self._radius * 0.6)
        GL.glVertex2f(x, y + self._radius * 0.6)
        GL.glEnd()

    def render_selection(self):
        """Render selection highlight"""
        if self._position is None:
            return

        x = self._position.x
        y = self._position.y

        # Draw selection ring
        GL.glColor4f(1.0, 1.0, 0.0, 0.8)  # Yellow
        GL.glLineWidth(3.0)
        self._draw_circle(x, y, self._radius + 2.0, filled=False)

    def _draw_circle(self, x, y, radius, filled=True, segments=20):
        """Draw a circle using OpenGL"""
        import math

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
        """Test if point is inside wire layout handle"""
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
        """Move wire layout to new position"""
        if self._position is None:
            return

        with self._position:
            self._position.x = world_x
            self._position.y = world_y


class WireLayoutMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

    def on_add_splice(self):
        pass

    def on_trace_circuit(self):
        pass

    def on_select(self):
        pass

    def on_delete(self):
        pass
