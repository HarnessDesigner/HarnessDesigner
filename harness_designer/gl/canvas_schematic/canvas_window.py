# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import canvas as _canvas
from ... import check_types as _check_types
from ..canvas_base import canvas_window_base as _canvas_window_base

if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class CanvasWindow(_canvas_window_base.CanvasWindowBase):
    """
    Represent a canvas schematic in :mod:`harness_designer.gl.canvas_schematic.canvas_window`.
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame",
                 config: "_config.Config.editor_schematic", size=None):
        """
        Initialise the :class:`Canvas2D` instance.

        :param mainframe: Parent object.
        :type mainframe: :class:`_ui.MainFrame`

        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor_schematic`

        :param size: Value for ``size``.
        :type size: UNKNOWN
        """

        self._canvas = _canvas.Canvas(mainframe, config)

        super().__init__(mainframe, config, size)
