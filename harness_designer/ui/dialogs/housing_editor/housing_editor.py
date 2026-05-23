# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QVBoxLayout, QTabWidget, QHBoxLayout

from .. import dialog_base as _dialog_base
from .... import config as _config
from ....gl import canvas3d as _canvas3d
from . import config as _config
from . import housing_obj as _housing_obj
from . import housing_panel as _housing_panel
from . import cavity_panel as _cavity_panel
from . import accessory_panel as _accessory_panel

if TYPE_CHECKING:
    from .... import ui as _ui


Config = _config.Config


class HousingEditorDialog(_dialog_base.BaseDialog):

    def __init__(self, parent: "_ui.MainFrame", db_obj):
        self.db_obj = db_obj

        _dialog_base.BaseDialog.__init__(self, parent, 'Edit Housing', size=(1200, 900))

        w = _config.Config.editor3d.virtual_canvas.width
        h = _config.Config.editor3d.virtual_canvas.height

        self.canvas = _canvas3d.Canvas3D(
            self.panel, Config.editor3d, size=(w, h))

        self.controls = QTabWidget(self.panel)
        self.controls.setMaximumHeight(250)
        self.housing = _housing_obj.Housing(self, db_obj)
        self.housing_panel = _housing_panel.HousingPanel(self, self.controls, self.housing.obj3d)
        self.cavity_panel = _cavity_panel.CavityPanel(self, self.controls, self.housing.obj3d)
        self.accessory_panel = _accessory_panel.AccessoryPanel(self, self.controls, self.housing.obj3d)

        self.controls.addTab(self.housing_panel, 'Housing')
        self.controls.addTab(self.accessory_panel, 'Accessories')
        self.controls.addTab(self.cavity_panel, 'Cavities')

        v_layout = QVBoxLayout(self.panel)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.canvas, 1)
        v_layout.addLayout(h_layout, 1)
        v_layout.addSpacing(5)
        v_layout.addWidget(self.controls)

    def closeEvent(self, event):
        """Clean up the dialog's GL canvas before the window is destroyed."""
        self.canvas.cleanup()
        super().closeEvent(event)

    @property
    def editor2d(self):
        return None

    @property
    def editor3d(self):
        return self

    def add_object(self, obj):
        self.canvas.add_object(obj)

    def remove_object(self, obj):
        self.canvas.remove_object(obj)

    def _set_selected(self, obj):
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    def set_selected(self, obj):  # NOQA
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self):
        return self._selected_obj

    @property
    def config(self):
        return Config.editor3d

    def Refresh(self, *_, **__):
        self.canvas.update()

    @property
    def context(self):
        return self.canvas.context
