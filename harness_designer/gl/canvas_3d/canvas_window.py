# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
import numpy as np
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
    def create_focal_target(self) -> None:
        """Forwarded from the inner canvas -- see
        :meth:`Canvas.create_focal_target`."""
        self._canvas.create_focal_target()

    @_check_types.do
    def delete_focal_target(self) -> None:
        """Forwarded from the inner canvas -- see
        :meth:`Canvas.delete_focal_target`."""
        self._canvas.delete_focal_target()

    @_check_types.do
    def _camera_state(self) -> tuple[float, ...]:
        """
        Camera position and focal position -- everything a fit sets.
        """

        camera = self._canvas.camera

        return (*camera.position.as_float, *camera.focal_position.as_float)

    @_check_types.do
    def _apply_fit(self, lo: np.ndarray, hi: np.ndarray, width: int, height: int) -> None:
        """
        Move the whole camera rig -- eye and focal point together -- to
        where the box *lo*..*hi* is centered in the *width* x *height*
        pixel window and just fits. The distance between the eye and the
        focal point, and the viewing direction, are left exactly as they
        are (see :meth:`Camera.MoveRigTo`): the rig slides sideways to
        center the project and backs off along its own view axis until
        all 8 corners are inside the window.

        The projection is built for the whole fixed virtual surface (see
        ``Canvas._set_view``), so both axes share one pixel scale, set by
        that surface's height and the vertical FOV; the window is a
        centered crop of it. With the box center on the view axis, a
        corner lying ``x``/``y`` off the axis and ``z`` past the center
        is ``t + z`` deep from an eye ``t`` back from the center, and is
        visible when ``|x| <= tan_x * (t + z)`` (same for y) -- so the
        ``t`` that just fits the whole box is the largest
        ``|x| / tan_x - z`` / ``|y| / tan_y - z`` over the corners.
        """

        camera = self._canvas.camera

        # forward/up are only refreshed at paint time, not on every move --
        # make sure they reflect wherever the camera is right now.
        camera.set()

        focal_px = (self._virtual_size.height() / 2.0) / math.tan(math.radians(_canvas.FOV_DEGREES) / 2.0)
        tan_x = (width / 2.0) / focal_px
        tan_y = (height / 2.0) / focal_px

        center = (lo + hi) / 2.0

        corners = np.array(
            [[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])],
            dtype=np.float64) - center

        forward = camera.forward.astype(np.float64)
        right = np.cross(forward, camera.up.astype(np.float64))
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)

        across = corners @ right
        vertical = corners @ up
        depth = corners @ forward

        back = max(float((np.abs(across) / tan_x - depth).max()),
                   float((np.abs(vertical) / tan_y - depth).max()),
                   # never let a corner end up at or behind the eye
                   float(1.0 - depth.min()),
                   self._fit_min_distance)

        camera.MoveRigTo(center - forward * back)

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

        # Skip while this canvas isn't shown yet -- it's built (and the
        # overlay moved to its remembered position) well before the
        # surrounding dock widget/window is ever shown, and Qt fires
        # several resizeEvents as that layout settles into its real
        # size. Clamping the overlay against those still-too-small
        # transitional sizes below would move() it, and that move()
        # triggers the overlay's own moveEvent(), which persists
        # whatever position it lands on back into config.position --
        # permanently overwriting a correct remembered position with a
        # wrong, pre-layout one before the user ever sees the window.
        # Only a real post-show resize (the user resizing the window/
        # dock) should ever clamp/persist a new position.
        if not self.isVisible():
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
