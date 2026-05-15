# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtWidgets
from PySide6 import QtGui

from . import dialog_base as _dialog_base
from ..widgets import checkbox_ctrl as _checkbox_ctrl
from ..widgets import float_ctrl as _float_ctrl
from ... import color as _color
from ... import config as _config

# PySide6 colour picker — uses QColorDialog indirectly via a thin wrapper.
# We provide a small ColourPickerCtrl shim below that matches the wx API
# used in this file (GetColour / SetColour).
from PySide6.QtWidgets import QPushButton, QColorDialog


if TYPE_CHECKING:
    from ... import ui as _ui


Config = _config.Config


class _ColourPickerCtrl(QPushButton):
    """Minimal wx.ColourPickerCtrl replacement."""

    def __init__(self, parent, colour: "_color.Color"):
        super().__init__(parent)
        self._color = colour
        self._apply_color(colour)
        self.clicked.connect(self._pick)

    def _apply_color(self, c):
        self._color = c
        try:
            qc = c.to_qcolor()
        except AttributeError:
            qc = QtGui.QColor(c.GetRed(), c.GetGreen(), c.GetBlue())

        self.setStyleSheet(
            f'background-color: {qc.name()}; min-width: 40px; min-height: 20px;')

    def _pick(self):
        c = self._color

        try:
            qc = c.to_qcolor()
        except AttributeError:
            qc = QtGui.QColor(c.GetRed(), c.GetGreen(), c.GetBlue())

        chosen = QColorDialog.getColor(qc, self, "Choose colour")
        if chosen.isValid():
            new_c = _color.Color(
                chosen.red(), chosen.green(), chosen.blue(), 255)

            self._apply_color(new_c)

    def GetColour(self):
        return self._color


class DebugSettingsDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame"):
        self.mainframe = parent
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Debug Settings', size=(-1, 675))

        panel = self.panel
        vsizer = QtWidgets.QVBoxLayout(panel)

        rendering3d = Config.debug.rendering3d

        # Visual Settings group
        visual_box = QtWidgets.QGroupBox("Visual Settings", panel)
        visual_lay = QtWidgets.QVBoxLayout(visual_box)

        self.faces = _checkbox_ctrl.CheckboxCtrl(
            visual_box, 'Render Faces:')

        self.faces.SetValue(rendering3d.draw_faces)
        visual_lay.addWidget(self.faces)

        # Edges sub-group
        edges_box = QtWidgets.QGroupBox("Edges", visual_box)
        edges_lay = QtWidgets.QVBoxLayout(edges_box)

        self.edges = _checkbox_ctrl.CheckboxCtrl(
            edges_box, 'Render Edges:')

        self.edges.SetValue(rendering3d.draw_edges)

        r, g, b = rendering3d.edge_color_dark
        edge_dark_color = _color.Color(r, g, b, 255)
        self.edge_color_dark = _ColourPickerCtrl(edges_box, edge_dark_color)

        r, g, b = rendering3d.edge_color_light
        edge_light_color = _color.Color(r, g, b, 255)
        self.edge_color_light = _ColourPickerCtrl(edges_box, edge_light_color)

        edges_row = QtWidgets.QHBoxLayout()
        edges_row.addWidget(self.edges, 1)
        dark_row = QtWidgets.QHBoxLayout()
        dark_row.addWidget(QtWidgets.QLabel('Color Dark:', edges_box))
        dark_row.addWidget(self.edge_color_dark)
        light_row = QtWidgets.QHBoxLayout()
        light_row.addWidget(QtWidgets.QLabel('Color Light:', edges_box))
        light_row.addWidget(self.edge_color_light)
        edges_row.addLayout(dark_row)
        edges_row.addLayout(light_row)
        edges_lay.addLayout(edges_row)

        self.edge_threshold = _float_ctrl.FloatCtrl(
            edges_box, 'Color Threshold:', min_val=0.10,
            max_val=0.90, inc=0.01, slider=True)

        self.edge_threshold.SetValue(rendering3d.edge_luminance_threshold)
        edges_lay.addWidget(self.edge_threshold)

        visual_lay.addWidget(edges_box)

        # Bounding Boxes sub-group
        bb_box = QtWidgets.QGroupBox("Bounding Boxes", visual_box)
        bb_lay = QtWidgets.QHBoxLayout(bb_box)

        self.aabb = _checkbox_ctrl.CheckboxCtrl(
            bb_box, 'Axis Aligned Bounding Box (AABB):')

        self.aabb.SetValue(rendering3d.draw_aabb)
        bb_lay.addWidget(self.aabb, 1)

        self.obb = _checkbox_ctrl.CheckboxCtrl(
            bb_box, 'Oriented Bounding Box (OBB):')

        self.obb.SetValue(rendering3d.draw_obb)
        bb_lay.addWidget(self.obb, 1)

        visual_lay.addWidget(bb_box)

        # Normals sub-group
        normals_box = QtWidgets.QGroupBox("Normals", visual_box)
        normals_lay = QtWidgets.QVBoxLayout(normals_box)

        self.normals = _checkbox_ctrl.CheckboxCtrl(
            normals_box, 'Render Normals:')

        self.normals.SetValue(rendering3d.draw_normals)

        r, g, b = rendering3d.normals_color
        normals_color = _color.Color(r, g, b, 255)
        self.normals_color = _ColourPickerCtrl(normals_box, normals_color)

        normals_row = QtWidgets.QHBoxLayout()
        normals_row.addWidget(self.normals, 1)
        nc_row = QtWidgets.QHBoxLayout()
        nc_row.addWidget(QtWidgets.QLabel('Color:', normals_box))
        nc_row.addWidget(self.normals_color)
        normals_row.addLayout(nc_row)
        normals_lay.addLayout(normals_row)

        visual_lay.addWidget(normals_box)

        # Vertices sub-group
        vertices_box = QtWidgets.QGroupBox("Vertices", visual_box)
        vertices_lay = QtWidgets.QVBoxLayout(vertices_box)

        self.vertices = _checkbox_ctrl.CheckboxCtrl(vertices_box, 'Render Vertices:')
        self.vertices.SetValue(rendering3d.draw_vertices)

        r, g, b = rendering3d.vertices_color
        vertices_color = _color.Color(r, g, b, 255)
        self.vertices_color = _ColourPickerCtrl(vertices_box, vertices_color)

        vertices_row = QtWidgets.QHBoxLayout()
        vertices_row.addWidget(self.vertices, 1)
        vc_row = QtWidgets.QHBoxLayout()
        vc_row.addWidget(QtWidgets.QLabel('Color:', vertices_box))
        vc_row.addWidget(self.vertices_color)
        vertices_row.addLayout(vc_row)
        vertices_lay.addLayout(vertices_row)

        visual_lay.addWidget(vertices_box)

        vsizer.addWidget(visual_box)

        # Function Settings group
        functions = Config.debug.functions
        functions_box = QtWidgets.QGroupBox("Function Settings", panel)
        functions_lay = QtWidgets.QVBoxLayout(functions_box)

        if not functions.log_args and not functions.log_duration:
            restart_lbl = QtWidgets.QLabel(
                'Application restart will be needed if these are changed.',
                functions_box)

            restart_lbl.setStyleSheet('color: red;')
            functions_lay.addWidget(restart_lbl)

        self.log_args = _checkbox_ctrl.CheckboxCtrl(
            functions_box, 'Log Function Parameters:')

        self.log_args.SetValue(functions.log_args)

        self.log_duration = _checkbox_ctrl.CheckboxCtrl(
            functions_box, 'Log Function Duration:')

        self.log_duration.SetValue(functions.log_duration)

        fn_row = QtWidgets.QHBoxLayout()
        fn_row.addWidget(self.log_args, 1)
        fn_row.addWidget(self.log_duration, 1)
        functions_lay.addLayout(fn_row)

        vsizer.addWidget(functions_box)

    def SetValues(self):
        def _get_color(picker):
            c = picker.GetColour()
            color = _color.Color(c.GetRed(), c.GetGreen(), c.GetBlue(), 255)
            return color.rgba_scalar[:-1]

        Config.debug.rendering3d.draw_faces = self.faces.GetValue()
        Config.debug.rendering3d.draw_edges = self.edges.GetValue()
        Config.debug.rendering3d.edge_color_dark = (
            _get_color(self.edge_color_dark))

        Config.debug.rendering3d.edge_color_light = (
            _get_color(self.edge_color_light))

        Config.debug.rendering3d.edge_luminance_threshold = (
            self.edge_threshold.GetValue())

        Config.debug.rendering3d.draw_aabb = self.aabb.GetValue()
        Config.debug.rendering3d.draw_obb = self.obb.GetValue()
        Config.debug.rendering3d.draw_normals = self.normals.GetValue()
        Config.debug.rendering3d.normals_color = _get_color(self.normals_color)
        Config.debug.rendering3d.draw_vertices = self.vertices.GetValue()
        Config.debug.rendering3d.vertices_color = (
            _get_color(self.vertices_color))

        Config.debug.functions.log_args = self.log_args.GetValue()
        Config.debug.functions.log_duration = self.log_duration.GetValue()
