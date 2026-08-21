# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication
from PySide6 import QtCore

from ...gl import canvas_pegboard as _canvas_pegboard
from ...objects.objects_pegboard import base_pegboard as _base_pegboard
from ... import config as _config
from .. import dock_base as _dock_base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor_pegboard


class EditorPegboard(_dock_base.DockBase):
    """
    Represent a peg board editor in
    :mod:`harness_designer.ui.editor_pegboard.editor_pegboard`.

    Structural mirror of :class:`harness_designer.ui.editor_2d.editor2d.Editor2D`
    -- same dock-creation shape and same thin forwarding methods, so
    :class:`harness_designer.ui.mainframe.MainFrame`'s existing per-editor
    fan-out pattern can treat this editor uniformly alongside ``editor2d``
    and ``editor3d`` without special-casing it.
    """

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorPegboard` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = EditorPegboardPanel(mainframe)

        super().__init__(mainframe, 'Pegboard Editor', 'editor_pegboard',
                         QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

    @property
    @_check_types.do
    def context(self):
        """Return the GL context manager owned by the inner canvas.

        Mirrors ``ui.editor_3d.editor3d.Editor3D.context`` -- needed by
        ``objects.objects_pegboard.base_pegboard.BasePegboard._set_model``'s
        ``self.pegboard.context.acquire()``/``.release()`` calls, which
        otherwise have nowhere to resolve to.

        :returns: Property value.
        :rtype: UNKNOWN
        """
        return self._ui_obj.context

    @property
    @_check_types.do
    def camera(self):
        """Return the camera owned by the inner canvas.

        Mirrors ``ui.editor_3d.editor3d.Editor3D.camera``.

        :returns: Property value.
        :rtype: UNKNOWN
        """
        return self._ui_obj.camera

    @_check_types.do
    def set_selected(self, obj):
        """
        Set the selected.

        Forwards to :class:`EditorPegboardPanel`'s ``set_selected`` so
        callers (``mainframe._set_selected``) can treat this editor the
        same as ``editor2d``/``editor3d`` without special-casing.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.set_selected(obj)

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.

        Incremental now -- forwards to :class:`EditorPegboardPanel`, which
        registers ``obj.objpegboard`` with the inner ``Canvas`` (skipping every
        type that isn't a real, active anchor).

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.

        Incremental now -- forwards to :class:`EditorPegboardPanel`, which
        unregisters ``obj.objpegboard`` from the inner ``Canvas`` (skipping every
        type that isn't a real, active anchor).

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.remove_object(obj)

    @_check_types.do
    def bind(self, signal_name, handler):
        """
        Execute the bind operation.

        :param signal_name: Value for ``signal_name``.
        :type signal_name: UNKNOWN
        :param handler: Value for ``handler``.
        :type handler: UNKNOWN
        """

        self._ui_obj.bind(signal_name, handler)

    @_check_types.do
    def set_clone_obj(self, obj):
        """
        Set the clone obj.

        Phase 1 has no clone/paste model for the peg board -- forwards to
        :class:`EditorPegboardPanel`'s no-op stub.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.set_clone_obj(obj)

    @_check_types.do
    def clear(self) -> None:
        """
        Drop every anchor/strand in bulk, without touching the database.

        See :meth:`harness_designer.gl.canvas_pegboard.canvas.Canvas.clear`.
        """

        self._ui_obj.clear()

    @property
    @_check_types.do
    def editor(self) -> "EditorPegboardPanel":
        return self._ui_obj


class EditorPegboardPanel(_canvas_pegboard.CanvasPegboard):
    """
    Represent a peg board editor panel in
    :mod:`harness_designer.ui.editor_pegboard.editor_pegboard`.

    Structural mirror of
    :class:`harness_designer.ui.editor_2d.editor2d.Editor2DPanel` -- same
    virtual-canvas auto-sizing logic, reading from
    ``Config.editor_pegboard.virtual_canvas`` instead of
    ``Config.editor_schematic.virtual_canvas``.
    """

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`EditorPegboardPanel` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        if not Config.virtual_canvas.width or not Config.virtual_canvas.height:
            max_x = 0
            max_y = 0
            min_x = 0
            min_y = 0
            for screen in QApplication.screens():
                geo = screen.geometry()
                x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()
                max_x = max(x + w, max_x)
                max_y = max(y + h, max_y)
                min_x = min(x, min_x)
                min_y = min(y, min_y)

            width = max_x - min_x
            height = int(width / 1.777777)

            Config.virtual_canvas.width = width
            Config.virtual_canvas.height = height

        size = (Config.virtual_canvas.width,
                Config.virtual_canvas.height)

        super().__init__(parent, Config, size)

    @_check_types.do
    def set_selected(self, obj):
        """
        Repaint so the peg board's selection highlight picks up a
        cross-editor selection change.

        The inner ``Canvas``'s ``_render_scene`` derives highlight state
        live from each anchor's ``anchor.obj.is_selected`` on every frame
        (see ``gl.canvas_pegboard.canvas.Canvas._render_scene`` and
        ``gl.canvas_pegboard.mouse_handler._find_selected_anchor``), so no
        bookkeeping is needed here -- just a repaint, since Qt won't
        repaint on its own just because some unrelated Python attribute
        (``ObjectBase._is_selected``) changed elsewhere.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._canvas.update()

    @_check_types.do
    def add_object(self, obj):
        """
        Register *obj*'s peg-board anchor with the inner canvas, if it has
        a real, active one.

        Every :class:`~harness_designer.objects.object_base.ObjectBase`
        subclass has its own dedicated
        :class:`~harness_designer.objects.objects_pegboard.base_pegboard.BasePegboard`
        subclass (never a shared stub), but most construct it with
        ``vbo=None`` -- inert, ``is_active`` is ``False`` -- so this just
        skips those, matching
        :meth:`harness_designer.gl.canvas_pegboard.canvas.Canvas._collect_anchors`'s
        own gate.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._canvas.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Unregister *obj*'s peg-board anchor from the inner canvas, if it
        has a real, active one.

        Skips every inactive anchor (see :meth:`add_object`).

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._canvas.remove_object(obj)

    @_check_types.do
    def set_clone_obj(self, obj):
        """
        No-op: Phase 1 has no clone/paste model for the peg board yet.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        pass

    @_check_types.do
    def clear(self) -> None:
        """
        Forward to the inner GL canvas's bulk teardown.

        See :meth:`harness_designer.gl.canvas_pegboard.canvas.Canvas.clear`.
        """
        self._canvas.clear()

    @_check_types.do
    def center_on_object(self, obj) -> None:
        """
        Pan the peg board camera to bring *obj* into view, without
        changing zoom -- mirrors
        ``mainframe.MainFrame._set_selected``'s direct
        ``editor3d.camera.CenterOn(obj.obj3d.position)`` call for the 3D
        view, forwarded here (rather than exposed as a raw ``.camera``
        call at the mainframe level) since the peg board's own anchor
        position lives on ``obj.objpegboard``, not on ``obj`` itself.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        if obj.objpegboard is not None:
            self.camera.CenterOn(obj.objpegboard.position)
