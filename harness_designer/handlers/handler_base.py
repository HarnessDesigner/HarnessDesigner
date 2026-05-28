# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Base classes and shared helpers for interactive editor handlers.
"""

from typing import TYPE_CHECKING

from ..geometry import point as _point


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..geometry import point as _point


class HandlerBase:
    """
    Base class for the 3d handlers
    """

    def __init__(self, mainframe: "_ui.MainFrame", part_id: int):
        """Initialize the object and capture the state required for later interaction.

        :param mainframe: Main application frame that owns the editor and project state.
        :type mainframe: "_ui.MainFrame"
        :param part_id: Identifier of the selected part definition.
        :type part_id: int
        """
        self.mainframe = mainframe
        self.part_id = part_id
        self.obj = None
        self.is_active = False
        self.camera = self.mainframe.editor3d.camera
        self.ptables = mainframe.project.ptables
        self._captured_position: "_point.Point" = None
        self._finalized = False

    def capture_position(self, position: "_point.Point") -> None:
        """Store the most recently captured cursor position for later use by the handler.

        :param position: 3D point used for placement or geometric calculations.
        :type position: "_point.Point"
        """
        self._captured_position = position

    def release_capture(self) -> None:
        """Handle release of the captured position and complete any deferred placement work.

        :raises NotImplementedError: Raised by handlers that require a subclass implementation.
        """
        raise NotImplementedError

    def finalize(self, mouse_pos: _point.Point):
        """Finalize the active operation using the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        :raises NotImplementedError: Raised when the base handler hook is called directly.
        """
        raise NotImplementedError

    def start(self, mouse_pos: _point.Point):
        """Start the handler operation for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        :raises NotImplementedError: Raised when the base handler hook is called directly.
        """
        raise NotImplementedError

    def hover(self, mouse_pos: _point.Point):
        """Update preview or highlight state for the supplied mouse position.

        :param mouse_pos: Mouse position used for picking or preview updates.
        :type mouse_pos: _point.Point
        """
        pass

    def cancel(self):
        """Cancel the active operation and clean up any preview objects.
        """
        self.obj.delete()

    @property
    def is_finalized(self) -> bool:
        """Return whether the handler has completed all required work.

        :returns: :data:`True` when the handler has finished its work; otherwise :data:`False`.
        :rtype: bool
        """
        return self._finalized
