"""
document_viewer.py
══════════════════
Two embeddable widgets for displaying PDF, raster image, SVG, and DXF content.

    DocumentViewer   – full-featured viewer with an integrated toolbar
    DocumentPreview  – fixed-size, read-only thumbnail (no controls, no mouse)

Requires : PySide6 >= 6.4
Optional : ezdxf >= 1.0   pip install ezdxf   (needed only for DXF content)

Usage
─────
    from document_viewer import DocumentViewer, DocumentPreview

    # ── Viewer ────────────────────────────────────────────────────────────────
    viewer = DocumentViewer(parent=self)
    layout.addWidget(viewer)

    viewer.set_pdf(my_qpdf_document)        # QPdfDocument (already loaded)
    viewer.set_pixmap(my_qpixmap)           # QPixmap
    viewer.set_svg(my_qsvg_renderer)        # QSvgRenderer
    err = viewer.set_dxf(my_ezdxf_drawing)  # ezdxf Drawing; returns None or error str
    viewer.clear()                           # reset to blank state

    viewer.page_changed.connect(lambda cur, tot: ...)   # 1-based
    viewer.zoom_changed.connect(lambda factor: ...)

    # ── Preview ───────────────────────────────────────────────────────────────
    preview = DocumentPreview(parent=self)
    preview.setFixedSize(200, 280)          # caller sets the size
    layout.addWidget(preview)

    preview.set_pdf(my_qpdf_document)       # renders page 0 as thumbnail
    preview.set_pixmap(my_qpixmap)
    preview.set_svg(my_qsvg_renderer)
    err = preview.set_dxf(my_ezdxf_drawing)
    preview.clear()

Zoom controls (DocumentViewer)
──────────────────────────────
    Toolbar +/− buttons    25 % coarse step
    Ctrl + scroll          ~10 % fine step, proportional (smooth on trackpads)
    Ctrl + =  /  Ctrl + +  zoom in  25 %  (caught by dedicated mouse zoom buttons)
    Ctrl + −               zoom out 25 %
    Ctrl + 0               reset to 100 %

DXF notes
─────────
    Only the Model Space layout is rendered.
    _DXF_BG sets the scene canvas colour so that CAD colour-index 7
    (white/black) renders correctly.  Change or set to None as needed.
"""

from typing import Any

from PySide6 import QtCore
from PySide6 import QtGui

from PySide6 import QtPdf
from PySide6 import QtPdfWidgets
from PySide6 import QtSvg
from PySide6 import QtSvgWidgets
from PySide6 import QtWidgets


# ── Zoom ──────────────────────────────────────────────────────────────────────

_ZOOM_PRESETS: list[tuple[str, float]] = [
    ("25%",  0.25), ("50%",  0.50), ("75%",  0.75), ("100%", 1.00),
    ("125%", 1.25), ("150%", 1.50), ("175%", 1.75), ("200%", 2.00),
    ("300%", 3.00), ("400%", 4.00),
]

_FIT_WIDTH = "Fit Width"
_FIT_PAGE = "Fit Page"
_ZOOM_STEP = 1.25    # toolbar +/− button (25 %)
_ZOOM_STEP_WHEEL = 1.10    # Ctrl+scroll fine step (10 % per standard notch)
_ZOOM_MIN = 0.05
_ZOOM_MAX = 16.0

# ── DXF canvas colour ─────────────────────────────────────────────────────────
# CAD colour-index 7 ("white/black") appears white on dark backgrounds.
# Set to None to use whatever the QGraphicsView background is.
_DXF_BG: str | None = "#1e1e1e"

# ── Stack pane indices ────────────────────────────────────────────────────────
_PANE_PDF = 0
_PANE_IMAGE = 1   # raster, SVG and DXF all share this pane


# ── Shared helpers ────────────────────────────────────────────────────────────

def _small_btn(text: str, tooltip: str = "") -> QtWidgets.QPushButton:
    btn = QtWidgets.QPushButton(text)
    btn.setFixedWidth(28)

    if tooltip:
        btn.setToolTip(tooltip)

    return btn


def _vline() -> QtWidgets.QFrame:
    sep = QtWidgets.QFrame()
    sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

    return sep


# ══════════════════════════════════════════════════════════════════════════════
# _ImageView  (internal)
# ══════════════════════════════════════════════════════════════════════════════
class _ImageView(QtWidgets.QGraphicsView):
    """
    Internal QGraphicsView that renders raster images, SVG, and DXF.

    • Left-drag    → pan  (ScrollHandDrag)
    • Ctrl+scroll  → zoom (proportional, fine-grained)
    • Plain scroll → scroll
    """

    zoom_changed: QtCore.SignalInstance = QtCore.Signal(float)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QtWidgets.QGraphicsScene(self)
        self._renderer: QtSvg.QSvgRenderer | None = None   # keeps SVG renderer alive
        self._zoom = 1.0

        self.setScene(self._scene)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing |
            QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    # ── content loaders ───────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        self._clear(reset_bg=True)
        item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(item.boundingRect())
        self._reset_zoom()

    def set_svg(self, renderer: QtSvg.QSvgRenderer) -> str | None:
        """Returns None on success or an error string."""
        if not renderer.isValid():
            return "Invalid SVG renderer"

        self._clear(reset_bg=True)
        self._renderer = renderer
        item = QtSvgWidgets.QGraphicsSvgItem()
        item.setSharedRenderer(renderer)
        self._scene.addItem(item)
        self._scene.setSceneRect(item.boundingRect())
        self._reset_zoom()
        return None

    def set_dxf(self, drawing: Any) -> str | None:
        """
        Render an ezdxf Drawing (modelspace) into the scene.
        Returns None on success or an error string on failure.
        """
        try:
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.pyqt import PyQtBackend
            from ezdxf.addons.drawing.config import Configuration
        except ImportError:
            return "DXF support requires ezdxf — pip install ezdxf"

        self._clear(reset_bg=False)
        if _DXF_BG:
            self._scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(_DXF_BG)))

        try:
            backend = PyQtBackend(scene=self._scene)
            if _DXF_BG:
                backend.set_background(_DXF_BG)

            ctx = RenderContext(drawing)
            config = Configuration()
            Frontend(ctx, backend, config=config).draw_layout(drawing.modelspace())

        except Exception as exc:
            return f"DXF render error: {exc}"

        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            return "DXF file produced no drawable geometry"

        self._scene.setSceneRect(rect)
        self._reset_zoom()
        return None

    # ── zoom ──────────────────────────────────────────────────────────────────

    def set_zoom(self, factor: float) -> None:
        factor = max(_ZOOM_MIN, min(factor, _ZOOM_MAX))
        self.resetTransform()
        self.scale(factor, factor)
        self._zoom = factor
        self.zoom_changed.emit(factor)

    def zoom_by(self, multiplier: float) -> None:
        self.set_zoom(self._zoom * multiplier)

    def fit_page(self) -> None:
        if not self._scene.items():
            return
        self.fitInView(self._scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)

    def fit_width(self) -> None:
        if not self._scene.items():
            return

        vw = self.viewport().width()
        sw = self._scene.sceneRect().width()
        if sw > 0:
            self.set_zoom(vw / sw)

    @property
    def zoom_factor(self) -> float:
        return self._zoom

    # ── private ───────────────────────────────────────────────────────────────

    def _clear(self, *, reset_bg: bool) -> None:
        self._scene.clear()
        self._renderer = None

        if reset_bg:
            self._scene.setBackgroundBrush(QtGui.QBrush())

    def _reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom = 1.0

    def wheelEvent(self, event) -> None:
        if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_by(_ZOOM_STEP_WHEEL ** (delta / 120.0))

            event.accept()
        else:
            super().wheelEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# _PDFPanFilter  (internal)
# ══════════════════════════════════════════════════════════════════════════════
class _PDFPanFilter(QtCore.QObject):
    """
    Installed on QPdfView.viewport().
    Left-drag → pan.  Ctrl+scroll → zoom (emits zoom_changed).
    Plain scroll passes through to QPdfView unchanged.
    """

    zoom_changed: QtCore.SignalInstance = QtCore.Signal(float)

    def __init__(self, pdf_view: QtPdfWidgets.QPdfView) -> None:
        super().__init__(pdf_view)
        self._view = pdf_view
        self._dragging = False
        self._last = QtCore.QPoint()
        vp = pdf_view.viewport()
        vp.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        vp.installEventFilter(self)

    def eventFilter(self, obj, event: QtGui.QMouseEvent | QtGui.QWheelEvent) -> bool:
        t = event.type()

        if t == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                self._dragging = True
                self._last = event.globalPosition().toPoint()
                obj.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
                return True

        elif t == QtCore.QEvent.Type.MouseMove:
            if self._dragging:
                pos = event.globalPosition().toPoint()
                delta = pos - self._last
                self._last = pos

                self._view.horizontalScrollBar().setValue(
                    self._view.horizontalScrollBar().value() - delta.x())

                self._view.verticalScrollBar().setValue(
                    self._view.verticalScrollBar().value() - delta.y())

                return True

        elif t == QtCore.QEvent.Type.MouseButtonRelease:
            if event.button() == QtCore.Qt.MouseButton.LeftButton and self._dragging:
                self._dragging = False
                obj.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
                return True

        elif t == QtCore.QEvent.Type.Wheel:
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                delta = event.angleDelta().y()
                if delta:
                    factor = _ZOOM_STEP_WHEEL ** (delta / 120.0)

                    new_f = max(
                        _ZOOM_MIN, min(self._view.zoomFactor() * factor, _ZOOM_MAX))

                    self._view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
                    self._view.setZoomFactor(new_f)
                    self.zoom_changed.emit(new_f)

                return True

        return False


# ══════════════════════════════════════════════════════════════════════════════
# DocumentViewer
# ══════════════════════════════════════════════════════════════════════════════
class CADDatasheetCtrl(QtWidgets.QWidget):
    """
    Full-featured document viewer with an integrated toolbar.

    The toolbar is part of the widget, not the parent dialog, so it can be
    placed freely in any layout alongside other controls.

    Load content by calling one of the set_* methods with a pre-constructed
    data container (no file-open UI is included):

        set_pixmap(QPixmap)
        set_pdf(QPdfDocument)          # must already be in Status.Ready
        set_svg(QSvgRenderer)
        set_dxf(drawing) → str|None    # ezdxf Drawing; None = success
        clear()

    Signals
    -------
    page_changed(current: int, total: int)   1-based; single-page sources emit (1, 1)
    zoom_changed(factor: float)
    """

    page_changed: QtCore.SignalInstance = QtCore.Signal(int, int)
    zoom_changed: QtCore.SignalInstance = QtCore.Signal(float)

    # ── init ──────────────────────────────────────────────────────────────────

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._pdf_doc: QtPdf.QPdfDocument | None = None
        self._mode = _PANE_IMAGE   # start on blank image pane

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QtWidgets.QWidget()
        lay = QtWidgets.QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(4)

        # Page navigation
        self._btn_prev = _small_btn("‹", "Previous page  (←  /  PgUp)")
        self._btn_next = _small_btn("›", "Next page  (→  /  PgDn)")
        self._page_input = QtWidgets.QLineEdit("—")
        self._page_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._page_input.setFixedWidth(52)
        self._page_input.setToolTip("Current page — press Enter to jump")
        self._lbl_total = QtWidgets.QLabel("/ —")
        self._lbl_total.setToolTip("Total pages")

        for w in (self._btn_prev, self._page_input, self._lbl_total, self._btn_next):
            lay.addWidget(w)

        lay.addWidget(_vline())

        # Zoom
        self._btn_zoom_out = _small_btn(
            "−", "Zoom out  (Ctrl+−  or  Ctrl+scroll ↓)")

        self._btn_zoom_in = _small_btn(
            "+", "Zoom in   (Ctrl++  or  Ctrl+scroll ↑)")

        self._zoom_combo = QtWidgets.QComboBox()
        self._zoom_combo.setEditable(True)
        self._zoom_combo.setFixedWidth(108)
        self._zoom_combo.setToolTip("Zoom — pick a preset or type a percentage")
        self._zoom_combo.addItems([lbl for lbl, _ in _ZOOM_PRESETS])
        self._zoom_combo.addItem(_FIT_WIDTH)
        self._zoom_combo.addItem(_FIT_PAGE)
        self._zoom_combo.setCurrentText("100%")

        if le := self._zoom_combo.lineEdit():
            le.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        for w in (self._btn_zoom_out, self._zoom_combo, self._btn_zoom_in):
            lay.addWidget(w)

        lay.addWidget(_vline())

        # Page-mode toggle (PDF only; disabled for other types)
        self._btn_mode = QtWidgets.QPushButton("Continuous")
        self._btn_mode.setCheckable(True)
        self._btn_mode.setChecked(True)
        self._btn_mode.setToolTip(
            "Toggle between continuous scroll and single-page mode")

        lay.addWidget(self._btn_mode)

        # Start fully disabled
        self._set_nav_enabled(False)
        self._set_zoom_enabled(False)
        self._btn_mode.setEnabled(False)

        root.addWidget(bar)

        self._stack = QtWidgets.QStackedWidget(self)

        self._pdf_view = QtPdfWidgets.QPdfView(self)
        self._pdf_view.setPageMode(QtPdfWidgets.QPdfView.PageMode.MultiPage)
        self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
        self._pdf_view.setZoomFactor(1.0)
        self._pan_filter = _PDFPanFilter(self._pdf_view)
        self._stack.addWidget(self._pdf_view)  # _PANE_PDF = 0

        self._img_view = _ImageView(self)
        self._stack.addWidget(self._img_view)  # _PANE_IMAGE = 1

        self._stack.setCurrentIndex(_PANE_IMAGE)
        root.addWidget(self._stack)

        self._btn_prev.clicked.connect(self._go_prev)
        self._btn_next.clicked.connect(self._go_next)
        self._page_input.returnPressed.connect(self._jump_to_input_page)

        self._btn_zoom_in.clicked.connect(self._zoom_in)
        self._btn_zoom_out.clicked.connect(self._zoom_out)
        self._zoom_combo.currentIndexChanged.connect(
            self._on_zoom_index_changed)

        if le := self._zoom_combo.lineEdit():
            le.returnPressed.connect(self._on_zoom_typed)

        self._btn_mode.clicked.connect(self._toggle_page_mode)

        # PDF page change
        self._pdf_view.pageNavigator().currentPageChanged.connect(
            self._on_pdf_page_changed)

        # Zoom-from-scroll (PDF pan filter & image view both emit zoom_changed)
        self._pan_filter.zoom_changed.connect(self._on_zoom_changed_external)
        self._img_view.zoom_changed.connect(self._on_zoom_changed_external)

        # Browser-standard keyboard zoom — also catches dedicated mouse zoom buttons
        _ctx = QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut

        for seq, slot in (
            ("Ctrl+=", self._zoom_in),
            ("Ctrl++", self._zoom_in),
            ("Ctrl+-", self._zoom_out),
            ("Ctrl+0", self._zoom_reset),
        ):
            sc = QtGui.QShortcut(QtGui.QKeySequence(seq), self)
            sc.setContext(_ctx)
            sc.activated.connect(slot)

    # ── public API ────────────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Display a raster image (QPixmap)."""
        self._img_view.set_pixmap(pixmap)
        self._activate_image_pane()

    def set_pdf(self, document: QtPdf.QPdfDocument) -> None:
        """
        Display an already-loaded QPdfDocument.
        The document must be in QPdfDocument.Status.Ready before calling this.
        """
        self._pdf_doc = document
        self._mode = _PANE_PDF
        self._pdf_view.setDocument(document)
        self._stack.setCurrentIndex(_PANE_PDF)

        n = document.pageCount()
        self._page_input.setValidator(QtGui.QIntValidator(1, max(n, 1), self))
        self._lbl_total.setText(f"/ {n}")
        self._page_input.setText("1")
        self._set_nav_enabled(True)
        self._set_zoom_enabled(True)
        self._btn_mode.setEnabled(True)
        self._refresh_pdf_nav()

    def set_svg(self, renderer: QtSvg.QSvgRenderer) -> str | None:
        """
        Display an SVG via a QSvgRenderer.
        Returns None on success or an error string on failure.
        """
        err = self._img_view.set_svg(renderer)
        if err:
            return err

        self._activate_image_pane()

        return None

    def set_dxf(self, drawing: Any) -> str | None:
        """
        Display an ezdxf Drawing (model space).
        Returns None on success or an error string on failure.
        Requires ezdxf: pip install ezdxf
        """
        err = self._img_view.set_dxf(drawing)
        if err:
            return err

        self._activate_image_pane()

        return None

    def clear(self) -> None:
        """Reset the viewer to an empty state."""
        self._pdf_doc = None
        self._pdf_view.setDocument(None)
        self._img_view._clear(reset_bg=True)  # NOQA
        self._mode = _PANE_IMAGE
        self._stack.setCurrentIndex(_PANE_IMAGE)
        self._page_input.setText("—")
        self._lbl_total.setText("/ —")
        self._set_nav_enabled(False)
        self._set_zoom_enabled(False)
        self._btn_mode.setEnabled(False)

    # ── private: enable helpers ───────────────────────────────────────────────

    def _set_nav_enabled(self, enabled: bool) -> None:
        for w in (self._btn_prev, self._btn_next, self._page_input):
            w.setEnabled(enabled)

    def _set_zoom_enabled(self, enabled: bool) -> None:
        for w in (self._btn_zoom_in, self._btn_zoom_out, self._zoom_combo):
            w.setEnabled(enabled)

    # ── private: image-pane activation ───────────────────────────────────────

    def _activate_image_pane(self) -> None:
        self._mode = _PANE_IMAGE
        self._stack.setCurrentIndex(_PANE_IMAGE)
        self._page_input.setValidator(QtGui.QIntValidator(1, 1, self))
        self._page_input.setText("1")
        self._lbl_total.setText("/ 1")
        self._set_nav_enabled(False)   # locked to 1 / 1
        self._set_zoom_enabled(True)
        self._btn_mode.setEnabled(False)
        QtCore.QTimer.singleShot(0, self._img_view.fit_page)
        QtCore.QTimer.singleShot(0, lambda: self._sync_zoom_combo(self._img_view.zoom_factor))

    # ── private: PDF navigation ───────────────────────────────────────────────

    @QtCore.Slot(int)
    def _on_pdf_page_changed(self, page: int) -> None:   # 0-based
        if self._mode != _PANE_PDF:
            return

        self._page_input.setText(str(page + 1))
        self._refresh_pdf_nav()
        n = self._pdf_doc.pageCount() if self._pdf_doc else 0
        self.page_changed.emit(page + 1, n)

    def _refresh_pdf_nav(self) -> None:
        page = self._pdf_view.pageNavigator().currentPage()
        total = self._pdf_doc.pageCount() if self._pdf_doc else 0
        self._btn_prev.setEnabled(page > 0)
        self._btn_next.setEnabled(page < total - 1)

    @QtCore.Slot()
    def _go_prev(self) -> None:
        if self._mode != _PANE_PDF:
            return

        nav = self._pdf_view.pageNavigator()

        p = nav.currentPage()
        if p > 0:
            nav.jump(p - 1, QtCore.QPointF())

    @QtCore.Slot()
    def _go_next(self) -> None:
        if self._mode != _PANE_PDF:
            return

        nav = self._pdf_view.pageNavigator()
        p = nav.currentPage()

        if self._pdf_doc:
            total = self._pdf_doc.pageCount()
        else:
            total = 0

        if p < total - 1:
            nav.jump(p + 1, QtCore.QPointF())

    @QtCore.Slot()
    def _jump_to_input_page(self) -> None:
        if self._mode != _PANE_PDF or not self._pdf_doc:
            return

        try:
            page = int(self._page_input.text()) - 1
        except ValueError:
            return

        page = max(0, min(page, self._pdf_doc.pageCount() - 1))
        self._pdf_view.pageNavigator().jump(page, QtCore.QPointF())

    # ── private: page-mode toggle ─────────────────────────────────────────────

    @QtCore.Slot(bool)
    def _toggle_page_mode(self, checked: bool) -> None:
        if checked:
            self._pdf_view.setPageMode(QtPdfWidgets.QPdfView.PageMode.MultiPage)
            self._btn_mode.setText("Continuous")
        else:
            self._pdf_view.setPageMode(QtPdfWidgets.QPdfView.PageMode.SinglePage)
            self._btn_mode.setText("Single Page")

    # ── private: zoom ─────────────────────────────────────────────────────────

    @QtCore.Slot()
    def _zoom_in(self) -> None:
        if self._mode == _PANE_PDF:
            self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
            new_f = min(self._pdf_view.zoomFactor() * _ZOOM_STEP, _ZOOM_MAX)
            self._pdf_view.setZoomFactor(new_f)
            self._sync_zoom_combo(new_f)
        else:
            self._img_view.zoom_by(_ZOOM_STEP)

    @QtCore.Slot()
    def _zoom_out(self) -> None:
        if self._mode == _PANE_PDF:
            self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
            new_f = max(self._pdf_view.zoomFactor() / _ZOOM_STEP, _ZOOM_MIN)
            self._pdf_view.setZoomFactor(new_f)
            self._sync_zoom_combo(new_f)
        else:
            self._img_view.zoom_by(1.0 / _ZOOM_STEP)

    @QtCore.Slot()
    def _zoom_reset(self) -> None:
        if self._mode == _PANE_PDF:
            self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
            self._pdf_view.setZoomFactor(1.0)
            self._sync_zoom_combo(1.0)
        else:
            self._img_view.set_zoom(1.0)

    @QtCore.Slot(int)
    def _on_zoom_index_changed(self, idx: int) -> None:
        self._apply_zoom_text(self._zoom_combo.itemText(idx))

    @QtCore.Slot()
    def _on_zoom_typed(self) -> None:
        if le := self._zoom_combo.lineEdit():
            self._apply_zoom_text(le.text())

    def _apply_zoom_text(self, text: str) -> None:
        text = text.strip()
        if text == _FIT_WIDTH:
            if self._mode == _PANE_PDF:
                self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.FitToWidth)
            else:
                self._img_view.fit_width()

            return

        if text == _FIT_PAGE:
            if self._mode == _PANE_PDF:
                self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.FitInView)
            else:
                self._img_view.fit_page()

            return

        for label, factor in _ZOOM_PRESETS:
            if label == text:
                self._set_zoom_factor(factor)

                return

        try:
            factor = float(text.rstrip("%")) / 100.0
            self._set_zoom_factor(max(_ZOOM_MIN, min(factor, _ZOOM_MAX)))
        except ValueError:
            pass

    def _set_zoom_factor(self, factor: float) -> None:
        if self._mode == _PANE_PDF:
            self._pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
            self._pdf_view.setZoomFactor(factor)
        else:
            self._img_view.set_zoom(factor)

    @QtCore.Slot(float)
    def _on_zoom_changed_external(self, factor: float) -> None:
        """Receives zoom_changed from _PDFPanFilter or _ImageView."""
        self._sync_zoom_combo(factor)
        self.zoom_changed.emit(factor)

    def _sync_zoom_combo(self, factor: float) -> None:
        pct = f"{round(factor * 100)}%"
        self._zoom_combo.blockSignals(True)

        idx = self._zoom_combo.findText(pct)
        if idx >= 0:
            self._zoom_combo.setCurrentIndex(idx)
        elif le := self._zoom_combo.lineEdit():
            le.setText(pct)

        self._zoom_combo.blockSignals(False)
        self.zoom_changed.emit(factor)


# ══════════════════════════════════════════════════════════════════════════════
# DocumentPreview
# ══════════════════════════════════════════════════════════════════════════════
class CADDatasheetPreviewCtrl(QtWidgets.QWidget):
    """
    Read-only thumbnail of a document's first page (or only content).

    • No toolbar, no controls, no mouse or keyboard interaction.
    • Content is scaled to fit the widget while preserving aspect ratio.
    • Set the widget size externally (e.g. setFixedSize) before calling set_*.
    • Internally renders at _RENDER_LONG_EDGE pixels on the longest axis
      for HiDPI-quality output at typical preview sizes.

    API mirrors DocumentViewer:

        set_pixmap(QPixmap)
        set_pdf(QPdfDocument, page=0)
        set_svg(QSvgRenderer)
        set_dxf(drawing)  → str | None
        clear()
    """

    # px for internal render (change for quality/memory trade-off)
    _RENDER_LONG_EDGE = 1200

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self._pixmap: QtGui.QPixmap | None = None

    # ── content setters ───────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QtGui.QPixmap) -> None:
        """Display a raster image."""
        self._pixmap = pixmap
        self.update()

    def set_pdf(self, document: QtPdf.QPdfDocument, page: int = 0) -> None:
        """Render *page* (0-based) of an already-loaded QPdfDocument."""
        if (
            document.status() != QtPdf.QPdfDocument.Status.Ready or
            document.pageCount() == 0 or
            page >= document.pageCount()
        ):
            self._pixmap = None
            self.update()
            return

        page_pt = document.pagePointSize(page)   # QSizeF in typographic points
        if page_pt.isEmpty():
            self._pixmap = None
            self.update()
            return

        render_size = self._aspect_size(page_pt.width(), page_pt.height())
        image = document.render(page, render_size)

        if not image.isNull():
            self._pixmap = QtGui.QPixmap.fromImage(image)
        else:
            self._pixmap = None

        self.update()

    def set_svg(self, renderer: QtSvg.QSvgRenderer) -> str | None:
        """
        Render an SVG thumbnail.
        Returns None on success or an error string on failure.
        """
        if not renderer.isValid():
            self._pixmap = None
            self.update()
            return "Invalid SVG renderer"

        ds = renderer.defaultSize()   # QSize in logical pixels
        if ds.isEmpty():
            self._pixmap = None
            self.update()
            return "SVG has no default size"

        render_size = self._aspect_size(ds.width(), ds.height())
        image = QtGui.QImage(render_size, QtGui.QImage.Format.Format_ARGB32)
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(image)

        renderer.render(
            painter, QtCore.QRectF(0, 0, render_size.width(), render_size.height()))

        painter.end()
        self._pixmap = QtGui.QPixmap.fromImage(image)
        self.update()

        return None

    def set_dxf(self, drawing: Any) -> str | None:
        """
        Render DXF model space as a thumbnail.
        Returns None on success or an error string on failure.
        Requires ezdxf: pip install ezdxf
        """
        try:
            from ezdxf.addons.drawing import RenderContext, Frontend
            from ezdxf.addons.drawing.pyqt import PyQtBackend
            from ezdxf.addons.drawing.config import Configuration
        except ImportError:
            return "DXF support requires ezdxf — pip install ezdxf"

        try:
            scene = QtWidgets.QGraphicsScene()
            backend = PyQtBackend(scene=scene)

            if _DXF_BG:
                backend.set_background(_DXF_BG)

            ctx = RenderContext(drawing)

            Frontend(ctx, backend, Configuration()).draw_layout(
                drawing.modelspace())

        except Exception as exc:
            return f"DXF render error: {exc}"

        scene.setSceneRect(scene.itemsBoundingRect())
        if scene.sceneRect().isEmpty():
            return "DXF file produced no drawable geometry"

        br = scene.sceneRect()
        render_size = self._aspect_size(br.width(), br.height())

        if _DXF_BG:
            bg_color = QtGui.QColor(_DXF_BG)
        else:
            bg_color = QtGui.QColor(QtCore.Qt.GlobalColor.white)

        image = QtGui.QImage(render_size, QtGui.QImage.Format.Format_ARGB32)
        image.fill(bg_color)
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        scene.render(painter, QtCore.QRectF(image.rect()), scene.sceneRect())
        painter.end()

        self._pixmap = QtGui.QPixmap.fromImage(image)
        self.update()

    def clear(self) -> None:
        """Reset to blank state."""
        self._pixmap = None
        self.update()

    # ── painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        if not self._pixmap or self._pixmap.isNull():
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        scaled = self._pixmap.scaled(
            self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation)

        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    # ── block all interaction ─────────────────────────────────────────────────

    def mousePressEvent(self, e) -> None:
        e.accept()

    def mouseMoveEvent(self, e) -> None:
        e.accept()

    def mouseReleaseEvent(self, e) -> None:
        e.accept()

    def mouseDoubleClickEvent(self, e) -> None:
        e.accept()

    def wheelEvent(self, e) -> None:
        e.accept()

    def contextMenuEvent(self, e) -> None:
        e.accept()

    def keyPressEvent(self, e) -> None:
        e.accept()

    # ── private ───────────────────────────────────────────────────────────────

    def _aspect_size(self, w: float, h: float) -> QtCore.QSize:
        """Return a QSize with _RENDER_LONG_EDGE on the longer axis, preserving aspect."""
        if w <= 0 or h <= 0:
            return QtCore.QSize(self._RENDER_LONG_EDGE, self._RENDER_LONG_EDGE)

        if w >= h:
            return QtCore.QSize(self._RENDER_LONG_EDGE,
                                max(1, int(h / w * self._RENDER_LONG_EDGE)))

        return QtCore.QSize(max(1, int(w / h * self._RENDER_LONG_EDGE)),
                            self._RENDER_LONG_EDGE)
