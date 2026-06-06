# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from OpenGL import GL
import math
import numpy as np

from . import base2d as _base2d
from ...ui.widgets import context_menus as _context_menus
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...geometry.decimal import Decimal as _d


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing


class Housing(_base2d.Base2D):
    """
    2D representation of a housing for schematic view

    Renders as a rectangle with cavity positions using OpenGL.
    When moved, all child cavities move with it (hierarchical movement).
    Supports rotation using the Angle class.
    """
    _parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing"

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing.Housing`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        self._part = db_obj.part
        position = db_obj.position2d
        angle = db_obj.angle2d

        _base2d.Base2D.__init__(self, parent, db_obj, position, angle)

        # Get dimensions from part if available
        self._width = float(self._part.width)
        self._height = float(self._part.height)

        # Track child cavities for hierarchical movement
        self._cavities = []

    def add_cavity(self, cavity):
        """
        Add a cavity to this housing

        Args:
            cavity: Cavity object to add
        """
        if cavity not in self._cavities:
            self._cavities.append(cavity)
            if hasattr(cavity, 'obj2d'):
                cavity.obj2d._housing = self

    def remove_cavity(self, cavity):
        """
        Remove a cavity from this housing

        Args:
            cavity: Cavity object to remove
        """
        try:
            self._cavities.remove(cavity)
            if hasattr(cavity, 'obj2d'):
                cavity.obj2d._housing = None
        except ValueError:
            pass

    def render_gl(self):
        """Render housing using OpenGL with rotation support"""

        if self._is_deleted:
            return

        if self._position is None:
            return

        x = self._position.x
        y = self._position.y

        # Get rotation angle (Z-axis for 2D)
        rotation_rad = self._angle.z  # Z component in radians

        # Save current transformation matrix
        GL.glPushMatrix()

        # Apply transformations: translate, then rotate
        GL.glTranslatef(x, y, 0.0)
        GL.glRotatef(math.degrees(rotation_rad), 0.0, 0.0, 1.0)

        # Draw housing body (filled) - centered at origin after translation
        GL.glColor4f(0.3, 0.3, 0.3, 0.4)  # Semi-transparent dark gray
        GL.glBegin(GL.GL_QUADS)
        h_width = self._width / 2
        h_height = self._height / 2

        GL.glVertex2f(-h_width, -h_height)
        GL.glVertex2f(h_width, -h_height)
        GL.glVertex2f(h_width, h_height)
        GL.glVertex2f(-h_width, h_height)
        GL.glEnd()

        # Draw housing outline
        GL.glColor4f(0.4, 0.4, 0.4, 1.0)  # Dark gray
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINE_LOOP)

        GL.glVertex2f(-h_width, -h_height)
        GL.glVertex2f(h_width, -h_height)
        GL.glVertex2f(h_width, h_height)
        GL.glVertex2f(-h_width, h_height)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def render_selection(self):
        """Render selection highlight with rotation"""
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

        # Draw selection outline
        GL.glColor4f(1.0, 1.0, 0.0, 1.0)  # Yellow
        GL.glLineWidth(3.5)

        offset = 3.0
        GL.glBegin(GL.GL_LINE_LOOP)
        h_width = self._width / 2
        h_height = self._height / 2

        GL.glVertex2f(-h_width - offset, -h_height - offset)
        GL.glVertex2f(h_width + offset, -h_height - offset)
        GL.glVertex2f(h_width + offset, h_height + offset)
        GL.glVertex2f(-h_width - offset, h_height + offset)
        GL.glEnd()

        # Restore transformation matrix
        GL.glPopMatrix()

    def hit_test(self, world_pos: _point.Point) -> bool:
        """
        Test if point is inside housing (accounting for rotation)

        Uses inverse rotation to transform the point into housing's local space
        """
        if self._position is None:
            return False

        # Translate point to housing's local space
        local_pos = world_pos - self._position

        # Rotate point by negative angle (inverse rotation)
        rotation_rad = -self._angle.z
        cos_a = _d(math.cos(rotation_rad))
        sin_a = _d(math.sin(rotation_rad))

        rotated_x = local_pos.x * cos_a - local_pos.y * sin_a
        rotated_y = local_pos.x * sin_a + local_pos.y * cos_a

        # Check if within bounds
        return (abs(rotated_x) <= self._width / 2 and
                abs(rotated_y) <= self._height / 2)

    def get_bounds(self):
        """Get bounding box"""
        if self._position is None:
            return None

        x = self._position.x
        y = self._position.y

        h_width = self._width / 2
        h_height = self._height / 2

        return (x - h_width, y - h_height,
                x + h_width, y + h_height)

    def move_to(self, world_x: float, world_y: float):
        """
        Move housing to new position

        This implements hierarchical movement - all child cavities move with the housing.
        Uses context manager to defer callbacks until all updates are complete.
        """
        if self._position is None:
            return

        # Calculate offset from current position
        dx = world_x - self._position.x
        dy = world_y - self._position.y

        # Move the housing (use context manager to defer callbacks)
        with self._position:
            self._position.x = world_x
            self._position.y = world_y

        # Move all child cavities by the same offset
        for cavity in self._cavities:
            if hasattr(cavity, 'obj2d') and hasattr(cavity.obj2d, '_position'):
                cavity_pos = cavity.obj2d._position
                if cavity_pos is not None:
                    with cavity_pos:
                        cavity_pos.x += dx
                        cavity_pos.y += dy


class HousingMenu(QMenu):
    """Represent a housing menu in :mod:`harness_designer.objects.objects2d.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`HousingMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add CPA Lock')
        action.triggered.connect(self.on_add_cpa_lock)

        action = self.addAction('Add TPA Lock')
        action.triggered.connect(self.on_add_tpa_lock)

        action = self.addAction('Add Cover')
        action.triggered.connect(self.on_add_cover)

        action = self.addAction('Add Boot')
        action.triggered.connect(self.on_add_boot)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate2DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror2DMenu(canvas, selected)
        self.addMenu(mirror_menu)

        self.addSeparator()
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

    def on_add_seal(self):
        """Handle the add seal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_terminal(self):
        """Handle the add terminal event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_cpa_lock(self):
        """Handle the add CPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_tpa_lock(self):
        """Handle the add TPA lock event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_cover(self):
        """Handle the add cover event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_boot(self):
        """Handle the add boot event.

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
