# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import sys

import numpy as np

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QProgressBar, QFileDialog, QFrame
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QTimer

from .. import utils as _utils
from ..ui.dialogs import render_setings as _render_settings
from ..ui.dialogs import header as _header
from . import renderer as _renderer
from . import scene as _scene
from .. import config as _config


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.ray_trace


class RayTracingDialog(QDialog):

    def __init__(self, parent: "_ui.MainFrame", title="Ray Tracing Progress"):
        self._parent = parent
        super().__init__(parent, Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setWindowTitle('')
        self.resize(1200, 650)

        if sys.platform.startswith('win'):
            last_saved_dir = os.path.expandvars('~/Pictures')
        else:
            last_saved_dir = os.path.expanduser('~')

        self.last_saved_dir = last_saved_dir
        self.last_saved_file = 'new_render.png'

        self.cancelled = False
        self.current_image: QImage = None

        lay = QVBoxLayout(self)

        # Header widget (converted in Phase 2 dialogs)
        self.header_lbl = _header.Header(self, title)
        lay.addWidget(self.header_lbl)

        self.status_text = QLabel("Initializing ray tracer...", self)
        font = self.status_text.font()
        font.setBold(True)
        self.status_text.setFont(font)
        self.status_text.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status_text)

        self.image_label = QLabel(self)
        self.image_label.setFixedSize(1180, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet('background-color: #2d3135;')
        lay.addWidget(self.image_label, 0, Qt.AlignHCenter)

        prog_row = QHBoxLayout()
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        prog_row.addWidget(self.progress, 1)
        self.progress_text = QLabel("0%", self)
        prog_row.addWidget(self.progress_text)
        lay.addLayout(prog_row)

        hline = QFrame(self)
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)
        lay.addWidget(hline)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.settings_btn = QPushButton("Settings", self)
        self.settings_btn.clicked.connect(self.on_settings)
        btn_row.addWidget(self.settings_btn)

        vline = QFrame(self)
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        btn_row.addWidget(vline)

        self.mfb1 = QPushButton("Close", self)
        self.mfb1.clicked.connect(self.on_mfb1)
        btn_row.addWidget(self.mfb1)

        self.mfb2 = QPushButton("Start", self)
        self.mfb2.clicked.connect(self.on_mfb2)
        btn_row.addWidget(self.mfb2)

        lay.addLayout(btn_row)

        self.adjustSize()
        if parent:
            self.move(
                parent.mapToGlobal(parent.rect().center()) -
                self.rect().center()
            )

    def on_settings(self):
        dlg = _render_settings.RenderSettingsDialog(self)
        dlg.exec()

    def on_mfb2(self):
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

            self.current_image = QImage(width, height, QImage.Format_RGB888)
            self.current_image.fill(QColor(0, 0, 0))

            scene = _scene.Scene(width, height, self._parent.editor3d.camera)

            if Config.environment_map.enable:
                if Config.environment_map.generate or not Config.environment_map.path:
                    scene.generate_environment((width, height))
                elif Config.environment_map.path:
                    scene.load_environment_map(Config.environment_map.path)

            for obj in self._parent.editor3d.camera.objects_in_view:
                scene.add_object(obj.obj3d)

            renderer = _renderer.Renderer(scene, self.update_progress)
            renderer.start()

        elif label == 'Cancel':
            self.cancelled = True
            self.mfb2.setText('Start')
            self.mfb1.setText('Close')
            self.current_image = None
            self.mfb1.setEnabled(True)
            self.settings_btn.setEnabled(True)

    def on_mfb1(self):
        label = self.mfb1.text()

        if label == 'Close':
            self.cancelled = True
            self.reject()
        elif label == 'Save':
            self.mfb1.setText('Close')
            self.mfb2.setText('Start')

            path, _ = QFileDialog.getSaveFileName(
                self, 'Save Render',
                os.path.join(self.last_saved_dir, self.last_saved_file),
                "Images (*.png *.jpg *.bmp *.tiff)"
            )

            if path:
                self.last_saved_dir, self.last_saved_file = os.path.split(path)
                if self.current_image:
                    self.current_image.save(path)

    def update_progress(self, start_y, image_array, progress):
        if self.cancelled:
            self.cancelled = False
            return False

        height, width = image_array.shape[:2]
        # image_array is expected to be uint8 RGB
        rgb = np.ascontiguousarray(image_array[:, :, :3])
        row_bytes = width * 3
        patch = QImage(rgb.data, width, height, row_bytes, QImage.Format_RGB888)

        painter = QPainter(self.current_image)
        painter.drawImage(0, start_y, patch)
        painter.end()

        QTimer.singleShot(0, lambda: self._update_ui(progress))

        return not self.cancelled

    def _update_ui(self, progress):
        self.progress.setValue(int(progress))
        self.progress_text.setText(f"{progress:.1f}%")
        self.status_text.setText(f"Ray tracing... {progress:.1f}% complete")

        # Scale current_image to fit the label
        if self.current_image:
            pm = QPixmap.fromImage(self.current_image)
            pm = pm.scaled(self.image_label.size(),
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pm)

        if progress >= 100:
            self.status_text.setText("Render complete!")
            self.mfb1.setText('Save')
            self.mfb1.setEnabled(True)
            self.mfb2.setText('Start')
            self.settings_btn.setEnabled(True)

    def get_image(self):
        return self.current_image
