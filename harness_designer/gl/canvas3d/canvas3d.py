# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QEvent, Qt, QTimer

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas3D(QWidget):

    def __init__(self, parent: "_ui.MainFrame", config: "_config.Config.editor3d",
                 size=None, axis_overlay=False):

        QWidget.__init__(self, parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self._ref_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = _canvas.Canvas(
            self, config, axis_overlay=axis_overlay)
        layout.addWidget(self._canvas)

        if size is not None:
            self._canvas.resize(size)

        self.config = config

    def event(self, event):
        if event.type() == QEvent.MouseCaptureLost:
            pass  # canvas handles its own mouse capture release
        return QWidget.event(self, event)

    def resizeEvent(self, event):
        QWidget.resizeEvent(self, event)

        def _do():
            x1 = self.mapToGlobal(self.rect().topLeft()).x()
            y1 = self.mapToGlobal(self.rect().topLeft()).y()
            w = self.width()
            h = self.height()

            x2 = x1 + w
            y2 = y1 + h
            axis_overlay = self._canvas.axis_overlay

            if axis_overlay is not None:
                ao_global = axis_overlay.mapToGlobal(axis_overlay.rect().topLeft())
                ax1 = ao_global.x()
                ay1 = ao_global.y()
                aw = axis_overlay.width()
                ah = axis_overlay.height()

                ax2 = ax1 + aw
                ay2 = ay1 + ah

                x = 0
                y = 0

                if ax1 < x1:
                    x = x1
                elif ax2 > x2:
                    x = x2 - aw

                if ay1 < y1:
                    y = y1
                elif ay2 > y2:
                    y = y2 - ah

                if x or y:
                    new_local = axis_overlay.mapFromGlobal(
                        axis_overlay.mapToGlobal(axis_overlay.rect().topLeft())
                        .__class__(x, y)
                    )
                    axis_overlay.move(new_local)
                    axis_overlay.update()

        QTimer.singleShot(0, _do)

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

    def Truck(self, delta) -> None:
        self._canvas.TruckPedestal(delta, 0.0)

    def Pedestal(self, delta) -> None:
        self._canvas.TruckPedestal(0.0, delta)

    def TruckPedestal(self, truck_delta, pedestal_delta) -> None:
        self._canvas.TruckPedestal(truck_delta, pedestal_delta)

    def Zoom(self, delta):
        self._canvas.Zoom(delta, None)

    def RotateAbout(self, delta_x, delta_y) -> None:
        self._canvas.Rotate(delta_x, delta_y)

    def Dolly(self, delta):
        self._canvas.Walk(delta, 0.0)

    def Walk(self, delta_z, delta_x) -> None:
        self._canvas.Walk(delta_z, delta_x)

    def Pan(self, delta):
        self._canvas.PanTilt(delta, 0.0)

    def Tilt(self, delta) -> None:
        self._canvas.PanTilt(0.0, delta)

    def PanTilt(self, pan_delta, tilt_delta):
        self._canvas.PanTilt(pan_delta, tilt_delta)
