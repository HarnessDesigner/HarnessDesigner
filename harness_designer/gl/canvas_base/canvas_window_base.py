# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6 import QtCore, QtGui

from . import canvas_base as _canvas_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


class CanvasWindowBase(QWidget):
    """
    Represent a canvas 3D.
    """

    # the canvas must be set before calling super()
    _canvas: _canvas_base.CanvasBase = None

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", config, size):
        """
        Initialise the :class:`Canvas3D` instance.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`

        :param config: Value for ``config``.
        :type config: UNKNOWN

        :param size: Value for ``size``.
        :type size: UNKNOWN
        """

        QWidget.__init__(self, parent)

        self._canvas.setParent(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._ref_count = 0
        self.config = config

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

    @_check_types.do
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

    @_check_types.do
    def get_virtual_size(self) -> tuple[int, int]:
        """
        Return the virtual size.

        :returns: Return value. UNKNOWN details.
        :rtype: tuple[int, int]
        """

        return self._virtual_size.width(), self._virtual_size.height()

    # ------------------------------------------------------------------
    # QAbstractScrollArea overrides
    # ------------------------------------------------------------------

    @_check_types.do
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """
        Execute the resize event operation.

        :param event: Event object.
        :type event: :class:`QtGui.QResizeEvent`
        """

        QWidget.resizeEvent(self, event)

        vw = self._virtual_size.width()
        vh = self._virtual_size.height()

        size = self.size()
        w = size.width()
        h = size.height()

        x = (w - vw) // 2
        y = (h - vh) // 2
        self._canvas.move(x, y)

    # ------------------------------------------------------------------
    # Forwarded API — identical public interface as before
    # ------------------------------------------------------------------

    @_check_types.do
    def event(self, evt):
        """
        Execute the event operation.

        :param evt: Event object.
        :type evt: UNKNOWN

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return QWidget.event(self, evt)

    @property
    @_check_types.do
    def context(self):
        """
        Return the context.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._canvas.context

    @property
    @_check_types.do
    def camera(self):
        """
        Return the camera.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return self._canvas.camera

    @property
    @_check_types.do
    def mainframe(self):
        """The owning MainFrame -- forwarded from the inner canvas (see
        ``CanvasBase.__init__``), needed by every drag/rotation/add
        handler constructed with *this* wrapper as their own ``canvas``
        (e.g. ``Base3D.handle_interaction`` arming a handler with
        ``self.editor3d.editor``) -- they're never handed the inner
        ``Canvas`` directly, only this outer window.
        """
        return self._canvas.mainframe

    @property
    @_check_types.do
    def objects_in_view(self) -> list:
        """Forwarded from the inner canvas -- see :attr:`mainframe`'s own
        docstring for why outward-facing code needs this on the wrapper
        too, not just internally on the inner canvas.
        """
        return self._canvas.objects_in_view

    @_check_types.do
    def get_selected(self):
        """Forwarded from the inner canvas -- see :attr:`mainframe`'s own
        docstring.
        """
        return self._canvas.get_selected()

    @property
    @_check_types.do
    def active_handler_obj(self):
        """Forwarded from the inner canvas -- see
        ``objectsvar.base_var.BaseVar.handle_interaction`` and
        :attr:`mainframe`'s own docstring on why outward-facing code
        (every ``start_add`` classmethod, ``Base3D.handle_interaction``'s
        own drag/rotation arming, ``MainFrame._cancel_active_handler_obj``)
        needs this reachable through the wrapper it's actually handed,
        not just internally on the inner canvas ``MouseHandlerBase``
        itself already operates on directly.
        """
        return self._canvas.active_handler_obj

    @active_handler_obj.setter
    @_check_types.do
    def active_handler_obj(self, value):
        self._canvas.active_handler_obj = value

    @_check_types.do
    def set_selected(self, obj):
        """
        Set the selected.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._canvas.set_selected(obj)

    @_check_types.do
    def set_mode(self, mode: int) -> None:
        """
        Set the mode.

        :param mode: Value for ``mode``.
        :type mode: int
        """

        self._canvas.set_mode(mode)

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._canvas.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._canvas.remove_object(obj)

    @_check_types.do
    def clear(self) -> None:
        """
        Drop every scene object in bulk, without touching the database.
        """

        self._canvas.clear()

    @_check_types.do
    def __enter__(self):
        """
        Enter the managed context.
        """

        self._ref_count += 1
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the managed context.
        """

        self._ref_count -= 1

    @_check_types.do
    def bind(self, signal_name: str, handler) -> None:
        """
        Forward signal connections to the inner QOpenGLWidget canvas.
        """

        getattr(self._canvas, signal_name).connect(handler)

    @_check_types.do
    def Refresh(self, *_, **__):
        """
        Execute the refresh operation.
        """

        if self._ref_count:
            return

        self._canvas.update()

    @_check_types.do
    def Truck(self, delta) -> None:
        """
        Execute the truck operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.TruckPedestal(delta, 0.0)

    @_check_types.do
    def Pedestal(self, delta) -> None:
        """
        Execute the pedestal operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.TruckPedestal(0.0, delta)

    @_check_types.do
    def TruckPedestal(self, truck_delta, pedestal_delta) -> None:
        """
        Execute the truck pedestal operation.

        :param truck_delta: Value for ``truck_delta``.
        :type truck_delta: UNKNOWN

        :param pedestal_delta: Value for ``pedestal_delta``.
        :type pedestal_delta: UNKNOWN
        """

        self._canvas.TruckPedestal(truck_delta, pedestal_delta)

    @_check_types.do
    def Zoom(self, delta):
        """
        Execute the zoom operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.Zoom(delta, None)

    @_check_types.do
    def RotateAbout(self, delta_x, delta_y) -> None:
        """
        Execute the rotate about operation.

        :param delta_x: Value for ``delta_x``.
        :type delta_x: UNKNOWN

        :param delta_y: Value for ``delta_y``.
        :type delta_y: UNKNOWN
        """

        self._canvas.Rotate(delta_x, delta_y)

    @_check_types.do
    def Dolly(self, delta):
        """
        Execute the dolly operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.Walk(delta, 0.0)

    @_check_types.do
    def Walk(self, delta_z, delta_x) -> None:
        """
        Execute the walk operation.

        :param delta_z: Value for ``delta_z``.
        :type delta_z: UNKNOWN

        :param delta_x: Value for ``delta_x``.
        :type delta_x: UNKNOWN
        """

        self._canvas.Walk(delta_z, delta_x)

    @_check_types.do
    def Pan(self, delta):
        """
        Execute the pan operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.PanTilt(delta, 0.0)

    @_check_types.do
    def Tilt(self, delta) -> None:
        """
        Execute the tilt operation.

        :param delta: Value for ``delta``.
        :type delta: UNKNOWN
        """

        self._canvas.PanTilt(0.0, delta)

    @_check_types.do
    def PanTilt(self, pan_delta, tilt_delta):
        """
        Execute the pan tilt operation.

        :param pan_delta: Value for ``pan_delta``.
        :type pan_delta: UNKNOWN

        :param tilt_delta: Value for ``tilt_delta``.
        :type tilt_delta: UNKNOWN
        """

        self._canvas.PanTilt(pan_delta, tilt_delta)

    @_check_types.do
    def cleanup(self):
        """
        Clean up GL resources before widget destruction.
        """

        self._canvas.cleanup()
