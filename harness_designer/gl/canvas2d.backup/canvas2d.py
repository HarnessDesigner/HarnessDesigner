# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

from . import canvas as _canvas
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ... import config as _config


# baseclass for schematic editor and pegboard editor
class Canvas2D(QtWidgets.QWidget):
    """Represent a canvas 2D in :mod:`harness_designer.gl.canvas2d.canvas2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    # this needs to be duplicated in the subclasses except we need to change the
    # type to the correct canvas type being used
    #
    # String (forward-ref) annotation -- not just style: the attribute name
    # and the imported module's alias are both "_canvas", so a live
    # (non-string) annotation here resolves the module reference against
    # this not-yet-assigned class attribute instead of the actual module,
    # raising AttributeError: 'NoneType' object has no attribute 'Canvas'
    # at class-definition time.
    _canvas: "_canvas.Canvas" = None

    # this also needs to be duplicated in the subclass and it also needs to
    # have it's type set correctly
    config = None

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", config, size=None):
        """Initialise the :class:`Canvas2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param config: Value for ``config``.
        :type config: :class:`_config.Config.editor2d`
        :param size: Value for ``size``.
        :type size: UNKNOWN
        """

        self.config = config

        QtWidgets.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._ref_count = 0

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # `parent` here is the real MainFrame (Canvas2D's own constructor
        # contract, see the type hint above) -- passed straight through
        # so the inner Canvas doesn't need to rediscover it by walking
        # the Qt parent chain.
        # This code needs to be added to the sublcass so the correct canvas
        # can be intiilized.. the canvas should be initilized before
        # super().__init__ is called so the _canvas attribute will be properly
        # set

        # self._canvas = _canvas.Canvas(self, parent, config)

        layout.addWidget(self._canvas)

        if size is not None:
            w, h = size
            self._canvas.resize(w, h)

    @_check_types.do
    def center_on_object(self, obj) -> None:
        """Forward to the inner canvas's pan-to-object.

        :param obj: The wrapper whose anchor should be centered.
        :type obj: :class:`harness_designer.objects.object_base.ObjectBase`
        """
        self._canvas.center_on_object(obj)

    @_check_types.do
    def event(self, event):
        """
        Execute the event operation.

        :param event: Event object.
        :type event: UNKNOWN

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        return QtWidgets.QWidget.event(self, event)

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

    @_check_types.do
    def set_selected(self, obj):
        """
        Set the selected.
        """

        self._canvas.set_selected(obj)

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.
        """

        self._canvas.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.
        """

        self._canvas.remove_object(obj)

    @_check_types.do
    def clear(self) -> None:
        """
        Drop every scene object in bulk, without touching the database.

        See :meth:`harness_designer.gl.canvas2d.canvas.Canvas.clear`.
        """

        self._canvas.clear()

    @_check_types.do
    def __enter__(self):
        self._ref_count += 1
        return self

    @_check_types.do
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1

    @_check_types.do
    def bind(self, signal_name: str, handler) -> None:
        """Forward signal connections to the inner QOpenGLWidget canvas."""
        getattr(self._canvas, signal_name).connect(handler)

    @_check_types.do
    def Refresh(self, *_, **__):
        if self._ref_count:
            return

        self._canvas.update()
