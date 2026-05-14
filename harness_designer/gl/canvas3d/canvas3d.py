# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QAbstractScrollArea, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6 import QtCore, QtGui

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas3D(QAbstractScrollArea):
    """
    Container widget for the 3-D OpenGL canvas that replicates the
    wx SetVirtualSize / virtual-canvas behaviour.

    wx behaviour recap
    ------------------
    * The GLCanvas had a *virtual size* larger (or equal) to the window.
    * Resizing the panel that held the canvas did NOT change the canvas
      size — it only changed how much of the virtual canvas was visible.
    * The GL viewport, projection aspect-ratio, etc. were therefore stable
      and never distorted by panel resizes.

    PySide6 equivalent
    ------------------
    * Canvas3D inherits QAbstractScrollArea.  The inner QOpenGLWidget
      lives in the scroll area's *viewport()* but is positioned manually
      (no layout manager) so it can be larger than the visible area.
    * When the outer frame resizes, only the *viewport* window changes
      size.  The inner canvas keeps its virtual size and is simply
      clipped.  No resizeGL / aspect-ratio change occurs.
    * Call set_virtual_size(w, h) to explicitly change the canvas
      dimensions (mirrors wx SetVirtualSize).
    * When no explicit size is supplied the canvas starts at the same
      size as the container and grows with it — identical to the old
      behaviour when the panel and canvas started at the same size.
    """

    def __init__(self, parent: "QWidget", config: "_config.Config.editor3d",
                 size=(), axis_overlay=False):

        QAbstractScrollArea.__init__(self, parent)

        # Hide scroll bars — we mirror wx which showed no scroll bars
        # (the "virtual" area was just a larger GL surface, not scrollable
        # in the traditional sense).  Flip to ScrollBarAsNeeded if you
        # want scroll bars later.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QAbstractScrollArea.Shape.NoFrame)

        self._ref_count = 0
        self.config = config

        # The actual OpenGL canvas sits inside the scroll area's viewport
        # widget.  We position it manually so it can exceed the visible area.
        self._canvas = _canvas.Canvas(
            self.viewport(), config, axis_overlay=axis_overlay)

        # If an explicit virtual size was requested, apply it immediately.
        # Otherwise start at (0, 0) — the first resizeEvent will sync it.
        if size:
            w, h = size
            self._canvas.setFixedSize(w, h)
            self._virtual_size = QSize(w, h)
        else:
            self._virtual_size = QSize(0, 0)  # filled in first resizeEvent

        self._canvas.move(0, 0)

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
        """
        Called when the *outer* container is resized.

        wx behaviour: the canvas size was unaffected; only the visible
        window into it changed.

        Qt equivalent: if no explicit virtual size has been set yet, grow
        the canvas to match the new container size (same as wx when the
        canvas and panel start at the same dimensions).  Once an explicit
        virtual size is set, the canvas is left at that size.
        """
        QAbstractScrollArea.resizeEvent(self, event)

        vw = self.viewport().width()
        vh = self.viewport().height()

        if self._virtual_size.isEmpty():
            # First resize — initialise virtual size to container size
            self._virtual_size = QSize(vw, vh)
            self._canvas.setFixedSize(vw, vh)
            self._canvas.notify_virtual_size_changed(vw, vh)
        # else: virtual size was set explicitly — do NOT resize the canvas

        # Reposition axis overlay so it stays within the visible viewport
        QTimer.singleShot(0, self._reposition_axis_overlay)

    def _reposition_axis_overlay(self) -> None:
        axis_overlay = self._canvas.axis_overlay
        if axis_overlay is None:
            return

        vx1 = self.viewport().mapToGlobal(self.viewport().rect().topLeft()).x()
        vy1 = self.viewport().mapToGlobal(self.viewport().rect().topLeft()).y()
        vx2 = vx1 + self.viewport().width()
        vy2 = vy1 + self.viewport().height()

        ao_global = axis_overlay.mapToGlobal(axis_overlay.rect().topLeft())
        ax1 = ao_global.x()
        ay1 = ao_global.y()
        aw = axis_overlay.width()
        ah = axis_overlay.height()
        ax2 = ax1 + aw
        ay2 = ay1 + ah

        x = y = 0
        if ax1 < vx1:
            x = vx1
        elif ax2 > vx2:
            x = vx2 - aw

        if ay1 < vy1:
            y = vy1
        elif ay2 > vy2:
            y = vy2 - ah

        if x or y:
            new_local = axis_overlay.mapFromGlobal(
                axis_overlay.mapToGlobal(
                    axis_overlay.rect().topLeft()).__class__(x, y)
            )
            axis_overlay.move(new_local)
            axis_overlay.update()

    # ------------------------------------------------------------------
    # Forwarded API — identical public interface as before
    # ------------------------------------------------------------------

    def event(self, event):
        return QAbstractScrollArea.event(self, event)

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
