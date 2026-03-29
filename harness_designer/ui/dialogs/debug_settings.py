from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import checkbox_ctrl as _checkbox_ctrl
from ..widgets import float_ctrl as _float_ctrl
from ... import color as _color

from ... import config as _config

if TYPE_CHECKING:
    from ... import ui as _ui


Config = _config.Config


class DebugSettingsDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame"):

        self.mainframe = parent
        _dialog_base.BaseDialog.__init__(self, parent, 'Settings', label='Debug Settings', size=(-1, 675))

        panel = self.panel
        vsizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(vsizer)

        rendering3d = Config.debug.rendering3d

        visual_sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Visual Settings")
        visual_sb = visual_sz.GetStaticBox()

        self.faces = _checkbox_ctrl.CheckboxCtrl(visual_sb, 'Render Faces:')
        self.faces.SetValue(rendering3d.draw_faces)

        visual_sz.Add(self.faces, 0, wx.ALL, 5)

        edges_sz = wx.StaticBoxSizer(wx.VERTICAL, visual_sb, "Edges")
        edges_sb = edges_sz.GetStaticBox()

        self.edges = _checkbox_ctrl.CheckboxCtrl(edges_sb, 'Render Edges:')
        self.edges.SetValue(rendering3d.draw_edges)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.edges, 1, wx.TOP | wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)

        r, g, b = rendering3d.edge_color_dark
        edge_dark_color = _color.Color(r, g, b, 1.0)
        self.edge_color_dark = wx.ColourPickerCtrl(edges_sb, wx.ID_ANY, colour=edge_dark_color)
        st = wx.StaticText(edges_sb, wx.ID_ANY, label='Color Dark:')
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(st, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.edge_color_dark, 1, wx.LEFT, 5)

        hsizer.Add(sizer, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)

        r, g, b = rendering3d.edge_color_light
        edge_light_color = _color.Color(r, g, b, 1.0)
        self.edge_color_light = wx.ColourPickerCtrl(edges_sb, wx.ID_ANY, colour=edge_light_color)
        st = wx.StaticText(edges_sb, wx.ID_ANY, label='Color Light:')
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(st, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.edge_color_light, 1, wx.LEFT, 5)

        hsizer.Add(sizer, 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        edges_sz.Add(hsizer, 1, wx.EXPAND)

        self.edge_threshold = _float_ctrl.FloatCtrl(
            edges_sb, 'Color Threshold:', min_val=0.10, max_val=0.90, inc=0.01, slider=True)
        self.edge_threshold.SetValue(rendering3d.edge_luminance_threshold)

        edges_sz.Add(self.edge_threshold, 0, wx.EXPAND | wx.ALL, 5)

        visual_sz.Add(edges_sz, 0, wx.ALL | wx.EXPAND, 5)

        bounding_box_sz = wx.StaticBoxSizer(wx.VERTICAL, visual_sb, "Bounding Boxes")
        bound_box_sb = bounding_box_sz.GetStaticBox()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.aabb = _checkbox_ctrl.CheckboxCtrl(bound_box_sb, 'Axis Aligned Bounding Box (AABB):')
        self.aabb.SetValue(rendering3d.draw_aabb)

        hsizer.Add(self.aabb, 1, wx.ALL, 5)

        self.obb = _checkbox_ctrl.CheckboxCtrl(bound_box_sb, 'Oriented Bounding Box (OBB):')
        self.obb.SetValue(rendering3d.draw_obb)

        hsizer.Add(self.obb, 1, wx.ALL, 5)

        bounding_box_sz.Add(hsizer, 1, wx.EXPAND)

        visual_sz.Add(bounding_box_sz, 0, wx.ALL | wx.EXPAND, 5)

        normals_sz = wx.StaticBoxSizer(wx.VERTICAL, visual_sb, "Normals")
        normals_sb = normals_sz.GetStaticBox()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.normals = _checkbox_ctrl.CheckboxCtrl(normals_sb, 'Render Normals:')
        self.normals.SetValue(rendering3d.draw_normals)

        hsizer.Add(self.normals, 1, wx.ALL, 5)

        r, g, b = rendering3d.normals_color
        normals_color = _color.Color(r, g, b, 1.0)
        self.normals_color = wx.ColourPickerCtrl(normals_sb, wx.ID_ANY, colour=normals_color)
        st = wx.StaticText(normals_sb, wx.ID_ANY, label='Color:')
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(st, 1, wx.RIGHT, 5)
        sizer.Add(self.normals_color, 1, wx.LEFT, 5)

        hsizer.Add(sizer, 1, wx.ALL, 5)

        normals_sz.Add(hsizer, 1, wx.EXPAND)

        visual_sz.Add(normals_sz, 0, wx.ALL | wx.EXPAND, 5)

        vertices_sz = wx.StaticBoxSizer(wx.VERTICAL, visual_sb, "Vertices")
        vertices_sb = vertices_sz.GetStaticBox()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.vertices = _checkbox_ctrl.CheckboxCtrl(vertices_sb, 'Render Vertices:')
        self.vertices.SetValue(rendering3d.draw_vertices)

        hsizer.Add(self.vertices, 1, wx.ALL, 5)

        r, g, b = rendering3d.vertices_color
        vertices_color = _color.Color(r, g, b, 1.0)
        self.vertices_color = wx.ColourPickerCtrl(vertices_sb, wx.ID_ANY, colour=vertices_color)
        st = wx.StaticText(vertices_sb, wx.ID_ANY, label='Color:')
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(st, 1, wx.RIGHT, 5)
        sizer.Add(self.vertices_color, 1, wx.LEFT, 5)

        hsizer.Add(sizer, 1, wx.ALL, 5)

        vertices_sz.Add(hsizer, 1, wx.EXPAND)

        visual_sz.Add(vertices_sz, 0, wx.ALL | wx.EXPAND, 5)

        vsizer.Add(visual_sz, 0, wx.EXPAND | wx.ALL, 10)

        functions = Config.debug.functions

        functions_sz = wx.StaticBoxSizer(wx.VERTICAL, panel, "Function Settings")
        functions_sb = functions_sz.GetStaticBox()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        if not functions.log_args and not functions.log_duration:
            st = wx.StaticText(functions_sb, wx.ID_ANY, label='Application restart will be needed if these are changed.')
            st.SetForegroundColour(wx.RED)
            functions_sz.Add(st, 0, wx.ALL, 5)

        self.log_args = _checkbox_ctrl.CheckboxCtrl(functions_sb, 'Log Function Parameters:')
        self.log_args.SetValue(functions.log_args)

        hsizer.Add(self.log_args, 1, wx.ALL, 5)

        self.log_duration = _checkbox_ctrl.CheckboxCtrl(functions_sb, 'Log Function Duration:')
        self.log_duration.SetValue(functions.log_duration)

        hsizer.Add(self.log_duration, 1, wx.ALL, 5)

        functions_sz.Add(hsizer, 0, wx.EXPAND)
        vsizer.Add(functions_sz, 0, wx.EXPAND | wx.ALL, 10)

    def SetValues(self):

        def _get_color(color):
            r = color.GetRed()
            g = color.GetGreen()
            b = color.GetBlue()

            color = _color.Color(r, g, b, 255)
            return color.rgba_scalar[:-1]

        Config.debug.rendering3d.draw_faces = self.faces.GetValue()
        Config.debug.rendering3d.draw_edges = self.edges.GetValue()
        Config.debug.rendering3d.edge_color_dark = _get_color(self.edge_color_dark.GetColour())
        Config.debug.rendering3d.edge_color_light = _get_color(self.edge_color_light.GetColour())
        Config.debug.rendering3d.edge_luminance_threshold = self.edge_threshold.GetValue()
        Config.debug.rendering3d.draw_aabb = self.aabb.GetValue()
        Config.debug.rendering3d.draw_obb = self.obb.GetValue()
        Config.debug.rendering3d.draw_normals = self.normals.GetValue()
        Config.debug.rendering3d.normals_color = _get_color(self.normals_color.GetColour())
        Config.debug.rendering3d.draw_vertices = self.vertices.GetValue()
        Config.debug.rendering3d.vertices_color = _get_color(self.vertices_color.GetColour())

        Config.debug.functions.log_args = self.log_args.GetValue()
        Config.debug.functions.log_duration = self.log_duration.GetValue()