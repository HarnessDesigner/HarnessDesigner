# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QSize
from PySide6 import QtGui

from . import canvas as _canvas
from ... import check_types as _check_types
from ..canvas_base import canvas_window_base as _canvas_window_base

if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class CanvasWindow(_canvas_window_base.CanvasWindowBase):
    """Represent a canvas 3D in :mod:`harness_designer.gl.canvas3d.canvas3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame", config: "_config.Config.editor_3d",
                 size, axis_overlay: bool = False):
        """Initialise the :class:`Canvas3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Parent object.
        :type mainframe: :class:`_ui.MainFrame`
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor_3d`
        :param size: Value for ``size``.
        :type size: UNKNOWN
        :param axis_overlay: Value for ``axis_overlay``.
        :type axis_overlay: bool
        """

        self._canvas = _canvas.Canvas(mainframe, config)

        super().__init__(mainframe, config, size)

        from . import axis_overlay as _axis_overlay

        if axis_overlay:
            self._axis_overlay = _axis_overlay.Overlay(self, config.axis_overlay)
        else:
            self._axis_overlay = None

    @_check_types.do
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """
        Execute the resize event operation.

        :param event: Event object.
        :type event: :class:`QtGui.QResizeEvent`
        """

        super().resizeEvent(event)
        self._reposition_axis_overlay()

    @_check_types.do
    def _reposition_axis_overlay(self) -> None:
        """
        Execute the reposition axis overlay operation.
        """

        axis_overlay = self._axis_overlay

        if axis_overlay is None:
            return

        pos = axis_overlay.pos()
        x1 = pos.x()
        y1 = pos.y()

        size = axis_overlay.size()
        x2 = x1 + size.width()
        y2 = y1 + size.height()

        size = self.size()
        w = size.width()
        h = size.height()

        if x1 < 0:
            x_offset = -x1
        elif x2 > w:
            x_offset = w - x2
        else:
            x_offset = 0

        if y1 < 0:
            y_offset = -y1
        elif y2 > h:
            y_offset = h - y2
        else:
            y_offset = 0

        x = x1 + x_offset
        y = y1 + y_offset

        if x != x1 or y != y1:
            axis_overlay.move(x, y)
