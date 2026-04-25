import wx
from wx.lib import scrolledpanel

from . import dialog_base as _dialog_base
from ... import config as _config

Config = _config.Config.ray_trace


class RenderSettingsDialog(_dialog_base.BaseDialog):
    """Dialog for configuring render settings"""

    def __init__(self, parent):
        super().__init__(parent, title='Render Settings', label='Render Settings', size=(-1, 600))

        panel = self.panel
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        choices = [res['label'] for res in Config.resolutions]
        resolution_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(panel, wx.ID_ANY, label='Resolution:')
        resolution_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.resolution = wx.Choice(panel, wx.ID_ANY, choices=choices)
        self.resolution.SetStringSelection(Config.default_resolution)
        resolution_sizer.Add(self.gradient_check, 0, wx.EXPAND)
        main_sizer.Add(resolution_sizer, 0, wx.EXPAND | wx.ALL, 5)

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

        gen_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(bg_box, wx.ID_ANY, label='Generate Environment Map:')
        gen_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.gen_check = wx.CheckBox(bg_box, label='')
        gen_sizer.Add(self.gen_check, 0, wx.EXPAND)
        bg_sizer.Add(gen_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.envmap_check.SetValue(self.settings.enable_environment_map)
        self.envmap_check.Enable(scene.environment_map is not None)

        load_env_btn = wx.Button(bg_box, label="Load Environment Map...")
        load_env_btn.Bind(wx.EVT_BUTTON, self.on_load_envmap)
        bg_sizer.Add(load_env_btn, 0, wx.ALL, 5)

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
        st = wx.StaticText(ao_box, wx.ID_ANY, label='Enable')
        ao_enable_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ao_check = wx.CheckBox(ao_box, label='')
        self.ao_check.SetValue(self.settings.enable_ambient_occlusion)
        ao_enable_sizer.Add(self.ao_check, 0, wx.EXPAND)
        ao_sizer.Add(ao_enable_sizer, 0, wx.EXPAND | wx.ALL, 5)

        ao_samples_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(ao_box, label="Samples:")
        ao_samples_sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.ao_samples_spin = wx.SpinCtrl(
            ao_box, value=str(int(self.settings.ao_samples)),
            min=4, max=64, initial=int(self.settings.ao_samples))
        ao_samples_sizer.Add(self.ao_samples_spin, 0, wx.EXPAND)
        ao_sizer.Add(ao_samples_sizer, 0, wx.EXPAND | wx.ALL, 5)

        # AO radius
        ao_radius_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(ao_box, label="Radius:")
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

        lights_sizer = wx.BoxSizer(wx.HORIZONTAL)
        st = wx.StaticText(lighting_box, label="Lights")
        lights_sizer.AddSpacer(1)
        lights_sizer.Add(st, 0, wx.ALL, 5)
        lights_sizer.AddSpacer(1)

        lighting_sizer.Add(lights_sizer, 0, wx.EXPAND)

        lights_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lights = LightingPanel(lighting_box)
        lights_sizer.Add(self.lights, 0, wx.ALL, 5)
        lighting_sizer.Add(lights_sizer, 0, wx.EXPAND)

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
                path = fileDialog.GetPath()
                Config.environment_map.path = path
                self.gen_check.SetValue(False)
                self.envmap_check.SetValue(True)

    def on_apply(self, event):
        # Update settings
        Config.background.enable_gradient = self.gradient_check.GetValue()

        Config.environment_map.enable = self.envmap_check.GetValue()
        Config.enable_reflections = self.reflections_check.GetValue()
        Config.shadows.enable = self.shadows_check.GetValue()
        Config.ambient_occlusion.enable = self.ao_check.GetValue()
        Config.ambient_occlusion.samples = float(self.ao_samples_spin.GetValue())
        Config.ambient_occlusion.radius = self.ao_radius_spin.GetValue()
        Config.lighting.intensity = self.ambient_spin.GetValue()
        Config.environment_map.generate = self.gen_check.GetValue()
        Config.default_resolution = self.resolution.GetStringSelection()
        Config.lighting.lights = self.lights.GetValue()

        self.EndModal(wx.ID_OK)


class LightingPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.lights_panel = LightsPanel(self, Config.lighting.lights)

        self.add_btn = wx.Button(self, wx.ID_ANY, label='Add Light')
        self.remove_btn = wx.Button(self, wx.ID_ANY, label='Remove Light')

        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.lights_panel, 1, wx.ALL, 10)
        vsizer.Add(hsizer, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.AddStretchSpacer(1)
        hsizer.Add(self.add_btn, 0, wx.ALL, 10)
        hsizer.Add(self.remove_btn, 0, wx.ALL, 10)
        vsizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizer(vsizer)

    def GetValue(self):
        return self.lights_panel.GetValue()


class LightsPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, lights):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.lights = lights
        self.items = []
        self.selected = None

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        for light in lights:
            light = LightItem(self, **light)
            self.items.append(light)

            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            hsizer.Add(light, 0)
            self.main_sizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizer(self.main_sizer)
        self.SetupScrolling()

    def GetValue(self):
        res = [light.GetValue() for light in self.items]
        return res

    def add_light(self):
        position = [0.0, 0.0, 0.0]
        color = 0.0, 0.0, 0.0
        intensity = 1.0

        light = LightItem(self, position, intensity, color)
        self.items.append(light)
        self.lights.append(light.GetValue())

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(light, 0)
        self.main_sizer.Add(hsizer, 0, wx.EXPAND)

        self.Layout()
        self.Refresh(False)

    def remove_item(self):
        if self.selected is None:
            return

        index = self.items.index(self.selected)
        self.lights.pop(index)
        self.items.pop(index)

        self.selected.Show(False)
        self.selected.Destroy()

        self.selected = None
        self.Layout()
        self.Refresh(False)

    def set_selected(self, light):
        if self.selected is not None:
            self.selected.unselect()

        self.selected = light



def get_item_sizer(st, ctrl):

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(st, 0, wx.ALL | wx.ALIGN_CENTER, 5)
    sizer.Add(ctrl, 1, wx.ALL, 5)

    return sizer


class LightItem(wx.Panel):

    def __init__(self, parent, position, intensity, color):
        self._parent = parent
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.unselected_color = self.GetBackgroundColour()
        self.selected_color = wx.SystemColour.GetColour(wx.SYS_COLOUR_HIGHLIGHT)  # NOQA

        x, y, z = position

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        st = wx.StaticText(self, wx.ID_ANY, label='X:')
        self.x_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=x, initial=str(x), min=-99999.0, max=99999.0, inc=0.5)

        x_sizer = get_item_sizer(st, self.x_ctrl)
        hsizer.Add(x_sizer, 1)

        st = wx.StaticText(self, wx.ID_ANY, label='Y:')
        self.y_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=y, initial=str(y), min=-99999.0, max=99999.0, inc=0.5)
        y_sizer = get_item_sizer(st, self.y_ctrl)
        hsizer.Add(y_sizer, 1)


        st = wx.StaticText(self, wx.ID_ANY, label='Z:')
        self.z_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=z, initial=str(z), min=-99999.0, max=99999.0, inc=0.5)
        z_sizer = get_item_sizer(st, self.z_ctrl)
        hsizer.Add(z_sizer, 1)


        st = wx.StaticText(self, wx.ID_ANY, label='Intensity:')
        self.intensity_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value=intensity, initial=str(intensity), min=0.001, max=1.0, inc=0.001)
        intensity_sizer = get_item_sizer(st, self.intensity_ctrl)
        hsizer.Add(intensity_sizer, 1)

        self.color_ctrl = wx.ColourPickerCtrl(self, wx.ID_ANY, colour=color)
        hsizer.Add(self.color_ctrl, 0, wx.ALL, 5)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizer(vsizer)

        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)

    def GetValue(self):
        x = self.x_ctrl.GetValue()
        y = self.y_ctrl.GetValue()
        z = self.z_ctrl.GetValue()
        position = [x, y, z]

        intensity = self.intensity_ctrl.GetValue()

        color = self.color_ctrl.GetColour()

        r = color.GetRed() / 255.0
        g = color.GetFreen() / 255.0
        b = color.GetBlue() / 255.0
        color = [r, g, b]

        return dict(
            position=position,
            intensity=intensity,
            color=color
        )


    def unselect(self):
        self.SetBackgroundColour(self.unselected_color)

    def on_left_up(self, evt):
        self._parent.set_selected(self)
        self.SetBackgroundColour(self.selected_color)

        evt.Skip()
