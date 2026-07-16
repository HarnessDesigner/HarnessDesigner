from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore

if TYPE_CHECKING:
    from . import mainframe as _mainframe


_DefaultFeatures = (QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable |
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)


class DockWidget(QtWidgets.QDockWidget):

    def Raise(self):
        self.raise_()

    def Show(self, flag=True):
        if flag:
            self.show()
            self.raise_()

        else:
            self.hide()


class DockBase:

    _ui_obj = None

    def __init__(self, mainframe: "_mainframe.MainFrame", title: str,
                 name: str, area: QtCore.Qt.DockWidgetArea = None,
                 features: QtWidgets.QDockWidget.DockWidgetFeature = _DefaultFeatures):

        self.mainframe = mainframe

        self._dock = DockWidget(title, mainframe)

        self._dock.setObjectName(name)
        self._dock.setWindowTitle(title)
        self._dock.setWidget(self._ui_obj)
        self._dock.setFeatures(features)
        self._dock.Show()

        if area is None:
            area = QtCore.Qt.DockWidgetArea.RightDockWidgetArea

        mainframe.addDockWidget(area, self._dock)

    @property
    def dock(self) -> DockWidget:
        """
        Returns the underlying QT dock object
        """

        return self._dock

    def IsShown(self) -> bool:
        """
        Execute the is shown operation.

        :rtype: bool
        """

        return self._dock.isVisible()

    def Show(self, show=True) -> None:
        """
        Show or hide the 3D editor's dock (does not close it — see the
        ``DockWidgetClosable`` feature stripped in ``__init__``).

        :param show: Value for ``show``.
        :type show: bool
        """

        if show:
            self._dock.show()
            self._dock.raise_()
        else:
            self._dock.hide()

    def Refresh(self, *_, **__) -> None:
        """
        Execute the refresh operation.
        """

        self._ui_obj.Refresh()

    def Destroy(self) -> None:
        """
        Execute the destroy operation.
        """

        self._ui_obj.deleteLater()
