# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import canvas as _canvas
from ... import config as _config


if TYPE_CHECKING:
    from ... import ui as _ui


class CanvasPegBoard(QtWidgets.QWidget):
    """Outer ``QWidget`` hosting the peg board editor's inner
    ``QOpenGLWidget`` (:class:`harness_designer.gl.canvas_pegboard.canvas.Canvas`).

    Mirrors :class:`harness_designer.gl.canvas2d.canvas2d.Canvas2D`'s wrapper
    role (owns the layout, hosts the inner GL widget, forwards
    context/camera/bind/Refresh). One difference: ``Canvas2D`` itself does
    NOT size from ``Config.editor2d.virtual_canvas`` -- that fallback lives
    one layer up, in ``ui/editor_2d/editor2d.py``'s ``Editor2DPanel``
    (which also auto-detects a size from screen geometry the first time
    ``virtual_canvas`` is unset). Since the peg board dock
    (``ui/editor_pegboard/``) is a separate, later task, the
    ``virtual_canvas``-driven default is folded into ``CanvasPegBoard``
    itself here so this package is runnable/testable standalone without
    that dock layer existing yet.
    """

    def __init__(self, parent: "_ui.MainFrame",
                 config: "_config.Config.editor_pegboard" = None, size=None):
        """Initialise the :class:`CanvasPegBoard` instance.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param config: Peg board editor config section. Defaults to
            ``Config.editor_pegboard``.
        :type config: :class:`_config.Config.editor_pegboard`
        :param size: Optional ``(width, height)`` tuple. Defaults to
            ``Config.editor_pegboard.virtual_canvas.width/height``.
        :type size: UNKNOWN
        """

        QtWidgets.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._ref_count = 0

        if config is None:
            config = _config.Config.editor_pegboard

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = _canvas.Canvas(self, config)
        layout.addWidget(self._canvas)

        if size is None:
            size = (config.virtual_canvas.width, config.virtual_canvas.height)

        if size is not None:
            w, h = size
            self._canvas.resize(w, h)

        self.config = config

    def event(self, event):
        """Execute the event operation.

        :param event: Event object.
        :type event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return QtWidgets.QWidget.event(self, event)

    @property
    def context(self):
        """Return the GL context manager owned by the inner canvas.

        :returns: Property value.
        :rtype: UNKNOWN
        """
        return self._canvas.context

    @property
    def camera(self):
        """Return the camera owned by the inner canvas.

        :returns: Property value.
        :rtype: UNKNOWN
        """
        return self._canvas.camera

    def center_on_object(self, obj) -> None:
        """Forward to the inner canvas's pan-to-object.

        :param obj: The wrapper whose anchor should be centered.
        :type obj: :class:`harness_designer.objects.object_base.ObjectBase`
        """
        self._canvas.center_on_object(obj)

    def __enter__(self):
        """Enter the managed context."""
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        :param exc_type: Exception type, if any.
        :type exc_type: UNKNOWN
        :param exc_val: Exception value, if any.
        :type exc_val: UNKNOWN
        :param exc_tb: Exception traceback, if any.
        :type exc_tb: UNKNOWN
        """
        self._ref_count -= 1

    def bind(self, signal_name: str, handler) -> None:
        """Forward signal connections to the inner QOpenGLWidget canvas."""
        getattr(self._canvas, signal_name).connect(handler)

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        :param _: Unused positional arguments.
        :type _: UNKNOWN
        :param __: Unused keyword arguments.
        :type __: UNKNOWN
        """
        if self._ref_count:
            return

        self._canvas.update()
