# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from . import dialog_base as _dialog_base
from ... import config as _config

Config = _config.Config.ray_trace


class RenderSettingsDialog(_dialog_base.BaseDialog):
    """Represent a render settings dialog in :mod:`harness_designer.ui.dialogs.render_setings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`RenderSettingsDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, title='Render Settings', size=(-1, 600))

        panel = self.panel
        main_sizer = QtWidgets.QVBoxLayout(panel)

        # Resolution
        res_row = QtWidgets.QHBoxLayout()
        res_row.addWidget(QtWidgets.QLabel('Resolution:', panel))
        self.resolution = QtWidgets.QComboBox(panel)
        choices = [res['label'] for res in Config.resolutions]
        self.resolution.addItems(choices)

        idx = self.resolution.findText(Config.default_resolution)
        if idx >= 0:
            self.resolution.setCurrentIndex(idx)

        res_row.addWidget(self.resolution)
        main_sizer.addLayout(res_row)

        # Background group
        bg_box = QtWidgets.QGroupBox("Background", panel)
        bg_lay = QtWidgets.QVBoxLayout(bg_box)

        grad_row = QtWidgets.QHBoxLayout()
        grad_row.addWidget(QtWidgets.QLabel('Use Gradient Background:', bg_box))
        self.gradient_check = QtWidgets.QCheckBox(bg_box)
        self.gradient_check.setChecked(Config.background.enable_gradient)
        grad_row.addWidget(self.gradient_check)
        bg_lay.addLayout(grad_row)

        env_row = QtWidgets.QHBoxLayout()
        env_row.addWidget(QtWidgets.QLabel('Use Environment Map:', bg_box))
        self.envmap_check = QtWidgets.QCheckBox(bg_box)
        self.envmap_check.setChecked(Config.environment_map.enable)
        env_row.addWidget(self.envmap_check)
        bg_lay.addLayout(env_row)

        gen_row = QtWidgets.QHBoxLayout()
        gen_row.addWidget(QtWidgets.QLabel('Generate Environment Map:', bg_box))
        self.gen_check = QtWidgets.QCheckBox(bg_box)
        self.gen_check.setChecked(Config.environment_map.generate)
        gen_row.addWidget(self.gen_check)
        bg_lay.addLayout(gen_row)

        load_env_btn = QtWidgets.QPushButton("Load Environment Map...", bg_box)
        load_env_btn.clicked.connect(self.on_load_envmap)
        bg_lay.addWidget(load_env_btn)

        main_sizer.addWidget(bg_box)

        # Effects group
        effects_box = QtWidgets.QGroupBox("Effects", panel)
        effects_lay = QtWidgets.QVBoxLayout(effects_box)

        refl_row = QtWidgets.QHBoxLayout()
        refl_row.addWidget(QtWidgets.QLabel('Enable Reflections:', effects_box))
        self.reflections_check = QtWidgets.QCheckBox(effects_box)
        self.reflections_check.setChecked(Config.enable_reflections)
        refl_row.addWidget(self.reflections_check)
        effects_lay.addLayout(refl_row)

        shad_row = QtWidgets.QHBoxLayout()
        shad_row.addWidget(QtWidgets.QLabel('Enable Shadows:', effects_box))
        self.shadows_check = QtWidgets.QCheckBox(effects_box)
        self.shadows_check.setChecked(Config.shadows.enable)
        shad_row.addWidget(self.shadows_check)
        effects_lay.addLayout(shad_row)

        main_sizer.addWidget(effects_box)

        # Ambient Occlusion group
        ao_box = QtWidgets.QGroupBox("Ambient Occlusion", panel)
        ao_lay = QtWidgets.QVBoxLayout(ao_box)

        ao_en_row = QtWidgets.QHBoxLayout()
        ao_en_row.addWidget(QtWidgets.QLabel('Enable', ao_box))
        self.ao_check = QtWidgets.QCheckBox(ao_box)
        self.ao_check.setChecked(Config.ambient_occlusion.enable)
        ao_en_row.addWidget(self.ao_check)
        ao_lay.addLayout(ao_en_row)

        ao_samp_row = QtWidgets.QHBoxLayout()
        ao_samp_row.addWidget(QtWidgets.QLabel('Samples:', ao_box))
        self.ao_samples_spin = QtWidgets.QSpinBox(ao_box)
        self.ao_samples_spin.setRange(4, 64)
        self.ao_samples_spin.setValue(int(Config.ambient_occlusion.samples))
        ao_samp_row.addWidget(self.ao_samples_spin)
        ao_lay.addLayout(ao_samp_row)

        ao_rad_row = QtWidgets.QHBoxLayout()
        ao_rad_row.addWidget(QtWidgets.QLabel('Radius:', ao_box))
        self.ao_radius_spin = QtWidgets.QDoubleSpinBox(ao_box)
        self.ao_radius_spin.setRange(0.1, 5.0)
        self.ao_radius_spin.setSingleStep(0.1)
        self.ao_radius_spin.setValue(Config.ambient_occlusion.radius)
        ao_rad_row.addWidget(self.ao_radius_spin)
        ao_lay.addLayout(ao_rad_row)

        main_sizer.addWidget(ao_box)

        # Lighting group
        lighting_box = QtWidgets.QGroupBox("Lighting", panel)
        lighting_lay = QtWidgets.QVBoxLayout(lighting_box)

        amb_row = QtWidgets.QHBoxLayout()
        amb_row.addWidget(QtWidgets.QLabel('Ambient Intensity:', lighting_box))
        self.ambient_spin = QtWidgets.QDoubleSpinBox(lighting_box)
        self.ambient_spin.setRange(0.0, 1.0)
        self.ambient_spin.setSingleStep(0.05)
        self.ambient_spin.setValue(Config.lighting.ambient_intensity)
        amb_row.addWidget(self.ambient_spin)
        lighting_lay.addLayout(amb_row)

        self.lights = LightingPanel(lighting_box)
        lighting_lay.addWidget(self.lights)

        main_sizer.addWidget(lighting_box)

        # Connect OK to on_apply
        self.button_box.accepted.disconnect()
        self.button_box.accepted.connect(self.on_apply)

    def on_load_envmap(self):
        """Handle the load envmap event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load Environment Map', '',
            'Image files (*.jpg *.png *.hdr *.bmp)')

        if path:
            Config.environment_map.path = path
            self.gen_check.setChecked(False)
            self.envmap_check.setChecked(True)

    def on_apply(self):
        """Handle the apply event.

        UNKNOWN details are inferred from the callable name and signature.
        """
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


class LightingPanel(QtWidgets.QWidget):
    """Represent a lighting panel in :mod:`harness_designer.ui.dialogs.render_setings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`LightingPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent)

        self.lights_panel = LightsPanel(self, Config.lighting.lights)

        self.add_btn = QtWidgets.QPushButton('Add Light', self)
        self.remove_btn = QtWidgets.QPushButton('Remove Light', self)

        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

        inner = QtWidgets.QHBoxLayout()
        inner.addWidget(self.lights_panel, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(inner)
        lay.addLayout(btn_row)

    def on_add(self):
        """Handle the add event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.lights_panel.add_light()

    def on_remove(self):
        """Handle the remove event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.lights_panel.remove_item()

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.lights_panel.GetValue()


class LightsPanel(QtWidgets.QScrollArea):
    """Represent a lights panel in :mod:`harness_designer.ui.dialogs.render_setings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, lights):
        """Initialise the :class:`LightsPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param lights: Value for ``lights``.
        :type lights: UNKNOWN
        """
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.Box)

        self._container = QtWidgets.QWidget()
        self.main_sizer = QtWidgets.QVBoxLayout(self._container)
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
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return [light.GetValue() for light in self.items]

    def add_light(self):
        """Add a light.

        UNKNOWN details are inferred from the callable name and signature.
        """
        light = LightItem(self._container,
                          position=[0.0, 0.0, 0.0],
                          intensity=1.0,
                          color=[0.0, 0.0, 0.0])

        light.clicked_signal.connect(lambda i=light: self._set_selected(i))
        self.items.append(light)
        self.main_sizer.addWidget(light)

    def remove_item(self):
        """Remove the item.

        UNKNOWN details are inferred from the callable name and signature.
        """
        if self.selected is None:
            return

        index = self.items.index(self.selected)
        self.items.pop(index)
        self.selected.setParent(None)
        self.selected.deleteLater()
        self.selected = None

    def _set_selected(self, light):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param light: Value for ``light``.
        :type light: UNKNOWN
        """
        if self.selected is not None:
            self.selected.unselect()
        self.selected = light
        light.select()


def _item_row(parent, label_text, ctrl):
    """Execute the item row operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param parent: Parent object.
    :type parent: UNKNOWN
    :param label_text: Value for ``label_text``.
    :type label_text: UNKNOWN
    :param ctrl: Value for ``ctrl``.
    :type ctrl: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    row = QtWidgets.QHBoxLayout()
    row.addWidget(QtWidgets.QLabel(label_text, parent))
    row.addWidget(ctrl, 1)
    return row


class LightItem(QtWidgets.QWidget):
    """Represent a light item in :mod:`harness_designer.ui.dialogs.render_setings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    clicked_signal: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent, position, intensity, color):
        """Initialise the :class:`LightItem` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param position: Position value.
        :type position: UNKNOWN
        :param intensity: Value for ``intensity``.
        :type intensity: UNKNOWN
        :param color: Value for ``color``.
        :type color: UNKNOWN
        """
        super().__init__(parent)
        self._unselected_bg = self.palette().color(self.backgroundRole())

        x, y, z = position

        self.x_ctrl = QtWidgets.QDoubleSpinBox(self)
        self.x_ctrl.setRange(-99999.0, 99999.0)
        self.x_ctrl.setSingleStep(0.5)
        self.x_ctrl.setValue(float(x))

        self.y_ctrl = QtWidgets.QDoubleSpinBox(self)
        self.y_ctrl.setRange(-99999.0, 99999.0)
        self.y_ctrl.setSingleStep(0.5)
        self.y_ctrl.setValue(float(y))

        self.z_ctrl = QtWidgets.QDoubleSpinBox(self)
        self.z_ctrl.setRange(-99999.0, 99999.0)
        self.z_ctrl.setSingleStep(0.5)
        self.z_ctrl.setValue(float(z))

        self.intensity_ctrl = QtWidgets.QDoubleSpinBox(self)
        self.intensity_ctrl.setRange(0.001, 1.0)
        self.intensity_ctrl.setSingleStep(0.001)
        self.intensity_ctrl.setValue(float(intensity))

        # Color as a button that opens a color dialog
        self._color = color
        self.color_btn = QtWidgets.QPushButton(self)
        r, g, b = (int(c * 255) for c in color)

        self.color_btn.setStyleSheet(
            f'background-color: rgb({r},{g},{b}); min-width:40px;')

        self.color_btn.clicked.connect(self._pick_color)

        row = QtWidgets.QHBoxLayout(self)
        row.addLayout(_item_row(self, 'X:', self.x_ctrl))
        row.addLayout(_item_row(self, 'Y:', self.y_ctrl))
        row.addLayout(_item_row(self, 'Z:', self.z_ctrl))

        row.addLayout(_item_row(
            self, 'Intensity:', self.intensity_ctrl))

        row.addWidget(self.color_btn)

    def _pick_color(self):
        """Execute the pick color operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        r, g, b = (int(c * 255) for c in self._color)

        chosen = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(r, g, b), self, "Light colour")

        if chosen.isValid():
            self._color = [chosen.red() / 255.0,
                           chosen.green() / 255.0,
                           chosen.blue() / 255.0]

            self.color_btn.setStyleSheet(
                f'background-color: {chosen.name()}; min-width:40px;')

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return dict(
            position=[self.x_ctrl.value(),
                      self.y_ctrl.value(),
                      self.z_ctrl.value()],
            intensity=self.intensity_ctrl.value(),
            color=list(self._color)
        )

    def select(self):
        """Execute the select operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.setStyleSheet('background-color: palette(highlight);')

    def unselect(self):
        """Execute the unselect operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.setStyleSheet('')

    def mousePressEvent(self, event):
        """Execute the mouse press event operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param event: Event object.
        :type event: UNKNOWN
        """
        self.clicked_signal.emit()
        super().mousePressEvent(event)
