# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPixmap, QPainter, QTransform, QCursor

from ... import image as _image


class ImageViewer(QWidget):

    def __init__(self, parent, img):
        QWidget.__init__(self, parent)

        self.pixmap = QPixmap(img)
        self.filename = None

        self.scale = 1.0

        self.hand_cursor = _image.cursors.hand.cursor
        self.grab_cursor = _image.cursors.grab.cursor

        self.setCursor(self.hand_cursor)

        self.coords = QPoint(0, 0)
        self.offset_x = 0
        self.offset_y = 0

        self.setMouseTracking(True)
        self._dragging = False

    def mousePressEvent(self, evt):
        if evt.button() == Qt.LeftButton and not self._dragging:
            self._dragging = True
            self.grabMouse()
            self.setCursor(self.grab_cursor)
            self.coords = evt.position().toPoint()

    def mouseReleaseEvent(self, evt):
        if evt.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.releaseMouse()
            self.setCursor(self.hand_cursor)
            self.coords = QPoint(0, 0)

    def mouseMoveEvent(self, evt):
        if self._dragging:
            pos = evt.position().toPoint()
            x1, y1 = pos.x(), pos.y()
            x2, y2 = self.coords.x(), self.coords.y()

            self.coords = pos

            diff_x = x2 - x1
            diff_y = y2 - y1
            self.offset_x += diff_x
            self.offset_y += diff_y

            w = self.pixmap.width()
            h = self.pixmap.height()
            cw = self.width()
            ch = self.height()

            if self.offset_x > 0:
                self.offset_x = 0
            elif self.offset_x < cw - w:
                self.offset_x = cw - w

            if self.offset_y > 0:
                self.offset_y = 0
            elif self.offset_y < ch - h:
                self.offset_y = ch - h

            QTimer.singleShot(0, self.update)

    def wheelEvent(self, evt):
        self.scale += evt.angleDelta().y() / 8000.0
        QTimer.singleShot(0, self.update)

    def paintEvent(self, evt):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)

        cw = self.width()
        ch = self.height()
        w = self.pixmap.width()
        h = self.pixmap.height()

        x = 0 if w >= cw else int((cw - w) / 2)
        y = 0 if h >= ch else int((ch - h) / 2)

        painter.setTransform(QTransform().scale(self.scale, self.scale))
        painter.drawPixmap(x + self.offset_x, y + self.offset_y, self.pixmap)
        painter.end()

    def closeEvent(self, evt):
        if self.filename is not None:
            os.remove(self.filename)
        evt.accept()


class PDFViewer(QWidget):

    def __init__(self, parent, pdf_file):
        QWidget.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Try native QPdfView first (Qt 6.4+), fall back to pymupdf rendering
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView

            self._doc = QPdfDocument(self)
            self._doc.load(pdf_file)

            self._view = QPdfView(self)
            self._view.setDocument(self._doc)
            self._view.setPageMode(QPdfView.PageMode.MultiPage)
            self._view.setZoomMode(QPdfView.ZoomMode.FitInView)

            # Navigation toolbar using standard Qt actions
            from PySide6.QtWidgets import QToolBar, QAction, QSpinBox, QLabel
            toolbar = QToolBar(self)
            toolbar.setMovable(False)

            self._page_spin = QSpinBox(self)
            self._page_spin.setMinimum(1)
            self._page_spin.setMaximum(max(1, self._doc.pageCount()))
            self._page_spin.valueChanged.connect(self._go_to_page)

            toolbar.addWidget(QLabel("Page:", self))
            toolbar.addWidget(self._page_spin)
            toolbar.addWidget(QLabel(f"of {self._doc.pageCount()}", self))

            act_zoom_in = QAction("Zoom In", self)
            act_zoom_in.triggered.connect(lambda: self._zoom(1.25))
            act_zoom_out = QAction("Zoom Out", self)
            act_zoom_out.triggered.connect(lambda: self._zoom(0.8))
            toolbar.addAction(act_zoom_in)
            toolbar.addAction(act_zoom_out)

            layout.addWidget(toolbar)
            layout.addWidget(self._view, 1)
            self._zoom_factor = 1.0

        except ImportError:
            # Fall back to pymupdf page rendering into a scrollable label
            self._load_with_pymupdf(pdf_file, layout)

    def _go_to_page(self, page_number):
        # QPdfView.PageNavigator is available via navigator()
        try:
            self._view.pageNavigator().jump(page_number - 1, QPoint())
        except Exception:
            pass

    def _zoom(self, factor):
        self._zoom_factor *= factor
        try:
            self._view.setZoomFactor(self._zoom_factor)
        except Exception:
            pass

    def _load_with_pymupdf(self, pdf_file, layout):
        try:
            import fitz  # pymupdf
            from PySide6.QtWidgets import QScrollArea
            from PySide6.QtGui import QImage

            doc = fitz.open(pdf_file)
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setSpacing(4)

            for page in doc:
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img = QImage(pix.samples, pix.width, pix.height,
                             pix.stride, QImage.Format.Format_RGB888)
                lbl = QLabel()
                lbl.setPixmap(QPixmap.fromImage(img))
                lbl.setAlignment(Qt.AlignCenter)
                vbox.addWidget(lbl)

            scroll.setWidget(container)
            layout.addWidget(scroll, 1)

        except ImportError:
            # Last resort: plain label
            lbl = QLabel(f"PDF viewer unavailable.\nInstall PySide6-QtPdf or pymupdf to view:\n{pdf_file}", self)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            layout.addWidget(lbl, 1)


class DatasheetViewer(QWidget):
    def __init__(self, parent, datasheet):
        QWidget.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        format_type = os.path.splitext(datasheet)[-1][1:].lower()

        if format_type == 'pdf':
            ctrl = PDFViewer(self, datasheet)
        else:
            ctrl = ImageViewer(self, datasheet)

        layout.addWidget(ctrl, 1)
