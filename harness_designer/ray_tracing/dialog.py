# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Dialog helpers for configuring, running, and previewing ray-tracing renders.
"""

from typing import TYPE_CHECKING, Union as _Union

import os
import sys
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from .. import utils as _utils
from ..ui.dialogs import render_setings as _render_settings
from ..ui.dialogs import header as _header
from . import renderer as _renderer
from . import scene as _scene
from .. import config as _config
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.ray_trace


class RayTracingDialog(QtWidgets.QDialog):

    """Display render progress, preview the current image, and expose save/settings actions for the ray tracer.
    """
    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame", title: str = "Ray Tracing Progress") -> None:
        """Initialize the object and capture the state required for later interaction.

        :param parent: Owning main window or parent widget.
        :type parent: "_ui.MainFrame"
        :param title: Dialog title text shown in the custom header.
        :type title: str
        """
        self._parent = parent
        super().__init__(parent, QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle('')
        self.resize(1200, 650)

        if sys.platform.startswith('win'):
            last_saved_dir = os.path.expandvars('~/Pictures')
        else:
            last_saved_dir = os.path.expanduser('~')

        self.last_saved_dir = last_saved_dir
        self.last_saved_file = 'new_render.png'

        self.cancelled = False
        self.current_image: QtGui.QImage = None

        lay = QtWidgets.QVBoxLayout(self)

        # Header widget (converted in Phase 2 dialogs)
        self.header_lbl = _header.Header(self, title)
        lay.addWidget(self.header_lbl)

        self.status_text = QtWidgets.QLabel("Initializing ray tracer...", self)
        font = self.status_text.font()
        font.setBold(True)
        self.status_text.setFont(font)
        self.status_text.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.status_text)

        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setFixedSize(1180, 480)
        self.image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #2d3135;')
        lay.addWidget(self.image_label, 0, QtCore.Qt.AlignHCenter)

        prog_row = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setRange(0, 100)
        prog_row.addWidget(self.progress, 1)
        self.progress_text = QtWidgets.QLabel("0%", self)
        prog_row.addWidget(self.progress_text)
        lay.addLayout(prog_row)

        hline = QtWidgets.QFrame(self)
        hline.setFrameShape(QtWidgets.QFrame.HLine)
        hline.setFrameShadow(QtWidgets.QFrame.Sunken)
        lay.addWidget(hline)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        self.settings_btn = QtWidgets.QPushButton("Settings", self)
        self.settings_btn.clicked.connect(self.on_settings)
        btn_row.addWidget(self.settings_btn)

        vline = QtWidgets.QFrame(self)
        vline.setFrameShape(QtWidgets.QFrame.VLine)
        vline.setFrameShadow(QtWidgets.QFrame.Sunken)
        btn_row.addWidget(vline)

        self.mfb1 = QtWidgets.QPushButton("Close", self)
        self.mfb1.clicked.connect(self.on_mfb1)
        btn_row.addWidget(self.mfb1)

        self.mfb2 = QtWidgets.QPushButton("Start", self)
        self.mfb2.clicked.connect(self.on_mfb2)
        btn_row.addWidget(self.mfb2)

        lay.addLayout(btn_row)

        self.adjustSize()
        if parent:
            self.move(
                parent.mapToGlobal(parent.rect().center()) -
                self.rect().center()
            )

    @_check_types.do
    def on_settings(self) -> None:
        """Open the render settings dialog for the current operation.
        """
        dlg = _render_settings.RenderSettingsDialog(self)
        dlg.exec()

    @_check_types.do
    def on_mfb2(self) -> None:
        """Handle the secondary action button. UNKNOWN button naming details.
        """
        label = self.mfb2.text()
        if label == 'Start':
            self.mfb2.setText('Cancel')
            self.mfb1.setText('Save')
            self.mfb1.setEnabled(False)
            self.settings_btn.setEnabled(False)

            for res in Config.resolutions:
                if res['label'] == Config.default_resolution:
                    break
            else:
                res = dict(width=1920, height=1080)

            width = res['width']
            height = res['height']

            self.current_image = QtGui.QImage(width, height, QtGui.QImage.Format_RGB888)
            self.current_image.fill(QtGui.QColor(0, 0, 0))

            scene = _scene.Scene(width, height, self._parent.editor3d.camera)

            if Config.environment_map.enable:
                if Config.environment_map.generate or not Config.environment_map.path:
                    scene.generate_environment((width, height))
                elif Config.environment_map.path:
                    scene.load_environment_map(Config.environment_map.path)

            for view in self._parent.editor3d.editor.bounds_manager.aabb.visible_objects():
                scene.add_object(view)

            renderer = _renderer.Renderer(scene, self.update_progress)
            renderer.start()

        elif label == 'Cancel':
            self.cancelled = True
            self.mfb2.setText('Start')
            self.mfb1.setText('Close')
            self.current_image = None
            self.mfb1.setEnabled(True)
            self.settings_btn.setEnabled(True)

    @_check_types.do
    def on_mfb1(self) -> None:
        """Handle the primary action button. UNKNOWN button naming details.
        """
        label = self.mfb1.text()

        if label == 'Close':
            self.cancelled = True
            self.reject()
        elif label == 'Save':
            self.mfb1.setText('Close')
            self.mfb2.setText('Start')

            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, 'Save Render',
                os.path.join(self.last_saved_dir, self.last_saved_file),
                "Images (*.png *.jpg *.bmp *.tiff)"
            )

            if path:
                self.last_saved_dir, self.last_saved_file = os.path.split(path)
                if self.current_image:
                    self.current_image.save(path)

    @_check_types.do
    def update_progress(self, start_y: int, image_array: np.ndarray, progress: float) -> bool:
        """Update the render image with a newly completed chunk and schedule a UI refresh.

        :param start_y: Top row index of the rendered image chunk.
        :type start_y: int
        :param image_array: Rendered RGB image chunk represented as a NumPy array.
        :type image_array: numpy.ndarray
        :param progress: Current completion percentage for the render operation.
        :type progress: float
        :returns: The result of the operation. UNKNOWN exact semantics when not inferable from the current source.
        """
        if self.cancelled:
            self.cancelled = False
            return False

        height, width = image_array.shape[:2]
        # image_array is expected to be uint8 RGB
        rgb = np.ascontiguousarray(image_array[:, :, :3])
        row_bytes = width * 3
        patch = QtGui.QImage(rgb.data, width, height, row_bytes, QtGui.QImage.Format_RGB888)

        painter = QtGui.QPainter(self.current_image)
        painter.drawImage(0, start_y, patch)
        painter.end()

        QtCore.QTimer.singleShot(0, lambda: self._update_ui(progress))

        return not self.cancelled

    @_check_types.do
    def _update_ui(self, progress: float) -> None:
        """Refresh the visible progress widgets and preview image for the current render.

        :param progress: Current completion percentage for the render operation.
        :type progress: float
        """
        self.progress.setValue(int(progress))
        self.progress_text.setText(f"{progress:.1f}%")
        self.status_text.setText(f"Ray tracing... {progress:.1f}% complete")

        # Scale current_image to fit the label
        if self.current_image:
            pm = QtGui.QPixmap.fromImage(self.current_image)
            pm = pm.scaled(self.image_label.size(),
                           QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.image_label.setPixmap(pm)

        if progress >= 100:
            self.status_text.setText("Render complete!")
            self.mfb1.setText('Save')
            self.mfb1.setEnabled(True)
            self.mfb2.setText('Start')
            self.settings_btn.setEnabled(True)

    @_check_types.do
    def get_image(self) -> _Union["QtGui.QImage", None]:
        """Return the most recently rendered image stored by the dialog.

        :returns: The current :class:`~PySide6.QtGui.QImage` instance or :data:`None` when no render is available.
        :rtype: QtGui.QImage | None
        """
        return self.current_image
