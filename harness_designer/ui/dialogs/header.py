# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys

from PySide6 import QtWidgets
from PySide6 import QtGui

from ... import image as _image


class Header(QtWidgets.QWidget):
    """Represent a header in :mod:`harness_designer.ui.dialogs.header`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, label, size):
        """Initialise the :class:`Header` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        :param size: Value for ``size``.
        :type size: UNKNOWN
        """
        super().__init__(parent)
        self.setMaximumWidth(1920)
        self.setMinimumWidth(200)

        self.setMaximumHeight(80)
        self.setMinimumHeight(80)

        self.setFrameShape = lambda *a: None  # compat stub

        # Load the header pixmap from the image module.
        # _image.images.header is expected to expose .pixmap (a QPixmap)
        # as converted in the image module. Fall back gracefully if not yet
        # converted.
        self.full_header = _image.images.header
        w = size[0]

        if w > 0:
            img = self.full_header.crop(0, 0, w, 80)
        else:
            img = self.full_header

        base_pixmap = QtGui.QPixmap(img.pixmap)

        self.label = label

        # Composite the label text onto a copy of the base pixmap.
        pixmap = self._render_bitmap(base_pixmap)

        self.bitmap = QtWidgets.QLabel(self)
        self.bitmap.setPixmap(pixmap)
        if sys.platform.startswith('win'):
            self.bitmap.setFrameShape(QtWidgets.QFrame.Shape.WinPanel)
        else:
            self.bitmap.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

        self.bitmap.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.bitmap.setLineWidth(4)

        header_sizer = QtWidgets.QHBoxLayout()
        header_sizer.addWidget(self.bitmap, 1)

        sizer = QtWidgets.QVBoxLayout(self)
        sizer.addLayout(header_sizer)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Execute the resize event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: :class:`QtGui.QResizeEvent`
        """
        QtWidgets.QWidget.resizeEvent(self, event)

        size = self.size()
        w = size.width()
        h = size.height()

        img = self.full_header.crop(0, 0, w, h)
        base_pixmap = QtGui.QPixmap(img.pixmap)
        pixmap = self._render_bitmap(base_pixmap)
        self.bitmap.setPixmap(pixmap)
        self.update()

    def _render_bitmap(self, base_pixmap):
        """Render the bitmap.

        UNKNOWN details are inferred from the callable name and signature.

        :param base_pixmap: Value for ``base_pixmap``.
        :type base_pixmap: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        # Find the best font size so the label fits in roughly 273x25 px.
        font = QtGui.QFont(self.font())
        font.setItalic(True)

        for size in range(6, 48):
            font.setPointSize(size)
            fm = QtGui.QFontMetrics(font)
            r = fm.boundingRect(self.label)

            if r.width() > 273 or r.height() > 30:
                font.setPointSize(max(6, size - 1))
                break

        pixmap = QtGui.QPixmap(base_pixmap)
        painter = QtGui.QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(12, 12 + QtGui.QFontMetrics(font).ascent(), self.label)
        painter.end()

        return pixmap
