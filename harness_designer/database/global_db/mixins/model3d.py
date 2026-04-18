from typing import TYPE_CHECKING

import wx

from .... import utils as _utils
from ....ui.editor_obj import prop_grid as _prop_grid
from ....gl import model_preview as _model_preview

from .base import BaseMixin

if TYPE_CHECKING:
    from .. import model3d as _model3d


class Model3DMixin(BaseMixin):

    @property
    def model3d(self) -> "_model3d.Model3D":
        model3d_id = self.model3d_id
        if model3d_id is None:
            return None

        return self._table.db.models3d_table[model3d_id]

    @property
    def model3d_id(self) -> int:
        return self._table.select('model3d_id', id=self._db_id)[0][0]

    @model3d_id.setter
    def model3d_id(self, value: int):
        self._table.update(self._db_id, model3d_id=value)
        self._populate('model3d_id')


class Model3DControl(_prop_grid.Category):

    def set_obj(self, db_obj: Model3DMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.angle3d_page.SetValue(None)
            self.position3d_page.SetValue(None)

            self.path_ctrl.SetWildcards('')
            self.path_ctrl.SetValue('')
            self.data_path_ctrl.SetValue('')
            self.uuid_ctrl.SetValue('')

            self.simplify_ctrl.SetValue(False)
            self.target_count_ctrl.SetValue(10000)
            self.update_rate_ctrl.SetValue(1)
            self.iterations_ctrl.SetValue(1)
            self.aggressiveness_ctrl.SetValue(1.0)

            self.name_ctrl.SetValue('')
            self.extension_ctrl.SetValue('')
            self.mimetype_ctrl.SetValue('')

            self.path_ctrl.Enable(False)
            self.data_path_ctrl.Enable(False)
            self.uuid_ctrl.Enable(False)

            self.simplify_ctrl.Enable(False)
            self.target_count_ctrl.Enable(False)
            self.update_rate_ctrl.Enable(False)
            self.iterations_ctrl.Enable(False)
            self.aggressiveness_ctrl.Enable(False)

            self.name_ctrl.Enable(False)
            self.extension_ctrl.Enable(False)
            self.mimetype_ctrl.Enable(False)
            self.set_preview_model()

        else:
            model3d = db_obj.model3d

            self.angle3d_page.SetValue(model3d)
            self.position3d_page.SetValue(model3d)

            self.path_ctrl.Enable(True)
            self.path_ctrl.SetWildcards(_utils.MODEL_FILE_WILDCARDS)

            if model3d is None:
                self.path_ctrl.SetValue('')
                self.data_path_ctrl.SetValue('')
                self.uuid_ctrl.SetValue('')

                self.simplify_ctrl.SetValue(False)
                self.target_count_ctrl.SetValue(10000)
                self.update_rate_ctrl.SetValue(1)
                self.iterations_ctrl.SetValue(1)
                self.aggressiveness_ctrl.SetValue(1.0)

                self.name_ctrl.SetValue('')
                self.extension_ctrl.SetValue('')
                self.mimetype_ctrl.SetValue('')

                self.data_path_ctrl.Enable(False)
                self.uuid_ctrl.Enable(False)

                self.simplify_ctrl.Enable(False)
                self.target_count_ctrl.Enable(False)
                self.update_rate_ctrl.Enable(False)
                self.iterations_ctrl.Enable(False)
                self.aggressiveness_ctrl.Enable(False)

                self.name_ctrl.Enable(False)
                self.extension_ctrl.Enable(False)
                self.mimetype_ctrl.Enable(False)
                self.set_preview_model()
            else:
                self.set_preview_model()

                self.path_ctrl.SetValue(model3d.path)
                self.data_path_ctrl.SetValue(model3d.data_path)
                self.uuid_ctrl.SetValue(model3d.uuid)

                self.simplify_ctrl.SetValue(model3d.simplify)
                self.target_count_ctrl.SetValue(model3d.target_count)
                self.update_rate_ctrl.SetValue(model3d.update_rate)
                self.iterations_ctrl.SetValue(model3d.iterations)
                self.aggressiveness_ctrl.SetValue(model3d.aggressiveness)

                filetype = model3d.file_type
                self.name_ctrl.SetValue(filetype.name)
                self.extension_ctrl.SetValue(filetype.extension)
                self.mimetype_ctrl.SetValue(filetype.mimetype)

                self.data_path_ctrl.Enable(True)
                self.uuid_ctrl.Enable(True)

                self.simplify_ctrl.Enable(True)
                self.target_count_ctrl.Enable(True)
                self.update_rate_ctrl.Enable(True)
                self.iterations_ctrl.Enable(True)
                self.aggressiveness_ctrl.Enable(True)

                self.name_ctrl.Enable(True)
                self.extension_ctrl.Enable(True)
                self.mimetype_ctrl.Enable(True)

    def set_preview_model(self):
        if self.db_obj is None:
            self.model_preview.set_model(None, None, None)
        else:
            model3d = self.db_obj.model3d

            if model3d is None:
                self.model_preview.set_model(None, None, None)
            else:
                vertices, faces = model3d.load()
                color = self.db_obj.color  # NOQA
                self.model_preview.set_model(color.ui, vertices, faces)

    def _on_path(self, evt):
        value = evt.GetValue()

        model3d = self.db_obj.table.db.models3d_table.insert(value)
        self.db_obj.model3d_id = model3d.db_id
        self.set_preview_model()

    def _on_simplify(self, evt):
        value = evt.GetValue()
        self.db_obj.model3d.simplify = value
        self.set_preview_model()

    def _on_target_count(self, evt):
        value = evt.GetValue()
        self.db_obj.model3d.target_count = value
        self.set_preview_model()

    def _on_update_rate(self, evt):
        value = evt.GetValue()
        self.db_obj.model3d.update_rate = value
        self.set_preview_model()

    def _on_iterations(self, evt):
        value = evt.GetValue()
        self.db_obj.model3d.iterations = value
        self.set_preview_model()

    def _on_aggressiveness(self, evt):
        value = evt.GetValue()
        self.db_obj.model3d.aggressiveness = value
        self.set_preview_model()

    def __init__(self, parent):
        self.db_obj: Model3DMixin = None

        super().__init__(parent, '3D Model')

        self.nb = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self.nb, 'General')
        self.path_ctrl = _prop_grid.PathProperty(general_page, 'Model Location')
        self.data_path_ctrl = _prop_grid.StringProperty(general_page, 'DB Path', '', style=wx.TE_READONLY)
        self.uuid_ctrl = _prop_grid.StringProperty(general_page, 'DB Path', '', style=wx.TE_READONLY)

        self.path_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_path)

        simplify_page = _prop_grid.Category(self.nb, 'Simplify')
        self.simplify_ctrl = _prop_grid.StringProperty(general_page, 'Enable', False)
        self.target_count_ctrl = _prop_grid.IntProperty(simplify_page, 'Target Vertices Count', 10000, min_value=10000, max_value=500000)
        self.update_rate_ctrl = _prop_grid.IntProperty(simplify_page, 'Update Rate', 1, min_value=1, max_value=100)
        self.iterations_ctrl = _prop_grid.IntProperty(simplify_page, 'Iterations', 1, min_value=1, max_value=100)
        self.aggressiveness_ctrl = _prop_grid.FloatProperty(simplify_page, 'Aggressiveness', 1.0, min_value=1.0, max_value=100.0, increment=0.1)

        self.simplify_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_simplify)
        self.target_count_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_target_count)
        self.update_rate_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_update_rate)
        self.iterations_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_iterations)
        self.aggressiveness_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_aggressiveness)

        file_type_page = _prop_grid.Category(self.nb, 'File Type')
        self.name_ctrl = _prop_grid.StringProperty(file_type_page, 'Name', '', style=wx.TE_READONLY)
        self.extension_ctrl = _prop_grid.StringProperty(file_type_page, 'File Extension', '', style=wx.TE_READONLY)
        self.mimetype_ctrl = _prop_grid.StringProperty(file_type_page, 'Minetype', '', style=wx.TE_READONLY)

        self.angle3d_page = _prop_grid.Angle3DProperty(self.nb, '3D Angle')
        self.position3d_page = _prop_grid.Angle3DProperty(self.nb, '3D Position')

        preview_page = _prop_grid.Category(self.nb, 'Model Preview')
        self.model_preview = _model_preview.PreviewCanvas(preview_page)

        for page in (
            general_page,
            simplify_page,
            file_type_page,
            self.angle3d_page,
            self.position3d_page,
            preview_page
        ):
            self.nb.AddPage(page, page.GetLabel())
            page.Realize()
