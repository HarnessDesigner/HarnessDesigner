# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QFontMetrics
from PySide6.QtCore import Qt

from ... import image as _image


class Header(QWidget):

    def __init__(self, parent, label):
        super().__init__(parent)
        self.setFrameShape = lambda *a: None  # compat stub

        # Load the header pixmap from the image module.
        # _image.images.header is expected to expose .pixmap (a QPixmap)
        # as converted in the image module. Fall back gracefully if not yet
        # converted.
        src = _image.images.header
        if hasattr(src, 'pixmap'):
            base_pixmap = QPixmap(src.pixmap)
        else:
            # image module not yet converted - create a solid-colour stand-in
            base_pixmap = QPixmap(300, 40)
            base_pixmap.fill(QColor(220, 230, 240))

        # Find the best font size so the label fits in roughly 273x25 px.
        font = QFont(self.font())
        font.setItalic(True)
        for size in range(6, 32):
            font.setPointSize(size)
            fm = QFontMetrics(font)
            r = fm.boundingRect(label)
            if r.width() > 273 or r.height() > 25:
                font.setPointSize(max(6, size - 1))
                break

        # Composite the label text onto a copy of the base pixmap.
        pixmap = QPixmap(base_pixmap)
        painter = QPainter(pixmap)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(12, 6 + QFontMetrics(font).ascent(), label)
        painter.end()

        lbl = QLabel(self)
        lbl.setPixmap(pixmap)
        lbl.setFixedSize(pixmap.size())
        self.setFixedSize(pixmap.size())
