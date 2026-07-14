# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore

from . import viewer as _viewer
from .. import dock_base as _dock_base

if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class LogViewer(_dock_base.DockBase):
    """
    Represent a log viewer in :mod:`harness_designer.ui.log_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`LogViewer` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = LogViewerPanel(mainframe, mainframe.logger)
        super().__init__(mainframe, 'Log Viewer', 'log_viewer',
                         QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

    @property
    def viewer(self) -> "LogViewerPanel":
        return self._ui_obj


class LogViewerPanel(_viewer.ViewerPanel):
    pass
