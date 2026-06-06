# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Generic Error Dialog for PySide6 applications.

Usage:
    from error_dialog import ErrorDialog

    # Simple usage
    ErrorDialog.show_error(parent, "Something went wrong.")

    # With title and details
    ErrorDialog.show_error(
        parent,
        message="Failed to load file.",
        title="File Error",
        details="Traceback (most recent call last):\n  ...",
    )

    # With extra widgets (parentless widgets are reparented to the dialog)
    retry_cb = QCheckBox("Retry automatically")   # no parent
    log_cb   = QCheckBox("Write to log file")     # no parent
    ErrorDialog.show_error(
        parent,
        message="Export failed.",
        extra_widgets=[retry_cb, log_cb],
    )

    # As an instance
    dlg = ErrorDialog(parent, message="Oops!", title="Error", details="...")
    dlg.exec()
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class ErrorDialog(QtWidgets.QDialog):
    """
    A generic, reusable error dialog.

    :param parent: Parent widget, typically the mainframe.
    :type parent: QWidget

    :param message: The primary error message shown to the user.
    :type message: str

    :param title: Window title.
    :type title: str

    :param widgets: Optional parentless widgets to embed after the message
                    Each widget is reparented to this dialog automatically
                    when it is added to the layout.
    :type widgets: tuple[QWidget]
    """

    def __init__(self, parent, message: str, title: str,
                 *widgets: tuple[QtWidgets.QWidget]) -> None:
        """Initialise the :class:`ErrorDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param message: Value for ``message``.
        :type message: str
        :param title: Value for ``title``.
        :type title: str
        :param widgets: Value for ``widgets``.
        :type widgets: tuple[QtWidgets.QWidget]
        """

        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setWindowFlags(
            self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)

        self._widgets = widgets

        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # ── Icon + message row ──────────────────────────────────────────
        top_row = QtWidgets.QHBoxLayout()
        top_row.setSpacing(14)

        icon_label = QtWidgets.QLabel()
        icon = self.style().StandardPixmap.SP_MessageBoxCritical
        icon = self.style().standardIcon(icon).pixmap(40, 40)
        icon_label.setPixmap(icon)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        icon_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,
                                 QtWidgets.QSizePolicy.Policy.Fixed)

        top_row.addWidget(icon_label)

        msg_label = QtWidgets.QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        font = QtGui.QFont()
        font.setPointSize(10)
        msg_label.setFont(font)
        top_row.addWidget(msg_label, stretch=1)

        root.addLayout(top_row)

        # ── caller-supplied widgets ─────────────────────────────────────
        # Adding a widget to a layout reparents it to the layout's parent
        # widget (this dialog), so callers can pass in parentless widgets.
        for widget in widgets:
            root.addWidget(widget)

        # ── Button row ──────────────────────────────────────────────────
        btn_row = QtWidgets.QHBoxLayout()

        btn_row.addSpacerItem(
            QtWidgets.QSpacerItem(
                0, 0, QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Minimum))

        ok_btn = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok)

        ok_btn.accepted.connect(self.accept)
        btn_row.addWidget(ok_btn)

        root.addLayout(btn_row)
