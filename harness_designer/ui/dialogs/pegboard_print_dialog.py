# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import math
import os
import traceback

from PySide6 import QtCore, QtGui, QtPrintSupport, QtWidgets

from . import dialog_base as _dialog_base
from . import error as _error
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui
    from ...pegboard_print import layout as _layout


PREVIEW_BACKGROUND = '#2d3135'
SETTINGS_WIDTH = 330

DEFAULT_MARGIN_MM = 6.0
DEFAULT_OVERLAP_MM = 12.0
DEFAULT_PADDING_MM = 10.0
DPI_CHOICES = (150, 300, 600)
DEFAULT_DPI = 300

# Asking first when a job is this many sheets keeps a mistyped scale from
# sending a hundred pages to the printer.
CONFIRM_PAGE_COUNT = 30


class _LayoutPreview(QtWidgets.QWidget):
    """Draws the content and the sheets it will be printed on."""

    _FILLS = (QtGui.QColor(90, 140, 210, 70), QtGui.QColor(230, 160, 70, 70))

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`_LayoutPreview` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        super().__init__(parent)
        self.setMinimumSize(360, 300)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

        self._layout = None
        self._message = 'There is nothing in the Peg Board Editor to print.'

    @_check_types.do
    def set_layout(self, layout: _Union["_layout.PrintLayout", None], message: str = '') -> None:
        """Show a different layout.

        :param layout: Layout to draw, or ``None`` to show *message* instead.
        :type layout: :class:`~harness_designer.pegboard_print.layout.PrintLayout` | None
        :param message: Text to show when there is no layout.
        :type message: str
        """
        self._layout = layout
        if message:
            self._message = message

        self.update()

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paint the sheets over the content, scaled to fit.

        :param event: Event object.
        :type event: :class:`QtGui.QPaintEvent`
        """
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(PREVIEW_BACKGROUND))

        layout = self._layout
        if layout is None:
            painter.setPen(QtGui.QColor(220, 220, 220))
            painter.drawText(self.rect().adjusted(20, 20, -20, -20),
                             QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.TextFlag.TextWordWrap,
                             self._message)
            painter.end()
            return

        tiles = layout.tiles
        left = min(t.x0 for t in tiles)
        top = min(t.z0 for t in tiles)
        right = max(t.x1 for t in tiles)
        bottom = max(t.z1 for t in tiles)

        area = QtCore.QRectF(self.rect()).adjusted(16, 16, -16, -16)
        factor = min(area.width() / (right - left), area.height() / (bottom - top))

        def to_widget(x: float, z: float) -> QtCore.QPointF:
            return QtCore.QPointF(area.center().x() + (x - (left + right) / 2.0) * factor,
                                  area.center().y() + (z - (top + bottom) / 2.0) * factor)

        def rect_of(x0: float, z0: float, x1: float, z1: float) -> QtCore.QRectF:
            return QtCore.QRectF(to_widget(x0, z0), to_widget(x1, z1))

        for tile in tiles:
            rect = rect_of(tile.x0, tile.z0, tile.x1, tile.z1)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 150), 1))
            painter.setBrush(self._FILLS[(tile.col + tile.row) % 2])
            painter.drawRect(rect)

        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        pen = QtGui.QPen(QtGui.QColor(120, 220, 120), 1.5, QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(rect_of(*layout.bounds))

        painter.setPen(QtGui.QColor(255, 255, 255))
        for tile in tiles:
            rect = rect_of(tile.x0, tile.z0, tile.x1, tile.z1)
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, str(tile.number))

        painter.end()


class PegboardPrintDialog(_dialog_base.BaseDialog):
    """Print the Peg Board Editor at a chosen scale, across as many sheets as it takes.

    A scale of 100% prints one millimetre on the peg board as one millimetre
    on the paper. The sheets overlap and carry alignment marks, so they can be
    laid edge to edge and glued with the crosshairs on top of each other. The
    floating wire tables and concentric sections print as they appear on
    screen.

    The paper size and orientation come from the printer (or PDF writer), via
    Page Setup. Settings are kept for as long as the dialog lives (the main
    window keeps one instance, :meth:`MainFrame.show_pegboard_print`).
    """

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`PegboardPrintDialog` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        super().__init__(
            mainframe, 'Print Peg Board', size=(980, 560),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Close)

        self._printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        self._bounds: tuple[float, float, float, float] | None = None
        self._layout: "_layout.PrintLayout | None" = None
        self._updating = False

        if os.name == 'nt':
            self._last_dir = os.path.expandvars('~/Documents')
        else:
            self._last_dir = os.path.expanduser('~')

        panel = self.panel

        self.paper_text = QtWidgets.QLabel(panel)
        self.paper_text.setWordWrap(True)
        self.page_setup_btn = QtWidgets.QPushButton('Page Setup...', panel)
        self.page_setup_btn.clicked.connect(self.on_page_setup)

        self.scale_radio = QtWidgets.QRadioButton('Scale', panel)
        self.scale_radio.setChecked(True)
        self.fit_radio = QtWidgets.QRadioButton('Fit to', panel)

        self.scale_spin = QtWidgets.QDoubleSpinBox(panel)
        self.scale_spin.setRange(1.0, 2000.0)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setSingleStep(5.0)
        self.scale_spin.setValue(100.0)
        self.scale_spin.setSuffix(' %')

        self.actual_btn = QtWidgets.QPushButton('1:1', panel)
        self.actual_btn.setToolTip('Print mm for mm (100%).')
        self.actual_btn.setFixedWidth(40)
        self.actual_btn.clicked.connect(self.on_actual_size)

        self.fit_cols = QtWidgets.QSpinBox(panel)
        self.fit_cols.setRange(1, 50)
        self.fit_cols.setValue(2)
        self.fit_rows = QtWidgets.QSpinBox(panel)
        self.fit_rows.setRange(1, 50)
        self.fit_rows.setValue(2)

        self.margin_spin = self._mm_spin(DEFAULT_MARGIN_MM, 0.0, 50.0)
        self.overlap_spin = self._mm_spin(DEFAULT_OVERLAP_MM, 10.0, 60.0)
        self.padding_spin = self._mm_spin(DEFAULT_PADDING_MM, 0.0, 500.0)

        self.dpi_combo = QtWidgets.QComboBox(panel)
        for dpi in DPI_CHOICES:
            self.dpi_combo.addItem(f'{dpi} dpi', dpi)
        self.dpi_combo.setCurrentIndex(DPI_CHOICES.index(DEFAULT_DPI))

        self.summary = QtWidgets.QLabel(panel)
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(QtCore.Qt.TextFormat.RichText)

        self.note = QtWidgets.QLabel(
            'Turn off "fit to page" / "scale to fit" in the printer settings. '
            'Each sheet has a scale bar to check the print against a ruler.', panel)
        self.note.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        scale_row = QtWidgets.QHBoxLayout()
        scale_row.addWidget(self.scale_spin, 1)
        scale_row.addWidget(self.actual_btn)
        form.addRow(self.scale_radio, scale_row)

        fit_row = QtWidgets.QHBoxLayout()
        fit_row.addWidget(self.fit_cols)
        fit_row.addWidget(QtWidgets.QLabel('x', panel))
        fit_row.addWidget(self.fit_rows)
        fit_row.addWidget(QtWidgets.QLabel('pages', panel))
        fit_row.addStretch(1)
        form.addRow(self.fit_radio, fit_row)

        form.addRow('Margin', self.margin_spin)
        form.addRow('Overlap', self.overlap_spin)
        form.addRow('Space around drawing', self.padding_spin)
        form.addRow('Quality', self.dpi_combo)

        paper_row = QtWidgets.QHBoxLayout()
        paper_row.addWidget(self.paper_text, 1)
        paper_row.addWidget(self.page_setup_btn)

        settings = QtWidgets.QVBoxLayout()
        settings.addLayout(paper_row)
        settings.addSpacing(8)
        settings.addLayout(form)
        settings.addSpacing(8)
        settings.addWidget(self.summary)
        settings.addStretch(1)
        settings.addWidget(self.note)

        settings_host = QtWidgets.QWidget(panel)
        settings_host.setLayout(settings)
        settings_host.setFixedWidth(SETTINGS_WIDTH)

        self.preview = _LayoutPreview(panel)

        main_lay = QtWidgets.QHBoxLayout(panel)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(settings_host)
        main_lay.addWidget(self.preview, 1)

        action_role = QtWidgets.QDialogButtonBox.ButtonRole.ActionRole

        self.pdf_btn = self.button_box.addButton('Save as PDF...', action_role)
        self.pdf_btn.clicked.connect(self.on_save_pdf)

        self.print_btn = self.button_box.addButton('Print...', action_role)
        self.print_btn.clicked.connect(self.on_print)

        for widget in (self.scale_spin, self.margin_spin, self.overlap_spin, self.padding_spin):
            widget.valueChanged.connect(self._on_settings_changed)

        for widget in (self.fit_cols, self.fit_rows):
            widget.valueChanged.connect(self._on_settings_changed)

        self.scale_radio.toggled.connect(self._on_settings_changed)
        self.dpi_combo.currentIndexChanged.connect(self._on_settings_changed)

        self._sync_printer_limits()

    @_check_types.do
    def _mm_spin(self, value: float, low: float, high: float) -> QtWidgets.QDoubleSpinBox:
        """A millimetre spin box.

        :param value: Starting value.
        :type value: float
        :param low: Smallest value.
        :type low: float
        :param high: Largest value.
        :type high: float
        :rtype: :class:`QtWidgets.QDoubleSpinBox`
        """
        spin = QtWidgets.QDoubleSpinBox(self.panel)
        spin.setRange(low, high)
        spin.setDecimals(1)
        spin.setSingleStep(1.0)
        spin.setSuffix(' mm')
        spin.setValue(value)
        return spin

    @_check_types.do
    def refresh(self) -> None:
        """Re-read the peg board and update the preview. Call before showing."""
        from ...pegboard_print import renderer as _renderer

        self._bounds = _renderer.content_bounds(self._canvas())
        self._recalculate()

    @_check_types.do
    def _canvas(self):
        """The Peg Board Editor's GL canvas."""
        return self.mainframe.editor_pegboard.editor._canvas  # NOQA

    @_check_types.do
    def _sync_printer_limits(self) -> None:
        """Keep the margin from going below what the printer cannot reach."""
        from ...pegboard_print import job as _job

        minimum = math.ceil(_job.minimum_margin(self._printer) * 10.0) / 10.0

        self._updating = True
        try:
            self.margin_spin.setMinimum(minimum)
            if self.margin_spin.value() < minimum:
                self.margin_spin.setValue(minimum)
        finally:
            self._updating = False

    @_check_types.do
    def _on_settings_changed(self, *_) -> None:
        """Recompute the layout after any control changed."""
        if self._updating:
            return

        self.scale_spin.setEnabled(self.scale_radio.isChecked())
        self.actual_btn.setEnabled(self.scale_radio.isChecked())
        self.fit_cols.setEnabled(self.fit_radio.isChecked())
        self.fit_rows.setEnabled(self.fit_radio.isChecked())

        self._recalculate()

    @_check_types.do
    def _padded_bounds(self) -> tuple[float, float, float, float] | None:
        """The content bounds with the chosen space added around them."""
        if self._bounds is None:
            return None

        pad = self.padding_spin.value()
        x0, z0, x1, z1 = self._bounds

        return x0 - pad, z0 - pad, x1 + pad, z1 + pad

    @_check_types.do
    def _build_layout(self) -> "_layout.PrintLayout":
        """The layout for the current controls and printer.

        :raises ValueError: When the controls cannot make a layout.
        """
        from ...pegboard_print import job as _job
        from ...pegboard_print import layout as _layout_mod

        bounds = self._padded_bounds()
        if bounds is None:
            raise ValueError('There is nothing in the Peg Board Editor to print.')

        geometry = _job.page_geometry(
            self._printer, self.margin_spin.value(), self.overlap_spin.value())

        if self.fit_radio.isChecked():
            scale = _layout_mod.fit_scale(
                bounds, self.fit_cols.value(), self.fit_rows.value(), geometry)
        else:
            scale = self.scale_spin.value() / 100.0

        return _layout_mod.build_layout(bounds, scale, geometry)

    @_check_types.do
    def _recalculate(self) -> None:
        """Rebuild the layout and everything that shows it."""
        page = self._printer.pageLayout()
        size = page.fullRect(QtGui.QPageLayout.Unit.Millimeter)
        orientation = ('Landscape' if page.orientation() == QtGui.QPageLayout.Orientation.Landscape
                       else 'Portrait')

        self.paper_text.setText(
            f'{page.pageSize().name()}, {orientation} '
            f'({size.width():.0f} x {size.height():.0f} mm)')

        try:
            self._layout = self._build_layout()
        except ValueError as err:
            self._layout = None
            self.preview.set_layout(None, str(err))
            self.summary.setText(f'<span style="color:#d05050">{err}</span>')
            self.print_btn.setEnabled(False)
            self.pdf_btn.setEnabled(False)
            return

        layout = self._layout
        width, height = layout.printed_size
        x0, z0, x1, z1 = layout.bounds

        # Fit mode picks the scale, so show what it picked.
        if self.fit_radio.isChecked():
            self._updating = True
            try:
                self.scale_spin.setValue(max(1.0, min(2000.0, layout.scale * 100.0)))
            finally:
                self._updating = False

        self.summary.setText(
            f'Drawing: {x1 - x0:,.0f} x {z1 - z0:,.0f} mm<br>'
            f'Printed size: {width:,.0f} x {height:,.0f} mm '
            f'({layout.scale * 100.0:.1f}%)<br>'
            f'<b>{layout.page_count} sheet{"s" if layout.page_count != 1 else ""}</b> '
            f'({layout.cols} across x {layout.rows} down)')

        self.preview.set_layout(layout)
        self.print_btn.setEnabled(True)
        self.pdf_btn.setEnabled(True)

    @_check_types.do
    def on_actual_size(self) -> None:
        """Set the scale to 1:1."""
        self.scale_radio.setChecked(True)
        self.scale_spin.setValue(100.0)

    @_check_types.do
    def on_page_setup(self) -> None:
        """Choose paper size and orientation."""
        dlg = QtPrintSupport.QPageSetupDialog(self._printer, self)
        if dlg.exec():
            self._sync_printer_limits()
            self._recalculate()

    @_check_types.do
    def on_print(self) -> None:
        """Pick a printer and print."""
        dlg = QtPrintSupport.QPrintDialog(self._printer, self)
        dlg.setWindowTitle('Print Peg Board')

        if not dlg.exec():
            return

        # The print dialog can change paper, orientation and the margins the
        # printer can reach, any of which changes the page count.
        self._sync_printer_limits()
        self._recalculate()

        if self._layout is not None:
            self._run(self._printer)

    @_check_types.do
    def on_save_pdf(self) -> None:
        """Write the pages to a PDF file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save as PDF', os.path.join(self._last_dir, 'pegboard.pdf'), 'PDF (*.pdf)')

        if not path:
            return

        self._last_dir = os.path.dirname(path)

        pdf = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
        pdf.setOutputFormat(QtPrintSupport.QPrinter.OutputFormat.PdfFormat)
        pdf.setOutputFileName(path)
        pdf.setPageLayout(self._printer.pageLayout())

        self._run(pdf)

    @_check_types.do
    def _run(self, printer: QtPrintSupport.QPrinter) -> None:
        """Print the current layout on *printer*, with a progress window.

        :param printer: Printer or PDF writer, set up for the layout's paper.
        :type printer: :class:`QtPrintSupport.QPrinter`
        """
        from ...pegboard_print import job as _job

        layout = self._layout
        count = layout.page_count

        if count >= CONFIRM_PAGE_COUNT:
            answer = QtWidgets.QMessageBox.question(
                self, 'Print Peg Board', f'This will print {count} sheets. Continue?')

            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        progress = QtWidgets.QProgressDialog('Preparing...', 'Cancel', 0, count, self)
        progress.setWindowTitle('Print Peg Board')
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)

        def step(done: int, total: int) -> bool:
            progress.setValue(done)
            if done < total:
                progress.setLabelText(f'Printing page {done + 1} of {total}...')

            # Between pages the canvas is back in its normal state, so letting
            # the UI run here is safe (see pegboard_print.renderer).
            QtWidgets.QApplication.processEvents()
            return not progress.wasCanceled()

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            _job.print_layout(
                self._canvas(), printer, layout, self.dpi_combo.currentData(), step)

        except Exception:  # NOQA
            self._show_error('The peg board could not be printed.', traceback.format_exc())

        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            progress.close()
            progress.deleteLater()

    @_check_types.do
    def _show_error(self, message: str, details: str = '') -> None:
        """Tell the user something went wrong.

        :param message: What happened.
        :type message: str
        :param details: Traceback or other technical detail.
        :type details: str
        """
        widgets = []

        if details:
            text = QtWidgets.QPlainTextEdit(details)
            text.setReadOnly(True)
            text.setMinimumHeight(160)
            widgets.append(text)

        dlg = _error.ErrorDialog(self, message, 'Print Peg Board', *widgets)
        try:
            dlg.exec()
        finally:
            dlg.deleteLater()

