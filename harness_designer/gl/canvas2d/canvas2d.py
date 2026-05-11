# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QEvent, Qt

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas2D(QWidget):

    def __init__(self, parent: "_ui.MainFrame", config: "_config.Config.editor2d", size=None):

        QWidget.__init__(self, parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self._ref_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = _canvas.Canvas(self, config)
        layout.addWidget(self._canvas)

        if size is not None:
            self._canvas.resize(size)

        self.config = config

    def event(self, event):
        if event.type() == QEvent.MouseCaptureLost:
            pass  # canvas handles its own mouse capture release
        return QWidget.event(self, event)

    @property
    def context(self):
        return self._canvas.context

    @property
    def camera(self):
        return self._canvas.camera

    def set_selected(self, obj):
        self._canvas.set_selected(obj)

    def set_mode(self, mode: int) -> None:
        self._canvas.set_mode(mode)

    def add_object(self, obj):
        self._canvas.add_object(obj)

    def remove_object(self, obj):
        self._canvas.remove_object(obj)

    def __enter__(self):
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    def Refresh(self, *args, **kwargs):
        if self._ref_count:
            return

        self._canvas.update()
