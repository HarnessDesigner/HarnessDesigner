# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6 import QtCore, QtGui

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas3D(QWidget):

    def __init__(self, parent: "QWidget", config: "_config.Config.editor3d",
                 size, axis_overlay=False):

        QWidget.__init__(self, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._ref_count = 0
        self.config = config

        # Canvas is now a direct child of this widget — no viewport() indirection
        self._canvas = _canvas.Canvas(
            self, config, axis_overlay=axis_overlay)

        vw, vh = size
        self._canvas.setFixedSize(vw, vh)
        self._virtual_size = QSize(vw, vh)

        size = self.size()
        w = size.width()
        h = size.height()

        x = (w - vw) // 2
        y = (h - vh) // 2
        self._canvas.move(x, y)

    # ------------------------------------------------------------------
    # Virtual-size API  (mirrors wx SetVirtualSize / GetVirtualSize)
    # ------------------------------------------------------------------

    def set_virtual_size(self, w: int, h: int) -> None:
        """
        Explicitly set the canvas's virtual (render) size.

        The canvas will keep this size even if the surrounding panel is
        made smaller or larger.  The aspect ratio and GL viewport are
        therefore stable — exactly like wx SetVirtualSize.
        """
        self._virtual_size = QSize(w, h)
        self._canvas.setFixedSize(w, h)
        # Tell the inner canvas to update its GL viewport for the new size
        self._canvas.notify_virtual_size_changed(w, h)

    def get_virtual_size(self) -> tuple[int, int]:
        return self._virtual_size.width(), self._virtual_size.height()

    # ------------------------------------------------------------------
    # QAbstractScrollArea overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        QWidget.resizeEvent(self, event)

        vw = self._virtual_size.width()
        vh = self._virtual_size.height()

        size = self.size()
        w = size.width()
        h = size.height()

        x = (w - vw) // 2
        y = (h - vh) // 2
        self._canvas.move(x, y)

        # Reposition axis overlay so it stays within the visible viewport
        self._reposition_axis_overlay()

    def _reposition_axis_overlay(self) -> None:
        axis_overlay = self._canvas.axis_overlay

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

    # ------------------------------------------------------------------
    # Forwarded API — identical public interface as before
    # ------------------------------------------------------------------

    def event(self, evt):
        return QWidget.event(self, evt)

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

    def bind(self, signal_name: str, handler) -> None:
        """Forward signal connections to the inner QOpenGLWidget canvas."""
        getattr(self._canvas, signal_name).connect(handler)

    def Refresh(self, *_, **__):
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

    def cleanup(self):
        """Clean up GL resources before widget destruction."""
        self._canvas.cleanup()
