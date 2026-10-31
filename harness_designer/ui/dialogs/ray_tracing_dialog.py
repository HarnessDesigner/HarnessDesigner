# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import sys
import traceback

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from . import dialog_base as _dialog_base
from . import error as _error
from . import render_setings as _render_settings
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ... import ui as _ui


PREVIEW_BACKGROUND = '#2d3135'
PREVIEW_REFRESH_MS = 100
SETTINGS_WIDTH = 480

# Repainting a 30000 pixel wide image scaled to a window every few
# hundred milliseconds would freeze the UI, so the preview shows a copy
# thinned to about this width. The full image is what Save writes.
PREVIEW_MAX_WIDTH = 2048

IMAGE_FILTERS = ';;'.join((
    'PNG (*.png)',
    'JPEG (*.jpg *.jpeg)',
    'Bitmap (*.bmp)',
    'TIFF (*.tif *.tiff)'
))


class _PreviewView(QtWidgets.QWidget):
    """Shows the render so far, scaled to fit and keeping its aspect ratio."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`_PreviewView` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        super().__init__(parent)
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                           QtWidgets.QSizePolicy.Policy.Expanding)

        self._image: QtGui.QImage | None = None

        # Chunks can arrive faster than a large image can be scaled and
        # painted, so repaints are coalesced.
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(PREVIEW_REFRESH_MS)
        self._timer.timeout.connect(self.update)

    @_check_types.do
    def set_image(self, image: QtGui.QImage | None) -> None:
        """Show a different image (or none).

        :param image: Image to display. It is shown as is, not copied, so the
            owner can keep writing into its pixels and call :meth:`refresh`.
        :type image: :class:`QtGui.QImage` | None
        """
        self._image = image
        self.update()

    @_check_types.do
    def refresh(self) -> None:
        """Repaint soon, at most once per refresh interval."""
        if not self._timer.isActive():
            self._timer.start()

    @_check_types.do
    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paint the image centred, scaled down or up to fit.

        :param event: Event object.
        :type event: :class:`QtGui.QPaintEvent`
        """
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(PREVIEW_BACKGROUND))

        if self._image is not None:
            size = self._image.size().scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            target = QtCore.QRect(QtCore.QPoint(0, 0), size)
            target.moveCenter(self.rect().center())

            painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(target, self._image)

        painter.end()


class RayTracingDialog(_dialog_base.BaseDialog):
    """Ray tracing settings, plus the image as it renders.

    The settings are the same controls as
    :class:`~harness_designer.ui.dialogs.render_setings.RenderSettingsDialog`.
    Pressing Render takes a snapshot of what the 3D editor is showing (camera
    and visible objects) and renders it on a worker thread; the image fills in
    a band of rows at a time. Settings are saved when a render starts.

    Closing the dialog cancels a render in progress and only hides it, so the
    main window keeps one instance (:meth:`MainFrame.show_ray_tracing`).
    """

    # Emitted from the render thread. The leading int is the run the signal
    # belongs to, so a cancelled render's late results can be ignored.
    chunk_ready = QtCore.Signal(int, int, object, float)
    render_finished = QtCore.Signal(int, bool)
    render_failed = QtCore.Signal(int, str)

    @_check_types.do
    def __init__(self, mainframe: "_ui.MainFrame"):
        """Initialise the :class:`RayTracingDialog` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        super().__init__(
            mainframe, 'Ray Tracing', size=(1400, 800),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Close)

        self._run_id = 0
        self._renderer = None
        self._pixels: np.ndarray | None = None
        self._image: QtGui.QImage | None = None
        self._preview_step = 1
        self._preview_pixels: np.ndarray | None = None

        if sys.platform.startswith('win'):
            self._last_dir = os.path.expandvars('~/Pictures')
        else:
            self._last_dir = os.path.expanduser('~')

        self._last_file = 'new_render.png'

        self.settings_panel = _render_settings.RenderSettingsPanel(self.panel)

        settings_area = QtWidgets.QScrollArea(self.panel)
        settings_area.setWidgetResizable(True)
        settings_area.setFixedWidth(SETTINGS_WIDTH)
        settings_area.setWidget(self.settings_panel)

        self.status_text = QtWidgets.QLabel('Ready', self.panel)
        font = self.status_text.font()
        font.setBold(True)
        self.status_text.setFont(font)
        self.status_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.preview = _PreviewView(self.panel)

        self.progress = QtWidgets.QProgressBar(self.panel)
        self.progress.setRange(0, 100)

        view_lay = QtWidgets.QVBoxLayout()
        view_lay.addWidget(self.status_text)
        view_lay.addWidget(self.preview, 1)
        view_lay.addWidget(self.progress)

        main_lay = QtWidgets.QHBoxLayout(self.panel)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.addWidget(settings_area)
        main_lay.addLayout(view_lay, 1)

        action_role = QtWidgets.QDialogButtonBox.ButtonRole.ActionRole

        self.save_btn = self.button_box.addButton('Save...', action_role)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save)

        self.render_btn = self.button_box.addButton('Render', action_role)
        self.render_btn.clicked.connect(self.on_render)

        self.chunk_ready.connect(self._on_chunk)
        self.render_finished.connect(self._on_finished)
        self.render_failed.connect(self._on_failed)

    @property
    @_check_types.do
    def is_rendering(self) -> bool:
        """Whether a render is in progress.

        :rtype: bool
        """
        return self._renderer is not None

    @_check_types.do
    def get_image(self) -> QtGui.QImage | None:
        """Return the most recent render.

        :returns: The image, or ``None`` when nothing has been rendered.
        :rtype: :class:`QtGui.QImage` | None
        """
        return self._image

    @_check_types.do
    def on_render(self) -> None:
        """Start a render, or cancel the one in progress."""
        if self.is_rendering:
            self._cancel_render()
            self._set_rendering(False)
            self.status_text.setText('Render cancelled')
        else:
            self._start_render()

    @_check_types.do
    def on_save(self) -> None:
        """Ask for a file name and save the image."""
        if self._image is None:
            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save Render', os.path.join(self._last_dir, self._last_file), IMAGE_FILTERS)

        if not path:
            return

        self._last_dir, self._last_file = os.path.split(path)

        if not self._image.save(path):
            self._show_error(f'The image could not be saved to {path}')

    @_check_types.do
    def reject(self) -> None:
        """Cancel any render and hide the dialog."""
        self._cancel_render()
        self._set_rendering(False)
        super().reject()

    @_check_types.do
    def _start_render(self) -> None:
        """Snapshot the 3D editor and start rendering it."""
        self.settings_panel.apply()

        try:
            from ...ray_tracing import renderer as _renderer
            from ...ray_tracing import scene as _scene
            from ...ray_tracing import settings as _settings
        except ImportError:
            self._show_error(
                'Ray tracing needs the pyopencl package and the compiled '
                'ray_tracing/bvh.pyx extension.', traceback.format_exc())
            return

        settings = _settings.RenderSettings.from_config()
        editor3d = self.mainframe.editor3d

        # The canvas is a fixed oversized surface and the editor window shows a centred crop of it;
        # the render has to frame the crop, not the whole surface.
        editor = editor3d.editor
        scene = _scene.Scene(
            settings, editor3d.camera, editor.get_virtual_size(), (editor.width(), editor.height()))

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        try:
            for obj in editor3d.editor.bounds_manager.aabb.visible_objects():
                scene.add_object(obj)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if not scene.object_count:
            self._show_error('There is nothing in the 3D editor to render.')
            return

        self._run_id += 1
        run_id = self._run_id

        try:
            self._renderer = _renderer.Renderer(
                scene,
                lambda start_y, rgb, progress: self.chunk_ready.emit(run_id, start_y, rgb, progress),
                lambda cancelled: self.render_finished.emit(run_id, cancelled),
                lambda err: self.render_failed.emit(
                    run_id, ''.join(traceback.format_exception(err))))
        except Exception:  # NOQA
            self._renderer = None
            self._show_error('Ray tracing could not be started.', traceback.format_exc())
            return

        self._pixels = np.zeros((settings.height, settings.width, 3), dtype=np.uint8)
        self._image = QtGui.QImage(
            self._pixels.data, settings.width, settings.height, settings.width * 3,
            QtGui.QImage.Format.Format_RGB888)

        self._preview_step = max(1, -(-settings.width // PREVIEW_MAX_WIDTH))

        if self._preview_step > 1:
            step = self._preview_step
            preview_w = -(-settings.width // step)
            preview_h = -(-settings.height // step)

            self._preview_pixels = np.zeros((preview_h, preview_w, 3), dtype=np.uint8)
            preview_image = QtGui.QImage(
                self._preview_pixels.data, preview_w, preview_h, preview_w * 3,
                QtGui.QImage.Format.Format_RGB888)
        else:
            self._preview_pixels = None
            preview_image = self._image

        self.preview.set_image(preview_image)
        self.progress.setValue(0)
        self.status_text.setText('Preparing scene...')
        self._set_rendering(True)

        self._renderer.start()

    @_check_types.do
    def _cancel_render(self) -> None:
        """Stop the running render and ignore anything it still reports."""
        if self._renderer is None:
            return

        self._run_id += 1
        self._renderer.cancel()
        self._renderer = None

    @_check_types.do
    def _set_rendering(self, rendering: bool) -> None:
        """Switch the controls between rendering and idle.

        :param rendering: ``True`` while a render is running.
        :type rendering: bool
        """
        self.render_btn.setText('Cancel' if rendering else 'Render')
        self.settings_panel.setEnabled(not rendering)
        self.save_btn.setEnabled(not rendering and self._image is not None)

    @_check_types.do
    def _on_chunk(self, run_id: int, start_y: int, rgb: np.ndarray, progress: float) -> None:
        """Copy a finished band of rows into the image.

        :param run_id: The render this belongs to.
        :type run_id: int
        :param start_y: Top row of the band.
        :type start_y: int
        :param rgb: ``(rows, width, 3)`` uint8 pixels.
        :type rgb: numpy.ndarray
        :param progress: Percent of the render complete.
        :type progress: float
        """
        if run_id != self._run_id:
            return

        self._pixels[start_y:start_y + len(rgb)] = rgb

        step = self._preview_step
        if self._preview_pixels is not None:
            # Keep every step-th row and column; ``first`` is the first row of this band on that grid.
            first = -(-start_y // step) * step
            rows = rgb[first - start_y::step]

            if len(rows):
                self._preview_pixels[first // step:first // step + len(rows)] = rows[:, ::step]

        self.progress.setValue(int(progress))
        self.status_text.setText(f'Ray tracing... {progress:.1f}% complete')
        self.preview.refresh()

    @_check_types.do
    def _on_finished(self, run_id: int, cancelled: bool) -> None:
        """Handle the render thread ending without an error.

        :param run_id: The render this belongs to.
        :type run_id: int
        :param cancelled: Whether it stopped early because it was cancelled.
        :type cancelled: bool
        """
        if run_id != self._run_id:
            return

        self._renderer = None
        self._set_rendering(False)
        self.preview.update()
        self.status_text.setText('Render cancelled' if cancelled else 'Render complete')

    @_check_types.do
    def _on_failed(self, run_id: int, details: str) -> None:
        """Handle the render thread failing.

        :param run_id: The render this belongs to.
        :type run_id: int
        :param details: Traceback of the failure.
        :type details: str
        """
        if run_id != self._run_id:
            return

        self._renderer = None
        self._set_rendering(False)
        self.status_text.setText('Render failed')
        self._show_error('The render failed.', details)

    @_check_types.do
    def _show_error(self, message: str, details: str = '') -> None:
        """Tell the user something went wrong.

        :param message: What went wrong.
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

        dlg = _error.ErrorDialog(self, message, 'Ray Tracing', *widgets)
        try:
            dlg.exec()
        finally:
            dlg.deleteLater()
