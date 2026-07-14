# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from ...gl import canvas_pegboard as _canvas_pegboard
from ... import config as _config
from .. import dock_base as _dock_base


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor_pegboard


class EditorPegBoard(_dock_base.DockBase):
    """
    Represent a peg board editor in
    :mod:`harness_designer.ui.editor_pegboard.editor_pegboard`.

    Structural mirror of :class:`harness_designer.ui.editor_2d.editor2d.Editor2D`
    -- same dock-creation shape and same thin forwarding methods, so
    :class:`harness_designer.ui.mainframe.MainFrame`'s existing per-editor
    fan-out pattern can treat this editor uniformly alongside ``editor2d``
    and ``editor3d`` without special-casing it.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorPegBoard` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = EditorPegBoardPanel(mainframe)

        super().__init__(mainframe, 'Peg Board Editor', 'editor_pegboard')

    def set_selected(self, obj):
        """
        Set the selected.

        Forwards to :class:`EditorPegBoardPanel`'s ``set_selected`` so
        callers (``mainframe._set_selected``) can treat this editor the
        same as ``editor2d``/``editor3d`` without special-casing.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.set_selected(obj)

    def add_object(self, obj):
        """
        Add an object.

        Phase 1 rebuilds the peg board's anchor list wholesale via
        :meth:`load_project` rather than incrementally -- forwards to
        :class:`EditorPegBoardPanel`'s no-op stub.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.add_object(obj)

    def remove_object(self, obj):
        """
        Remove the object.

        Phase 1 rebuilds the peg board's anchor list wholesale via
        :meth:`load_project` rather than incrementally -- forwards to
        :class:`EditorPegBoardPanel`'s no-op stub.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.remove_object(obj)

    def bind(self, signal_name, handler):
        """
        Execute the bind operation.

        :param signal_name: Value for ``signal_name``.
        :type signal_name: UNKNOWN
        :param handler: Value for ``handler``.
        :type handler: UNKNOWN
        """

        self._ui_obj.bind(signal_name, handler)

    def set_clone_obj(self, obj):
        """
        Set the clone obj.

        Phase 1 has no clone/paste model for the peg board -- forwards to
        :class:`EditorPegBoardPanel`'s no-op stub.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.set_clone_obj(obj)

    def load_project(self, project) -> None:
        """
        Rebuild the peg board's full static anchor list from *project*.

        Unlike ``editor2d`` (which builds its scene incrementally via
        ``add_object``), the peg board's Phase 1 render is a bulk rebuild --
        forwards to :meth:`harness_designer.gl.canvas_pegboard.canvas.Canvas.load_project`
        via :class:`EditorPegBoardPanel`.

        :param project: The currently open project.
        :type project: :class:`harness_designer.objects.project.Project`
        """

        self._ui_obj.load_project(project)

    @property
    def editor(self) -> "EditorPegBoardPanel":
        return self._ui_obj


class EditorPegBoardPanel(_canvas_pegboard.CanvasPegBoard):
    """
    Represent a peg board editor panel in
    :mod:`harness_designer.ui.editor_pegboard.editor_pegboard`.

    Structural mirror of
    :class:`harness_designer.ui.editor_2d.editor2d.Editor2DPanel` -- same
    virtual-canvas auto-sizing logic, reading from
    ``Config.editor_pegboard.virtual_canvas`` instead of
    ``Config.editor2d.virtual_canvas``.
    """

    def __init__(self, parent):
        """Initialise the :class:`EditorPegBoardPanel` instance.

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

    def set_selected(self, obj):
        """
        Repaint so the peg board's selection highlight picks up a
        cross-editor selection change.

        The inner ``Canvas``'s ``_render_objects`` derives highlight state
        live from each anchor's ``anchor.obj.is_selected`` on every frame
        (see ``gl.canvas_pegboard.canvas.Canvas._render_objects`` and
        ``gl.canvas_pegboard.mouse_handler._find_selected_anchor``), so no
        bookkeeping is needed here -- just a repaint, since Qt won't
        repaint on its own just because some unrelated Python attribute
        (``ObjectBase._is_selected``) changed elsewhere.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._canvas.update()

    def add_object(self, obj):
        """
        No-op: Phase 1 rebuilds the anchor list wholesale via
        :meth:`load_project` rather than incrementally.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        pass

    def remove_object(self, obj):
        """
        No-op: Phase 1 rebuilds the anchor list wholesale via
        :meth:`load_project` rather than incrementally.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        pass

    def set_clone_obj(self, obj):
        """
        No-op: Phase 1 has no clone/paste model for the peg board yet.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        pass

    def load_project(self, project) -> None:
        """
        Forward to the inner GL canvas's full anchor-list rebuild.

        :param project: The currently open project.
        :type project: :class:`harness_designer.objects.project.Project`
        """
        self._canvas.load_project(project)
