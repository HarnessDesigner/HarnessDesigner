# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import header as _header

if TYPE_CHECKING:
    from ... import ui as _ui


class BaseDialog(QtWidgets.QDialog):
    """Represent a base dialog in :mod:`harness_designer.ui.dialogs.dialog_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame", title: str, size=(-1, -1),
                 style=None, button_ids=None):
        """Initialise the :class:`BaseDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param title: Value for ``title``.
        :type title: str
        :param size: Value for ``size``.
        :type size: UNKNOWN
        :param style: Value for ``style``.
        :type style: UNKNOWN
        :param button_ids: Identifier for the button.
        :type button_ids: UNKNOWN
        """

        self.mainframe = parent
        self._drag_pos = None

        flags = (QtCore.Qt.WindowType.Dialog |
                 QtCore.Qt.WindowType.WindowStaysOnTopHint |
                 QtCore.Qt.WindowType.CustomizeWindowHint)

        if style is not None:
            flags |= style

        super().__init__(parent, flags)

        self.setMaximumWidth(1920)
        self.setMouseTracking(True)

        w, h = size

        if w < 0:
            w = self.sizeHint().width()
        if h < 0:
            h = self.sizeHint().height()

        self.panel = QtWidgets.QWidget(self)
        self.header = _header.Header(self, title, size=(w, h))

        if button_ids is None:
            button_ids = (QtWidgets.QDialogButtonBox.StandardButton.Ok |
                          QtWidgets.QDialogButtonBox.StandardButton.Cancel)

        self.button_box = QtWidgets.QDialogButtonBox(button_ids, parent=self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        sep = QtWidgets.QFrame(self)
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        root = QtWidgets.QVBoxLayout(self)

        root.setContentsMargins(5, 0, 5, 10)
        root.setSpacing(0)
        root.addWidget(self.header)
        root.addSpacing(5)
        root.addWidget(self.panel, 1)
        root.addSpacing(5)
        root.addWidget(sep)
        root.addSpacing(5)
        root.addWidget(self.button_box)

        self.resize(w, h)
        self._center_on_parent()

    def _center_on_parent(self):
        """Center this dialog on its parent window.

        If the parent is positioned such that centering on it would push
        any part of the dialog outside the visible area of the screen the
        parent is mostly displayed on (e.g. the main window was dragged
        mostly off-screen before the app was closed), center on that
        screen instead -- otherwise the dialog itself would open
        off-screen, and since it's modal there would be no way to move it
        or the parent back into view without editing the saved window
        position directly in the database.
        """
        if self.parent() is None:
            return

        parent_geo = self.parent().frameGeometry()
        geo = self.frameGeometry()
        geo.moveCenter(parent_geo.center())

        screen = self.parent().screen()
        if screen is not None and not screen.availableGeometry().contains(geo):
            geo.moveCenter(screen.availableGeometry().center())

        self.move(geo.topLeft())

    def _in_drag_zone(self, pos: QtCore.QPoint) -> bool:  # NOQA
        """Execute the in drag zone operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param pos: Value for ``pos``.
        :type pos: :class:`QtCore.QPoint`
        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return pos.y() < 10

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Execute the mouse move event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QtGui.QMouseEvent`
        """
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        elif self._in_drag_zone(event.position().toPoint()):
            self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        else:
            self.unsetCursor()

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Execute the mouse press event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QtGui.QMouseEvent`
        """
        if (event.button() == QtCore.Qt.MouseButton.LeftButton and
                self._in_drag_zone(event.position().toPoint())):
            self._drag_pos = event.globalPosition().toPoint()
            self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Execute the mouse release event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QtGui.QMouseEvent`
        """
        if self._drag_pos is not None:
            self._drag_pos = None
            self.unsetCursor()

        super().mouseReleaseEvent(event)

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError
