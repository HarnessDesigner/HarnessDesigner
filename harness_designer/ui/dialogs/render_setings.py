# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QCheckBox,
    QComboBox, QPushButton, QSpinBox, QDoubleSpinBox, QScrollArea,
    QWidget, QFrame, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from . import dialog_base as _dialog_base
from ... import config as _config

Config = _config.Config.ray_trace


class RenderSettingsDialog(_dialog_base.BaseDialog):

    def __init__(self, parent):
        super().__init__(parent, title='Render Settings', size=(-1, 600))

        panel = self.panel
        main_sizer = QVBoxLayout(panel)

        # Resolution
        res_row = QHBoxLayout()
        res_row.addWidget(QLabel('Resolution:', panel))
        self.resolution = QComboBox(panel)
        choices = [res['label'] for res in Config.resolutions]
        self.resolution.addItems(choices)
        idx = self.resolution.findText(Config.default_resolution)
        if idx >= 0:
            self.resolution.setCurrentIndex(idx)
        res_row.addWidget(self.resolution)
        main_sizer.addLayout(res_row)

        # Background group
        bg_box = QGroupBox("Background", panel)
        bg_lay = QVBoxLayout(bg_box)

        grad_row = QHBoxLayout()
        grad_row.addWidget(QLabel('Use Gradient Background:', bg_box))
        self.gradient_check = QCheckBox(bg_box)
        self.gradient_check.setChecked(Config.background.enable_gradient)
        grad_row.addWidget(self.gradient_check)
        bg_lay.addLayout(grad_row)

        env_row = QHBoxLayout()
        env_row.addWidget(QLabel('Use Environment Map:', bg_box))
        self.envmap_check = QCheckBox(bg_box)
        self.envmap_check.setChecked(Config.environment_map.enable)
        env_row.addWidget(self.envmap_check)
        bg_lay.addLayout(env_row)

        gen_row = QHBoxLayout()
        gen_row.addWidget(QLabel('Generate Environment Map:', bg_box))
        self.gen_check = QCheckBox(bg_box)
        self.gen_check.setChecked(getattr(Config.environment_map, 'generate', False))
        gen_row.addWidget(self.gen_check)
        bg_lay.addLayout(gen_row)

        load_env_btn = QPushButton("Load Environment Map...", bg_box)
        load_env_btn.clicked.connect(self.on_load_envmap)
        bg_lay.addWidget(load_env_btn)

        main_sizer.addWidget(bg_box)

        # Effects group
        effects_box = QGroupBox("Effects", panel)
        effects_lay = QVBoxLayout(effects_box)

        refl_row = QHBoxLayout()
        refl_row.addWidget(QLabel('Enable Reflections:', effects_box))
        self.reflections_check = QCheckBox(effects_box)
        self.reflections_check.setChecked(Config.enable_reflections)
        refl_row.addWidget(self.reflections_check)
        effects_lay.addLayout(refl_row)

        shad_row = QHBoxLayout()
        shad_row.addWidget(QLabel('Enable Shadows:', effects_box))
        self.shadows_check = QCheckBox(effects_box)
        self.shadows_check.setChecked(Config.shadows.enable)
        shad_row.addWidget(self.shadows_check)
        effects_lay.addLayout(shad_row)

        main_sizer.addWidget(effects_box)

        # Ambient Occlusion group
        ao_box = QGroupBox("Ambient Occlusion", panel)
        ao_lay = QVBoxLayout(ao_box)

        ao_en_row = QHBoxLayout()
        ao_en_row.addWidget(QLabel('Enable', ao_box))
        self.ao_check = QCheckBox(ao_box)
        self.ao_check.setChecked(Config.ambient_occlusion.enable)
        ao_en_row.addWidget(self.ao_check)
        ao_lay.addLayout(ao_en_row)

        ao_samp_row = QHBoxLayout()
        ao_samp_row.addWidget(QLabel('Samples:', ao_box))
        self.ao_samples_spin = QSpinBox(ao_box)
        self.ao_samples_spin.setRange(4, 64)
        self.ao_samples_spin.setValue(int(Config.ambient_occlusion.samples))
        ao_samp_row.addWidget(self.ao_samples_spin)
        ao_lay.addLayout(ao_samp_row)

        ao_rad_row = QHBoxLayout()
        ao_rad_row.addWidget(QLabel('Radius:', ao_box))
        self.ao_radius_spin = QDoubleSpinBox(ao_box)
        self.ao_radius_spin.setRange(0.1, 5.0)
        self.ao_radius_spin.setSingleStep(0.1)
        self.ao_radius_spin.setValue(Config.ambient_occlusion.radius)
        ao_rad_row.addWidget(self.ao_radius_spin)
        ao_lay.addLayout(ao_rad_row)

        main_sizer.addWidget(ao_box)

        # Lighting group
        lighting_box = QGroupBox("Lighting", panel)
        lighting_lay = QVBoxLayout(lighting_box)

        amb_row = QHBoxLayout()
        amb_row.addWidget(QLabel('Ambient Intensity:', lighting_box))
        self.ambient_spin = QDoubleSpinBox(lighting_box)
        self.ambient_spin.setRange(0.0, 1.0)
        self.ambient_spin.setSingleStep(0.05)
        self.ambient_spin.setValue(Config.lighting.intensity)
        amb_row.addWidget(self.ambient_spin)
        lighting_lay.addLayout(amb_row)

        self.lights = LightingPanel(lighting_box)
        lighting_lay.addWidget(self.lights)

        main_sizer.addWidget(lighting_box)

        # Connect OK to on_apply
        self.button_box.accepted.disconnect()
        self.button_box.accepted.connect(self.on_apply)

    def on_load_envmap(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Environment Map",
            "",
            "Image files (*.jpg *.png *.hdr *.bmp)"
        )
        if path:
            Config.environment_map.path = path
            self.gen_check.setChecked(False)
            self.envmap_check.setChecked(True)

    def on_apply(self):
        Config.background.enable_gradient = self.gradient_check.isChecked()
        Config.environment_map.enable = self.envmap_check.isChecked()
        Config.enable_reflections = self.reflections_check.isChecked()
        Config.shadows.enable = self.shadows_check.isChecked()
        Config.ambient_occlusion.enable = self.ao_check.isChecked()
        Config.ambient_occlusion.samples = float(self.ao_samples_spin.value())
        Config.ambient_occlusion.radius = self.ao_radius_spin.value()
        Config.lighting.intensity = self.ambient_spin.value()
        Config.environment_map.generate = self.gen_check.isChecked()
        Config.default_resolution = self.resolution.currentText()
        Config.lighting.lights = self.lights.GetValue()
        self.accept()


class LightingPanel(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.lights_panel = LightsPanel(self, Config.lighting.lights)

        self.add_btn = QPushButton('Add Light', self)
        self.remove_btn = QPushButton('Remove Light', self)

        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

        inner = QHBoxLayout()
        inner.addWidget(self.lights_panel, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(inner)
        lay.addLayout(btn_row)

    def on_add(self):
        self.lights_panel.add_light()

    def on_remove(self):
        self.lights_panel.remove_item()

    def GetValue(self):
        return self.lights_panel.GetValue()


class LightsPanel(QScrollArea):

    def __init__(self, parent, lights):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Box)

        self._container = QWidget()
        self.main_sizer = QVBoxLayout(self._container)
        self.setWidget(self._container)

        self.lights_data = lights
        self.items = []
        self.selected = None

        for light in lights:
            item = LightItem(self._container, **light)
            item.clicked_signal.connect(lambda i=item: self._set_selected(i))
            self.items.append(item)
            self.main_sizer.addWidget(item)

    def GetValue(self):
        return [light.GetValue() for light in self.items]

    def add_light(self):
        light = LightItem(self._container,
                          position=[0.0, 0.0, 0.0],
                          intensity=1.0,
                          color=[0.0, 0.0, 0.0])
        light.clicked_signal.connect(lambda i=light: self._set_selected(i))
        self.items.append(light)
        self.main_sizer.addWidget(light)

    def remove_item(self):
        if self.selected is None:
            return

        index = self.items.index(self.selected)
        self.items.pop(index)
        self.selected.setParent(None)
        self.selected.deleteLater()
        self.selected = None

    def _set_selected(self, light):
        if self.selected is not None:
            self.selected.unselect()
        self.selected = light
        light.select()


def _item_row(parent, label_text, ctrl):
    row = QHBoxLayout()
    row.addWidget(QLabel(label_text, parent))
    row.addWidget(ctrl, 1)
    return row


class LightItem(QWidget):
    from PySide6.QtCore import Signal
    clicked_signal = __import__('PySide6').QtCore.Signal()

    def __init__(self, parent, position, intensity, color):
        super().__init__(parent)
        self._unselected_bg = self.palette().color(self.backgroundRole())

        x, y, z = position

        self.x_ctrl = QDoubleSpinBox(self)
        self.x_ctrl.setRange(-99999.0, 99999.0)
        self.x_ctrl.setSingleStep(0.5)
        self.x_ctrl.setValue(float(x))

        self.y_ctrl = QDoubleSpinBox(self)
        self.y_ctrl.setRange(-99999.0, 99999.0)
        self.y_ctrl.setSingleStep(0.5)
        self.y_ctrl.setValue(float(y))

        self.z_ctrl = QDoubleSpinBox(self)
        self.z_ctrl.setRange(-99999.0, 99999.0)
        self.z_ctrl.setSingleStep(0.5)
        self.z_ctrl.setValue(float(z))

        self.intensity_ctrl = QDoubleSpinBox(self)
        self.intensity_ctrl.setRange(0.001, 1.0)
        self.intensity_ctrl.setSingleStep(0.001)
        self.intensity_ctrl.setValue(float(intensity))

        # Color as a button that opens a color dialog
        from PySide6.QtWidgets import QPushButton, QColorDialog
        self._color = color
        self.color_btn = QPushButton(self)
        r, g, b = (int(c * 255) for c in color)
        self.color_btn.setStyleSheet(
            f'background-color: rgb({r},{g},{b}); min-width:40px;')
        self.color_btn.clicked.connect(self._pick_color)

        row = QHBoxLayout(self)
        row.addLayout(_item_row(self, 'X:', self.x_ctrl))
        row.addLayout(_item_row(self, 'Y:', self.y_ctrl))
        row.addLayout(_item_row(self, 'Z:', self.z_ctrl))
        row.addLayout(_item_row(self, 'Intensity:', self.intensity_ctrl))
        row.addWidget(self.color_btn)

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        r, g, b = (int(c * 255) for c in self._color)
        chosen = QColorDialog.getColor(QColor(r, g, b), self, "Light colour")
        if chosen.isValid():
            self._color = [chosen.red() / 255.0,
                           chosen.green() / 255.0,
                           chosen.blue() / 255.0]
            self.color_btn.setStyleSheet(
                f'background-color: {chosen.name()}; min-width:40px;')

    def GetValue(self):
        return dict(
            position=[self.x_ctrl.value(),
                      self.y_ctrl.value(),
                      self.z_ctrl.value()],
            intensity=self.intensity_ctrl.value(),
            color=list(self._color)
        )

    def select(self):
        self.setStyleSheet('background-color: palette(highlight);')

    def unselect(self):
        self.setStyleSheet('')

    def mousePressEvent(self, event):
        self.clicked_signal.emit()
        super().mousePressEvent(event)
