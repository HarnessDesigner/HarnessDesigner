# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A label for text the application does not control -- a page's address, a
server's answer, a script's name -- that can never make its window wider.
"""

from PySide6 import QtCore
from PySide6 import QtWidgets

from ... import check_types as _check_types

# Text longer than this also goes into the tooltip, where all of it is shown.
_TOOLTIP_FROM = 60

# The widths the label asks its layout for however long its text is; the layout can still give it more.
_PREFERRED_WIDTH = 400
_MINIMUM_WIDTH = 40


class WrapLabel(QtWidgets.QLabel):
    """A plain ``QLabel`` asks its layout for a minimum width equal to its
    longest unbreakable word, so one 1,100-character address in a message
    made the whole main window 5,800 pixels wide (a Google search link).
    This one asks for almost nothing: text that does not fit wraps at its
    spaces (when *wrap* is true) and any word still too long is cut off at
    the edge. The full text is the tooltip.

    The text is always shown as plain text -- an address must never be
    read as markup.
    """

    @_check_types.do
    def __init__(self, text: str = '', parent: QtWidgets.QWidget | None = None, wrap: bool = True) -> None:
        """
        :param text: What to show to begin with.
        :param wrap: Wrap at spaces (``True``) or keep to one line.
        """
        super().__init__(parent)
        self.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.setWordWrap(wrap)
        self.setText(text)

    @_check_types.do
    def sizeHint(self) -> QtCore.QSize:  # NOQA -- Qt override
        """Never more than ``_PREFERRED_WIDTH`` wide: a dock sizes itself from
        its contents' size hints, so a long message would otherwise make the
        dock take most of the window."""
        hint = super().sizeHint()
        return QtCore.QSize(min(hint.width(), _PREFERRED_WIDTH), hint.height())

    @_check_types.do
    def minimumSizeHint(self) -> QtCore.QSize:  # NOQA -- Qt override
        """Never more than ``_MINIMUM_WIDTH`` wide, which is what keeps a long
        address from setting the minimum width of everything around it."""
        hint = super().minimumSizeHint()
        return QtCore.QSize(min(hint.width(), _MINIMUM_WIDTH), hint.height())

    @_check_types.do
    def setText(self, text: str) -> None:  # NOQA -- Qt override
        super().setText(text)
        tip = ''
        if len(text) > _TOOLTIP_FROM:
            tip = text

        self.setToolTip(tip)
