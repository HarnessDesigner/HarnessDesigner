# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
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
        """Initialise the :class:`Splice` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """

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
            self.editor2d.editor.canvas.update()

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


class SpliceMenu(QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects2d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`SpliceMenu` instance.

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
