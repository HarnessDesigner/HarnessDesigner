# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from ...gl import canvas2d as _canvas2d
from ... import config as _config
from .. import dock_base as _dock_base


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor2d


class Editor2D(_dock_base.DockBase):
    """Represent an editor 2D in :mod:`harness_designer.ui.editor_2d.editor2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`Editor2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = Editor2DPanel(mainframe)
        super().__init__(mainframe, 'Schematic Editor', 'editor_2d')

    @property
    def editor(self) -> "Editor2DPanel":
        return self._ui_obj

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._ui_obj.set_selected(obj)

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._ui_obj.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._ui_obj.remove_object(obj)

    def bind(self, signal_name, handler):
        """Execute the bind operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param signal_name: Value for ``signal_name``.
        :type signal_name: UNKNOWN
        :param handler: Value for ``handler``.
        :type handler: UNKNOWN
        """
        self._ui_obj.bind(signal_name, handler)

    def set_clone_obj(self, obj):
        """Set the clone obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._ui_obj.set_clone_obj(obj)


class Editor2DPanel(_canvas2d.Canvas2D):
    """Represent an editor 2dpanel in :mod:`harness_designer.ui.editor_2d.editor2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`Editor2DPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

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
