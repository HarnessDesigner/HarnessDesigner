# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets
from PySide6 import QtGui
from PySide6 import QtCore

from ..widgets import float_ctrl as _float_ctrl
from . import dialog_base as _dialog_base
from ... import config as _config
from ... import check_types as _check_types

Config = _config.Config.ray_trace

# World-space limits and step for a light's X/Y/Z, and its intensity range. FloatCtrl derives its
# decimal places from the step, and a step of 1 or more gives it no slider range, so keep them below 1.
POSITION_LIMIT = 5000.0
POSITION_STEP = 0.5
INTENSITY_MIN = 0.001
INTENSITY_MAX = 1.0
INTENSITY_STEP = 0.001


class RenderSettingsPanel(QtWidgets.QWidget):
    """The ray-trace settings controls (resolution, background, effects, ambient occlusion, lighting).

    Reads ``Config.ray_trace`` when it is built and writes it back in :meth:`apply`; nothing is saved
    before that. Embedded by :class:`RenderSettingsDialog` and by
    :class:`~harness_designer.ui.dialogs.ray_tracing_dialog.RayTracingDialog`.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`RenderSettingsPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        super().__init__(parent)

        self._envmap_path = Config.environment_map.path

        main_sizer = QtWidgets.QVBoxLayout(self)
        main_sizer.setContentsMargins(0, 0, 0, 0)

        # Resolution
        res_row = QtWidgets.QHBoxLayout()
        res_row.addWidget(QtWidgets.QLabel('Resolution:', self))
        self.resolution = QtWidgets.QComboBox(self)
        choices = [res['label'] for res in Config.resolutions]
        self.resolution.addItems(choices)

        idx = self.resolution.findText(Config.default_resolution)
        if idx >= 0:
            self.resolution.setCurrentIndex(idx)

        res_row.addWidget(self.resolution, 1)
        main_sizer.addLayout(res_row)

        # Background group
        bg_box = QtWidgets.QGroupBox("Background", self)
        bg_lay = QtWidgets.QVBoxLayout(bg_box)

        self.viewport_check = QtWidgets.QCheckBox('Match Viewport (background and floor)', bg_box)
        self.viewport_check.setToolTip(
            'Render the 3D editor\'s background colour and floor as it shows them.\n'
            'The gradient and environment map below are then not used.')
        self.viewport_check.setChecked(Config.match_viewport)
        bg_lay.addWidget(self.viewport_check)

        self.gradient_check = QtWidgets.QCheckBox('Use Gradient Background', bg_box)
        self.gradient_check.setChecked(Config.background.enable_gradient)
        bg_lay.addWidget(self.gradient_check)

        self.envmap_check = QtWidgets.QCheckBox('Use Environment Map', bg_box)
        self.envmap_check.setChecked(Config.environment_map.enable)
        bg_lay.addWidget(self.envmap_check)

        self.gen_check = QtWidgets.QCheckBox('Generate Environment Map', bg_box)
        self.gen_check.setChecked(Config.environment_map.generate)
        bg_lay.addWidget(self.gen_check)

        load_env_btn = QtWidgets.QPushButton("Load Environment Map...", bg_box)
        load_env_btn.clicked.connect(self.on_load_envmap)
        bg_lay.addWidget(load_env_btn)

        main_sizer.addWidget(bg_box)

        # Effects group
        effects_box = QtWidgets.QGroupBox("Effects", self)
        effects_lay = QtWidgets.QVBoxLayout(effects_box)

        self.reflections_check = QtWidgets.QCheckBox('Enable Reflections', effects_box)
        self.reflections_check.setChecked(Config.enable_reflections)
        effects_lay.addWidget(self.reflections_check)

        self.shadows_check = QtWidgets.QCheckBox('Enable Shadows', effects_box)
        self.shadows_check.setChecked(Config.shadows.enable)
        effects_lay.addWidget(self.shadows_check)

        main_sizer.addWidget(effects_box)

        # Ambient Occlusion group
        ao_box = QtWidgets.QGroupBox("Ambient Occlusion", self)
        ao_lay = QtWidgets.QVBoxLayout(ao_box)

        self.ao_check = QtWidgets.QCheckBox('Enable', ao_box)
        self.ao_check.setChecked(Config.ambient_occlusion.enable)
        ao_lay.addWidget(self.ao_check)

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
        lighting_box = QtWidgets.QGroupBox("Lighting", self)
        lighting_lay = QtWidgets.QVBoxLayout(lighting_box)

        amb_row = QtWidgets.QHBoxLayout()
        amb_row.addWidget(QtWidgets.QLabel('Ambient Intensity:', lighting_box))
        self.ambient_spin = QtWidgets.QDoubleSpinBox(lighting_box)
        self.ambient_spin.setRange(0.0, 1.0)
        self.ambient_spin.setSingleStep(0.05)
        self.ambient_spin.setValue(Config.lighting.ambient_intensity)
        amb_row.addWidget(self.ambient_spin)
        lighting_lay.addLayout(amb_row)

        self.camera_light_check = QtWidgets.QCheckBox('Light at Camera', lighting_box)
        self.camera_light_check.setToolTip(
            'Add a white light at the camera, as well as the lights below. The lights below are fixed\n'
            'points in the world; one inside or under the model leaves the visible side dark.')
        self.camera_light_check.setChecked(Config.lighting.camera_light)
        lighting_lay.addWidget(self.camera_light_check)

        self.lights = LightingPanel(lighting_box)
        lighting_lay.addWidget(self.lights)

        main_sizer.addWidget(lighting_box)

    @_check_types.do
    def on_load_envmap(self) -> None:
        """Pick an environment map image and switch to using it."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load Environment Map', '',
            'Image files (*.jpg *.png *.hdr *.bmp)')

        if path:
            self._envmap_path = path
            self.gen_check.setChecked(False)
            self.envmap_check.setChecked(True)

    @_check_types.do
    def apply(self) -> None:
        """Write the control values to ``Config.ray_trace``."""
        Config.match_viewport = self.viewport_check.isChecked()
        Config.background.enable_gradient = self.gradient_check.isChecked()
        Config.environment_map.enable = self.envmap_check.isChecked()
        Config.environment_map.generate = self.gen_check.isChecked()
        Config.environment_map.path = self._envmap_path
        Config.enable_reflections = self.reflections_check.isChecked()
        Config.shadows.enable = self.shadows_check.isChecked()
        Config.ambient_occlusion.enable = self.ao_check.isChecked()
        Config.ambient_occlusion.samples = float(self.ao_samples_spin.value())
        Config.ambient_occlusion.radius = self.ao_radius_spin.value()
        Config.lighting.ambient_intensity = self.ambient_spin.value()
        Config.lighting.camera_light = self.camera_light_check.isChecked()
        Config.lighting.lights = self.lights.GetValue()
        Config.default_resolution = self.resolution.currentText()


class RenderSettingsDialog(_dialog_base.BaseDialog):
    """Stand-alone dialog around :class:`RenderSettingsPanel`."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`RenderSettingsDialog` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        super().__init__(parent, title='Render Settings', size=(-1, 600))

        self.settings = RenderSettingsPanel(self.panel)
        QtWidgets.QVBoxLayout(self.panel).addWidget(self.settings)

        # Connect OK to on_apply
        self.button_box.accepted.disconnect()
        self.button_box.accepted.connect(self.on_apply)

    @_check_types.do
    def on_apply(self) -> None:
        """Save the settings and close."""
        self.settings.apply()
        self.accept()


class LightingPanel(QtWidgets.QWidget):
    """The lights, one tab each, with buttons to add and remove them.

    Tabs are labelled ``Light 1``, ``Light 2``... in order; adding a light appends a tab and
    removing one renumbers the rest so the numbers never skip.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`LightingPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        super().__init__(parent)

        self.tabs = QtWidgets.QTabWidget(self)

        self.add_btn = QtWidgets.QPushButton('Add Light', self)
        self.remove_btn = QtWidgets.QPushButton('Remove Light', self)

        self.add_btn.clicked.connect(self.on_add)
        self.remove_btn.clicked.connect(self.on_remove)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.tabs, 1)
        lay.addLayout(btn_row)

        for light in Config.lighting.lights:
            self._append(LightItem(self.tabs, **light))

        self._renumber()

    @_check_types.do
    def on_add(self) -> None:
        """Add a white light at the origin on a new tab and show it."""
        self._append(LightItem(self.tabs, position=[0.0, 0.0, 0.0], intensity=1.0, color=[1.0, 1.0, 1.0]))
        self._renumber()
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    @_check_types.do
    def on_remove(self) -> None:
        """Remove the light on the current tab and renumber the ones after it."""
        index = self.tabs.currentIndex()
        if index < 0:
            return

        page = self.tabs.widget(index)
        self.tabs.removeTab(index)
        page.deleteLater()

        self._renumber()

    @_check_types.do
    def GetValue(self) -> list[dict[str, list[float] | float]]:
        """Return every light, in tab order.

        :returns: One ``position`` / ``intensity`` / ``color`` dict per light.
        :rtype: list[dict[str, list[float] | float]]
        """
        return [self.tabs.widget(i).GetValue() for i in range(self.tabs.count())]

    @_check_types.do
    def _append(self, light: "LightItem") -> None:
        """Add a tab for ``light``; the label is set by :meth:`_renumber`.

        :param light: The light's controls.
        :type light: :class:`LightItem`
        """
        self.tabs.addTab(light, '')

    @_check_types.do
    def _renumber(self) -> None:
        """Label the tabs ``Light 1`` to ``Light n`` in order and update the Remove button."""
        for i in range(self.tabs.count()):
            self.tabs.setTabText(i, f'Light {i + 1}')

        self.remove_btn.setEnabled(self.tabs.count() > 0)


class LightItem(QtWidgets.QWidget):
    """One light's controls: X, Y and Z position, then intensity with its colour button."""

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, position: list[float], intensity: float, color: list[float]):
        """Initialise the :class:`LightItem` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        :param position: ``[x, y, z]`` world position.
        :type position: list[float]
        :param intensity: Brightness, ``INTENSITY_MIN`` to ``INTENSITY_MAX``.
        :type intensity: float
        :param color: ``[r, g, b]``, each 0.0 to 1.0.
        :type color: list[float]
        """
        super().__init__(parent)

        x, y, z = position

        self.x_ctrl = _float_ctrl.FloatCtrl(self, 'X:', -POSITION_LIMIT, POSITION_LIMIT, POSITION_STEP)
        self.y_ctrl = _float_ctrl.FloatCtrl(self, 'Y:', -POSITION_LIMIT, POSITION_LIMIT, POSITION_STEP)
        self.z_ctrl = _float_ctrl.FloatCtrl(self, 'Z:', -POSITION_LIMIT, POSITION_LIMIT, POSITION_STEP)

        # FloatCtrl starts at the middle of its range, so set the real values after building.
        self.x_ctrl.SetValue(float(x))
        self.y_ctrl.SetValue(float(y))
        self.z_ctrl.SetValue(float(z))

        self.intensity_ctrl = _float_ctrl.FloatCtrl(
            self, 'Intensity:', INTENSITY_MIN, INTENSITY_MAX, INTENSITY_STEP)
        self.intensity_ctrl.SetValue(float(intensity))

        self._color = [float(c) for c in color]
        self.color_btn = QtWidgets.QPushButton(self)
        self.color_btn.setToolTip('Light colour')
        self.color_btn.setFixedWidth(48)
        self.color_btn.clicked.connect(self._pick_color)
        self._update_color_button()

        intensity_row = QtWidgets.QHBoxLayout()
        intensity_row.addWidget(self.intensity_ctrl, 1)
        intensity_row.addWidget(self.color_btn, 0, QtCore.Qt.AlignmentFlag.AlignBottom)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(self.x_ctrl)
        lay.addWidget(self.y_ctrl)
        lay.addWidget(self.z_ctrl)
        lay.addLayout(intensity_row)
        lay.addStretch(1)

    @_check_types.do
    def _update_color_button(self) -> None:
        """Paint the colour button with the light's colour."""
        r, g, b = (int(round(c * 255)) for c in self._color)
        self.color_btn.setStyleSheet(f'background-color: rgb({r},{g},{b});')

    @_check_types.do
    def _pick_color(self) -> None:
        """Ask for a new colour for the light."""
        r, g, b = (int(round(c * 255)) for c in self._color)

        chosen = QtWidgets.QColorDialog.getColor(QtGui.QColor(r, g, b), self, 'Light colour')

        if chosen.isValid():
            self._color = [chosen.red() / 255.0, chosen.green() / 255.0, chosen.blue() / 255.0]
            self._update_color_button()

    @_check_types.do
    def GetValue(self) -> dict[str, list[float] | float]:
        """Return the light as it is stored in ``Config.ray_trace.lighting.lights``.

        :returns: ``position``, ``intensity`` and ``color``.
        :rtype: dict[str, list[float] | float]
        """
        return dict(
            position=[self.x_ctrl.GetValue(), self.y_ctrl.GetValue(), self.z_ctrl.GetValue()],
            intensity=self.intensity_ctrl.GetValue(),
            color=list(self._color)
        )
