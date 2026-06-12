# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QPixmap, QPainter, QTransform, QCursor

from ... import image as _image


class ImageViewer(QWidget):
    """Represent an image viewer in :mod:`harness_designer.ui.datasheet_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, img):
        """Initialise the :class:`ImageViewer` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param img: Value for ``img``.
        :type img: UNKNOWN
        """
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
        """Execute the mouse press event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        if evt.button() == Qt.LeftButton and not self._dragging:
            self._dragging = True
            self.grabMouse()
            self.setCursor(self.grab_cursor)
            self.coords = evt.position().toPoint()

    def mouseReleaseEvent(self, evt):
        """Execute the mouse release event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        if evt.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.releaseMouse()
            self.setCursor(self.hand_cursor)
            self.coords = QPoint(0, 0)

    def mouseMoveEvent(self, evt):
        """Execute the mouse move event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
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
        """Execute the wheel event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.scale += evt.angleDelta().y() / 8000.0
        QTimer.singleShot(0, self.update)

    def paintEvent(self, evt):
        """Execute the paint event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
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
        """Execute the close event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        if self.filename is not None:
            os.remove(self.filename)
        evt.accept()


class PDFViewer(QWidget):
    """Represent a PDF viewer in :mod:`harness_designer.ui.datasheet_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, pdf_file):
        """Initialise the :class:`PDFViewer` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param pdf_file: Value for ``pdf_file``.
        :type pdf_file: UNKNOWN
        """
        QWidget.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Native QPdfView (Qt 6.4+)
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
            lbl = QLabel(f"PDF viewer unavailable.\nInstall PySide6-QtPdf to view:\n{pdf_file}", self)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            layout.addWidget(lbl, 1)

    def _go_to_page(self, page_number):
        """Execute the go to page operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param page_number: Value for ``page_number``.
        :type page_number: UNKNOWN
        """
        # QPdfView.PageNavigator is available via navigator()
        try:
            self._view.pageNavigator().jump(page_number - 1, QPoint())
        except Exception:  # NOQA
            pass

    def _zoom(self, factor):
        """Execute the zoom operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param factor: Value for ``factor``.
        :type factor: UNKNOWN
        """
        self._zoom_factor *= factor
        try:
            self._view.setZoomFactor(self._zoom_factor)
        except Exception:  # NOQA
            pass


class DatasheetViewer(QWidget):
    """Represent a datasheet viewer in :mod:`harness_designer.ui.datasheet_viewer.viewer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, parent, datasheet):
        """Initialise the :class:`DatasheetViewer` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param datasheet: Value for ``datasheet``.
        :type datasheet: UNKNOWN
        """
        QWidget.__init__(self, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        format_type = os.path.splitext(datasheet)[-1][1:].lower()

        if format_type == 'pdf':
            ctrl = PDFViewer(self, datasheet)
        else:
            ctrl = ImageViewer(self, datasheet)

        layout.addWidget(ctrl, 1)
