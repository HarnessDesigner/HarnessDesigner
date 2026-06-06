# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6 import QtWidgets

from ... import config as _config
from ...gl import canvas3d as _canvas3d


if TYPE_CHECKING:
    from .. import mainframe as _mainframe
    from ...gl.canvas3d import camera as _camera


Config = _config.Config.editor3d


class Editor3D:
    """Represent an editor 3D in :mod:`harness_designer.ui.editor_3d.editor3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`Editor3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self.editor = Editor3DPanel(mainframe)
        self.mainframe = mainframe

        mainframe._make_dock(
            title='3D Editor',
            name='editor_3d',
            widget=self.editor,
            area=Qt.DockWidgetArea.AllDockWidgetAreas,  # centre pane — set as central widget directly
        )

    @property
    def context(self):
        """Return the context.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.editor.context

    @property
    def camera(self) -> "_camera.Camera":
        """Return the camera.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Camera instance
        :rtype: :class:`harness_designer.gl.canvas3d.camera.Camera`
        """
        return self.editor.camera

    @property
    def config(self) -> _config.Config.editor3d:
        """Return the config.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_config.Config.editor3d`
        """
        return self.editor.config

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

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        self.editor.Refresh()

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


class Editor3DPanel(_canvas3d.Canvas3D):
    """Represent an editor 3dpanel in :mod:`harness_designer.ui.editor_3d.editor3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """Initialise the :class:`Editor3DPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
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

        super().__init__(parent, Config, size, True)
