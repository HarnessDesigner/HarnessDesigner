from typing import TYPE_CHECKING

from PySide6 import QtWidgets

if TYPE_CHECKING:
    from . import mainframe as _mainframe


_DefaultFeatures = (QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetClosable |
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                    QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)


class DockBase:

    _ui_obj = None

    def __init__(self, mainframe: "_mainframe.MainFrame", title: str,
                 name: str, area=None, features=_DefaultFeatures):

        self.mainframe = mainframe

        self._dock = mainframe.make_dock(title=title, name=name,
                                         widget=self._ui_obj, area=area)

        self._dock.setFeatures(features)
        self._dock.show()

    @property
    def dock(self):
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
