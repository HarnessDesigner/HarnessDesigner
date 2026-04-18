import wx
from . import dialog_base as _dialog_base


class RenderSettingsDialog(_dialog_base.BaseDialog):
    """Dialog for configuring render settings"""

    def __init__(self, parent, scene):
        super().__init__(parent, title='Render Settings', label='Render Settings', size=(-1, 600))

        self.scene = scene
        self.settings = scene.render_settings

        panel = self.panel
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # background -----------------------------------------------------------
        bg_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, "Background")
        bg_box = bg_sizer.GetStaticBox()

        gradient_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(bg_box, wx.ID_ANY, label='Use Gradient Background:')
        gradient_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.gradient_check = wx.CheckBox(bg_box, label='')
        gradient_sizer.Add(self.gradient_check, 0, wx.EXPAND)
        bg_sizer.Add(gradient_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.gradient_check.SetValue(self.settings.enable_gradient)

        envmap_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(bg_box, wx.ID_ANY, label='Use Environment Map:')
        envmap_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.envmap_check = wx.CheckBox(bg_box, label='')
        envmap_sizer.Add(self.envmap_check, 0, wx.EXPAND)
        bg_sizer.Add(envmap_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.envmap_check.SetValue(self.settings.enable_environment_map)
        self.envmap_check.Enable(scene.environment_map is not None)

        load_env_btn = wx.Button(bg_box, label="Load Environment Map...")
        load_env_btn.Bind(wx.EVT_BUTTON, self.on_load_envmap)
        bg_sizer.Add(load_env_btn, 0, wx.ALL, 5)

        create_env_btn = wx.Button(bg_box, label="Create Simple Sky")
        create_env_btn.Bind(wx.EVT_BUTTON, self.on_create_sky)
        bg_sizer.Add(create_env_btn, 0, wx.ALL, 5)

        main_sizer.Add(bg_box, 0, wx.EXPAND | wx.ALL, 10)

        # effects --------------------------------------------------------------
        effects_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, "Effects")
        effects_box = effects_sizer.GetStaticBox()

        reflections_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(bg_box, wx.ID_ANY, label='Enable Reflections:')
        reflections_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.reflections_check = wx.CheckBox(effects_box, label="")
        reflections_sizer.Add(self.reflections_check, 0, wx.EXPAND)
        effects_sizer.Add(reflections_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.reflections_check.SetValue(self.settings.enable_reflections)

        shadows_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(bg_box, wx.ID_ANY, label='Enable Shadows:')
        shadows_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.shadows_check = wx.CheckBox(effects_box, label="")
        shadows_sizer.Add(self.shadows_check, 0, wx.EXPAND)
        effects_sizer.Add(shadows_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.shadows_check.SetValue(self.settings.enable_shadows)

        main_sizer.Add(effects_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # ambient occlusion ----------------------------------------------------
        ao_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, "Ambient Occlusion")
        ao_box = ao_sizer.GetStaticBox()

        ao_enable_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(ao_box, wx.ID_ANY, label='Enable Ambient Occlusion')
        ao_enable_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ao_check = wx.CheckBox(ao_box, label='')
        self.ao_check.SetValue(self.settings.enable_ambient_occlusion)
        ao_enable_sizer.Add(self.ao_check, 0, wx.EXPAND)
        ao_sizer.Add(ao_enable_sizer, 0, wx.EXPAND | wx.ALL, 5)

        ao_samples_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(ao_box, label="AO Samples:")
        ao_samples_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ao_samples_spin = wx.SpinCtrl(
            ao_box, value=str(int(self.settings.ao_samples)),
            min=4, max=64, initial=int(self.settings.ao_samples))
        ao_samples_sizer.Add(self.ao_samples_spin, 0, wx.EXPAND)
        ao_sizer.Add(ao_samples_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # AO radius
        ao_radius_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(ao_box, label="AO Radius:")
        ao_radius_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ao_radius_spin = wx.SpinCtrlDouble(
            ao_box, value=str(self.settings.ao_radius),
            min=0.1, max=5.0, initial=self.settings.ao_radius, inc=0.1)
        ao_radius_sizer.Add(self.ao_radius_spin, 0, wx.EXPAND)
        ao_sizer.Add(ao_radius_sizer, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(ao_sizer, 0, wx.EXPAND | wx.ALL, 10)

        # lighting settings ----------------------------------------------------
        lighting_sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, "Lighting")
        lighting_box = lighting_sizer.GetStaticBox()

        ambient_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(lighting_box, label="Ambient Intensity:")
        ambient_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ambient_spin = wx.SpinCtrlDouble(
            lighting_box, value=str(scene.ambient_intensity),
            min=0.0, max=1.0, initial=scene.ambient_intensity, inc=0.05)
        ambient_sizer.Add(self.ambient_spin, 0, wx.EXPAND)
        lighting_sizer.Add(ambient_sizer, 0, wx.EXPAND | wx.ALL, 5)

        main_sizer.Add(lighting_sizer, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(main_sizer)

    def on_load_envmap(self, event):
        with wx.FileDialog(
            self,
            "Load Environment Map",
            wildcard="Image files (*.jpg;*.png;*.hdr;*.bmp)|*.jpg;*.png;*.hdr;*.bmp",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_OK:
                pathname = fileDialog.GetPath()
                self.scene.load_environment_map(pathname)
                self.envmap_check.Enable(True)
                self.envmap_check.SetValue(True)

    def on_create_sky(self, event):
        self.scene.create_simple_environment()
        self.envmap_check.Enable(True)
        self.envmap_check.SetValue(True)
        wx.MessageBox("Simple sky environment created!", "Success", wx.OK | wx.ICON_INFORMATION)

    def on_apply(self, event):
        # Update settings
        self.settings.enable_gradient = self.gradient_check.GetValue()
        self.settings.enable_environment_map = self.envmap_check.GetValue()
        self.settings.enable_reflections = self.reflections_check.GetValue()
        self.settings.enable_shadows = self.shadows_check.GetValue()
        self.settings.enable_ambient_occlusion = self.ao_check.GetValue()
        self.settings.ao_samples = float(self.ao_samples_spin.GetValue())
        self.settings.ao_radius = self.ao_radius_spin.GetValue()

        self.scene.ambient_intensity = self.ambient_spin.GetValue()

        self.EndModal(wx.ID_OK)
