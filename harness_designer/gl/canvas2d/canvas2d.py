# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import canvas as _canvas


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


class Canvas2D(QtWidgets.QWidget):
    """Represent a canvas 2D in :mod:`harness_designer.gl.canvas2d.canvas2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame", config: "_config.Config.editor2d", size=None):
        """Initialise the :class:`Canvas2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor2d`
        :param size: Value for ``size``.
        :type size: UNKNOWN
        """

        QtWidgets.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._ref_count = 0

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._canvas = _canvas.Canvas(self, config)
        layout.addWidget(self._canvas)

        if size is not None:
            w, h = size
            self._canvas.resize(w, h)

        self.config = config

    def event(self, event):
        """Execute the event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return QtWidgets.QWidget.event(self, event)

    @property
    def context(self):
        """Return the context.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._canvas.context

    @property
    def camera(self):
        """Return the camera.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._canvas.camera

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._canvas.set_selected(obj)

    def set_mode(self, mode: int) -> None:
        """Set the mode.

        UNKNOWN details are inferred from the callable name and signature.

        :param mode: Value for ``mode``.
        :type mode: int
        """
        self._canvas.set_mode(mode)

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._canvas.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._canvas.remove_object(obj)

    def __enter__(self):
        """Enter the managed context.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the managed context.

        UNKNOWN details are inferred from the callable name and signature.

        :param exc_type: Value for ``exc_type``.
        :type exc_type: UNKNOWN
        :param exc_val: Value for ``exc_val``.
        :type exc_val: UNKNOWN
        :param exc_tb: Value for ``exc_tb``.
        :type exc_tb: UNKNOWN
        """
        self._ref_count -= 1

    def bind(self, signal_name: str, handler) -> None:
        """Forward signal connections to the inner QOpenGLWidget canvas."""
        getattr(self._canvas, signal_name).connect(handler)

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        if self._ref_count:
            return

        self._canvas.update()
