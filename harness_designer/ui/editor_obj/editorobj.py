# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtWidgets

from .. import dock_base as _dock_base


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class EditorObj(_dock_base.DockBase):
    """Represent an editor obj in :mod:`harness_designer.ui.editor_obj.editorobj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`EditorObj` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self._ui_obj = EditorObjPanel(mainframe)

        super().__init__(mainframe, 'Object Editor', 'editor_obj',
                         QtCore.Qt.DockWidgetArea.RightDockWidgetArea)

    def _on_visibility_changed(self, visible):
        """Handle the visibility changed event.

        UNKNOWN details are inferred from the callable name and signature.

        :param visible: Value for ``visible``.
        :type visible: UNKNOWN
        """
        if not visible:
            self.set_selected(None)

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        QtWidgets.QApplication.setOverrideCursor(
            QtCore.Qt.CursorShape.WaitCursor)
        try:
            self._ui_obj.set_selected(obj)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

    @property
    def editor(self) -> "EditorObjPanel":
        return self._ui_obj


class EditorObjPanel(QtWidgets.QWidget):
    """
    Represent an editor obj panel in :mod:`harness_designer.ui.editor_obj.editorobj`.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """
        Initialise the :class:`EditorObjPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """

        super().__init__(parent)
        self.mainframe = parent
        self.control = None

        vsizer = QtWidgets.QVBoxLayout(self)
        hsizer = QtWidgets.QHBoxLayout()
        vsizer.addLayout(hsizer)

        self.sizer = hsizer
        self._selected = None

    def set_selected(self, obj):
        """
        Set the selected.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        if obj is None:
            if self.control is not None:
                self.control.hide()
                self.sizer.removeWidget(self.control)
                self.control.setParent(self.mainframe)
                self.control = None
        else:
            control = obj.db_obj.table.control
            control.set_obj(obj.db_obj)
            control.setParent(self)

            if self.control is not None:
                self.control.hide()
                self.sizer.removeWidget(self.control)
                self.control.setParent(self.mainframe)

            self.sizer.addWidget(control, 1)
            # Qt does not have wx.EXPAND|wx.ALL; margins go on the layout
            self.sizer.setContentsMargins(10, 10, 10, 10)
            self.control = control
            control.show()

        self.updateGeometry()
        self.update()

        self._selected = obj
