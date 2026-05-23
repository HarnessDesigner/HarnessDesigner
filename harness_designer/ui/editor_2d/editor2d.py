# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication
from PySide6 import QtWidgets

from ...gl import canvas2d as _canvas2d
from ... import config as _config


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


Config = _config.Config.editor2d


class Editor2D:
    """Represent an editor 2D in :mod:`harness_designer.ui.editor_2d.editor2d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`Editor2D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self.editor = Editor2DPanel(mainframe)
        self.mainframe = mainframe

        dock = mainframe._make_dock(
            title='Schematic Editor',
            name='editor_2d',
            widget=self.editor,
            area=None,  # Right area; _make_dock uses Qt.RightDockWidgetArea by default
        )
        self._dock = dock
        dock.show()

    def Show(self, show=True):
        """Execute the show operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param show: Value for ``show``.
        :type show: UNKNOWN
        """
        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.set_selected(obj)

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.remove_object(obj)

    def Refresh(self, *args, **kwargs):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        self.editor.update()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.editor.deleteLater()

    def bind(self, signal_name, handler):
        """Execute the bind operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param signal_name: Value for ``signal_name``.
        :type signal_name: UNKNOWN
        :param handler: Value for ``handler``.
        :type handler: UNKNOWN
        """
        self.editor.bind(signal_name, handler)

    def set_clone_obj(self, obj):
        """Set the clone obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.set_clone_obj(obj)


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
