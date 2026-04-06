from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...geometry import angle as _angle


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui
    from ...ui import editor_2d as _editor_2d
    from ...database import project_db as _project_db


class Base2D:
    """
    Base class for 2D schematic representations of objects

    Uses OpenGL for rendering in the 2D schematic editor.
    """

    def __init__(self, parent: "_ObjectBase",
                 db_obj: "_project_db.PJTEntryBase",
                 position: _point.Point, angle: _angle.Angle):

        self.parent: "_ObjectBase" = parent
        self.db_obj = db_obj
        try:
            self.editor2d: "_editor_2d.Editor2D" = parent.mainframe.editor2d
            self.mainframe: "_ui.MainFrame" = parent.mainframe
        except AttributeError:
            return

        self._position = position
        self._o_position = position.copy()
        self._angle = angle
        self._o_angle = angle.copy()

        self._is_selected = False

        self._position.bind(self._on_position)
        self._angle.bind(self._on_angle)

    def _on_position(self, position: _point.Point) -> None:
        """Called when housing position changes"""
        self._o_position = position.copy()
        self.editor2d.editor.canvas.Refresh()

    def _on_angle(self, angle: _angle.Angle) -> None:
        """Called when housing angle changes"""
        self._o_angle = angle.copy()
        self.editor2d.editor.canvas.Refresh()

    @property
    def position(self) -> _point.Point:
        return self._position

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    def set_selected(self, flag: bool) -> None:
        self._is_selected = flag

        if flag:
            self.mainframe._set_selected(self.parent)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def render_gl(self) -> None:
        """
        Render this object using OpenGL

        Override this method in subclasses to implement specific rendering.
        """
        pass

    def render_selection(self) -> None:
        """
        Render selection highlight using OpenGL

        Override this method to customize selection appearance.
        """
        pass

    def hit_test(self, world_pos: "_point.Point") -> bool:
        """
        Test if a point hits this object

        Args:
            world_pos: world position

        Returns:
            True if the point hits this object
        """
        return False

    def get_bounds(self):
        """
        Get bounding box of this object

        Returns:
            tuple: (min_x, min_y, max_x, max_y) or None
        """
        return None

    def move_to(self, world_x: float, world_y: float):
        """
        Move this object to a new position

        Args:
            world_x: New world X coordinate
            world_y: New world Y coordinate
        """
        pass
