from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui
    from ...ui import editor_2d as _editor_2d
    from ...database import project_db as _project_db
    from ...geometry import point as _point


class Base2D:
    """
    Base class for 2D schematic representations of objects

    Uses OpenGL for rendering in the 2D schematic editor.
    """

    def __init__(self, parent: "_ObjectBase",
                 db_obj: "_project_db.PJTEntryBase"):

        self._parent: "_ObjectBase" = parent
        self.db_obj = db_obj

        self.editor2d: "_editor_2d.Editor2D" = parent.mainframe.editor2d
        self.mainframe: "_ui.MainFrame" = parent.mainframe

        self._is_selected = False

    def set_selected(self, flag: bool):
        self._is_selected = flag

        if flag:
            self.mainframe._set_selected(self._parent)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def render_gl(self):
        """
        Render this object using OpenGL

        Override this method in subclasses to implement specific rendering.
        """
        pass

    def render_selection(self):
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
