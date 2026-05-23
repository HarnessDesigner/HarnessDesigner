# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
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
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

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
            self.editor2d.editor.canvas.update()

    def _on_angle_changed(self, *args):
        """Called when terminal angle changes"""
        if self.editor2d and hasattr(self.editor2d, 'editor') and hasattr(self.editor2d.editor, 'canvas'):
            self.editor2d.editor.canvas.update()

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

        # Draw selection ring (rotation does not affect circular selection)
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

        For circular terminals, rotation does not affect hit testing
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


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects2d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`TerminalMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_add_wire(self):
        """Handle the add wire event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_wire_service_loop(self):
        """Handle the add wire service loop event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
