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
    def objects_in_window(self) -> list:
        """Objects from :attr:`objects_in_view` that are actually visible
        through this wrapper's on-screen window -- not just anywhere in
        the camera's frustum.

        ``objects_in_view`` is culled against the full, fixed-size
        *virtual* canvas (``self._virtual_size``) -- but the inner canvas
        is never resized to match this wrapper; it's recentered inside it
        via ``move()`` (see ``__init__``/``resizeEvent`` above) and
        whatever doesn't fit is simply clipped by Qt at this wrapper's own
        (usually much smaller) bounds. So an object can be squarely inside
        the camera's frustum while sitting in the cropped-away part of the
        virtual canvas the user can't actually see. This re-checks each
        candidate's projected screen position against the real visible
        rectangle. Used only for the "should this editor re-center on the
        newly selected object" decision (see ``MainFrame._set_selected``)
        -- everywhere else that cares about "is this in view" genuinely
        means the frustum, not the visible window (e.g. accessory
        placement gating on ``is_in_3dview``), so this is deliberately a
        separate method rather than a change to ``objects_in_view`` itself.
        """
        vw = self._virtual_size.width()
        vh = self._virtual_size.height()

        w = self.width()
        h = self.height()

        left = (vw - w) // 2
        top = (vh - h) // 2
        right = left + w
        bottom = top + h

        camera = self._canvas.camera
        get_view_object = self._canvas._get_view_object  # NOQA

        result = []
        for obj in self.objects_in_view:
            view_obj = get_view_object(obj)
            if view_obj is None or view_obj.position is None:
                continue

            screen = camera.ProjectPoint(view_obj.position)
            if screen is None:
                continue

            if left <= screen.x <= right and top <= screen.y <= bottom:
                result.append(obj)

        return result

    @_check_types.do
    def required_zoom_scale(self, aabb_min, aabb_max) -> float:
        """Scale factor (>= 1.0) the current zoom needs to widen by so an
        object with this world-space AABB fits inside the actually-
        visible window (see :meth:`objects_in_window`'s own docstring on
        why that's not the same as the camera's full frustum), with a 30%
        margin. Returns ``1.0`` when it already fits at the current zoom
        -- callers must never scale down (in) with this, only up (out),
        matching ``center_on_object``'s "never surprise the user by
        changing how zoomed in they are, beyond what's needed to actually
        see the thing" rule.
        """
        camera = self._canvas.camera

        xs = []
        ys = []
        for x in (float(aabb_min[0]), float(aabb_max[0])):
            for y in (float(aabb_min[1]), float(aabb_max[1])):
                for z in (float(aabb_min[2]), float(aabb_max[2])):
                    screen = camera.ProjectPoint((x, y, z))
                    if screen is None:
                        return 1.0

                    xs.append(screen.x)
                    ys.append(screen.y)

        proj_w = max(xs) - min(xs)
        proj_h = max(ys) - min(ys)

        w = self.width()
        h = self.height()

        if proj_w <= 0.0 or proj_h <= 0.0 or w <= 0 or h <= 0:
            return 1.0

        margin = 1.30
        scale = max((proj_w * margin) / w, (proj_h * margin) / h)

        return max(scale, 1.0)

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

    @property
    @_check_types.do
    def bounds_manager(self):
        """Forwarded from the inner canvas. ``gl.object_picker.find_object``
        picks through it, and many handlers hand it this wrapper (their
        ``self.canvas``) rather than the inner canvas."""
        return self._canvas.bounds_manager

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
