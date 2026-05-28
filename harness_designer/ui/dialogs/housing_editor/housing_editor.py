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
    """Represent a housing editor dialog in :mod:`harness_designer.ui.dialogs.housing_editor.housing_editor`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_ui.MainFrame"):
        """Initialise the :class:`HousingEditorDialog` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: UNKNOWN
        """
        self.db_obj = None

        _dialog_base.BaseDialog.__init__(self, parent, 'Edit Housing', size=(1200, 900))

        w = _config.Config.editor3d.virtual_canvas.width
        h = _config.Config.editor3d.virtual_canvas.height

        self.canvas = _canvas3d.Canvas3D(
            self.panel, Config.editor3d, size=(w, h))

        self.controls = QTabWidget(self.panel)
        self.controls.setMaximumHeight(250)
        self.housing: _housing_obj.Housing = None
        self.housing_panel: _housing_panel.HousingPanel = None
        self.cavity_panel: _cavity_panel.CavityPanel = None
        self.accessory_panel: _accessory_panel.AccessoryPanel = None

        v_layout = QVBoxLayout(self.panel)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.canvas, 1)
        v_layout.addLayout(h_layout, 1)
        v_layout.addSpacing(5)
        v_layout.addWidget(self.controls)

    def SetValue(self, db_obj):
        self.db_obj = db_obj

        self.housing = _housing_obj.Housing(self, db_obj)
        self.housing_panel = _housing_panel.HousingPanel(self, self.controls, self.housing.obj3d)
        self.cavity_panel = _cavity_panel.CavityPanel(self, self.controls, self.housing.obj3d)
        self.accessory_panel = _accessory_panel.AccessoryPanel(self, self.controls, self.housing.obj3d)

        self.controls.addTab(self.housing_panel, 'Housing')
        self.controls.addTab(self.accessory_panel, 'Accessories')
        self.controls.addTab(self.cavity_panel, 'Cavities')

        self.update()

    def closeEvent(self, event):
        """Clean up the dialog's GL canvas before the window is destroyed."""
        self.canvas.cleanup()
        super().closeEvent(event)

    @property
    def editor2d(self):
        """Return the editor 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return None

    @property
    def editor3d(self):
        """Return the editor 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.canvas.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.canvas.remove_object(obj)

    def _set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._selected_obj = obj
        self.canvas.set_selected(obj)

    def set_selected(self, obj):  # NOQA
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        if obj is not None:
            obj.set_selected(True)

    def get_selected(self):
        """Return the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._selected_obj

    @property
    def config(self):
        """Return the config.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return Config.editor3d

    def Refresh(self, *_, **__):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        :param __: Value for ``__``.
        :type __: UNKNOWN
        """
        self.canvas.update()

    @property
    def context(self):
        """Return the context.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.canvas.context
