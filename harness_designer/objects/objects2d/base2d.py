# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
        """Initialise the :class:`Base2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: _ObjectBase
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        :param position: Position value.
        :type position: :class:`_point.Point`
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

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

    def identify(self, color: list[float] | None):
        """Execute the identify operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param color: Value for ``color``.
        :type color: list[float] | None
        """
        pass

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
        """Return the position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self._position

    @property
    def angle(self) -> _angle.Angle:
        """Return the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """
        return self._angle

    def set_selected(self, flag: bool) -> None:
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._is_selected = flag

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_selected

    def render_gl(self, program: int, proj, view) -> None:
        """
        Render this object using the schematic2d shader.

        Parameters
        ----------
        program  Compiled schematic2d shader program handle for this context.
        proj     (4,4) float32 orthographic projection matrix from Canvas.
        view     (4,4) float32 view matrix from Canvas (identity for 2D).

        The 3D VBO shared with canvas3d is reused here.  The schematic2d
        vertex shader projects 3D vertices onto the XZ plane (Y-up world
        coords, flipY=0) to produce the top-down schematic view:
            2D X = 3D X
            2D Y = 3D Z

        The 2D position (self._position) is the canvas-local position that
        the user can move freely, independent of the 3D position.

        Override this method in subclasses to implement object-specific
        rendering.
        """
        pass

    def render_selection(self, program: int, proj, view) -> None:
        """
        Render selection highlight using the schematic2d shader.

        Override this method to customise selection appearance.
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
