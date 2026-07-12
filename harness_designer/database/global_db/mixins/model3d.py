# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


from .... import utils as _utils
from PySide6.QtWidgets import QTabWidget
from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

if TYPE_CHECKING:
    from .. import model3d as _model3d


class Model3DMixin(BaseMixin):
    """Represent a model 3dmixin in :mod:`harness_designer.database.global_db.mixins.model3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_model3d: "DefaultStoredValueType | _model3d.Model3D | None" = DefaultStoredValue

    @property
    def model3d(self) -> "_model3d.Model3D":
        """Return the model 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_model3d.Model3D`
        """
        if self._stored_model3d is DefaultStoredValue:
            model3d_id = self.model3d_id

            if model3d_id is None:
                self._stored_model3d = None
            else:
                self._stored_model3d = self._table.db.models3d_table[model3d_id]

        return self._stored_model3d

    _stored_model3d_id: int | DefaultStoredValueType | None = DefaultStoredValue

    @property
    def model3d_id(self) -> int:
        """Return the model 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_model3d_id is DefaultStoredValue:
            self._stored_model3d_id = self._table.select('model3d_id', id=self._db_id)[0][0]

        return self._stored_model3d_id

    @model3d_id.setter
    def model3d_id(self, value: int):
        """Set the model 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_model3d_id = value
        self._stored_model3d = DefaultStoredValue
        self._table.update(self._db_id, model3d_id=value)
        self._populate('model3d_id')


class Model3DControl(_prop_ctrls.Category):
    """Represent a model 3dcontrol in :mod:`harness_designer.database.global_db.mixins.model3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: Model3DMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Model3DMixin`
        """
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

            self.path_ctrl.setEnabled(False)
            self.data_path_ctrl.setEnabled(False)
            self.uuid_ctrl.setEnabled(False)

            self.simplify_ctrl.setEnabled(False)
            self.target_count_ctrl.setEnabled(False)
            self.update_rate_ctrl.setEnabled(False)
            self.iterations_ctrl.setEnabled(False)
            self.aggressiveness_ctrl.setEnabled(False)

            self.name_ctrl.setEnabled(False)
            self.extension_ctrl.setEnabled(False)
            self.mimetype_ctrl.setEnabled(False)
            self.set_preview_model()

        else:
            model3d = db_obj.model3d

            self.path_ctrl.setEnabled(True)
            self.path_ctrl.SetWildcards(_utils.MODEL_FILE_WILDCARDS)

            if model3d is None:
                self.angle3d_page.SetValue(None)
                self.position3d_page.SetValue(None)

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

                self.data_path_ctrl.setEnabled(False)
                self.uuid_ctrl.setEnabled(False)

                self.simplify_ctrl.setEnabled(False)
                self.target_count_ctrl.setEnabled(False)
                self.update_rate_ctrl.setEnabled(False)
                self.iterations_ctrl.setEnabled(False)
                self.aggressiveness_ctrl.setEnabled(False)

                self.name_ctrl.setEnabled(False)
                self.extension_ctrl.setEnabled(False)
                self.mimetype_ctrl.setEnabled(False)
                self.set_preview_model()
            else:
                self.set_preview_model()

                self.angle3d_page.SetValue(model3d.angle3d)
                self.position3d_page.SetValue(model3d.position3d)

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

                self.data_path_ctrl.setEnabled(True)
                self.uuid_ctrl.setEnabled(True)

                self.simplify_ctrl.setEnabled(True)
                self.target_count_ctrl.setEnabled(True)
                self.update_rate_ctrl.setEnabled(True)
                self.iterations_ctrl.setEnabled(True)
                self.aggressiveness_ctrl.setEnabled(True)

                self.name_ctrl.setEnabled(True)
                self.extension_ctrl.setEnabled(True)
                self.mimetype_ctrl.setEnabled(True)

    def set_preview_model(self):
        """Set the preview model.

        UNKNOWN details are inferred from the callable name and signature.
        """
        # if self.db_obj is None:
        #     self.model_preview.set_model(None, None, None)
        # else:
        #     model3d = self.db_obj.model3d
        #
        #     if model3d is None:
        #         self.model_preview.set_model(None, None, None)
        #     else:
        #         vertices, faces = model3d.load()
        #         color = self.db_obj.color  # NOQA
        #         self.model_preview.set_model(color.ui, vertices, faces)
        pass

    def _on_path(self, evt):
        """Handle the path event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()

        model3d = self.db_obj.table.db.models3d_table.insert(value)
        self.db_obj.model3d_id = model3d.db_id
        self.set_preview_model()

    def _on_simplify(self, evt):
        """Handle the simplify event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.model3d.simplify = value
        self.set_preview_model()

    def _on_target_count(self, evt):
        """Handle the target count event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.model3d.target_count = value
        self.set_preview_model()

    def _on_update_rate(self, evt):
        """Handle the update rate event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.model3d.update_rate = value
        self.set_preview_model()

    def _on_iterations(self, evt):
        """Handle the iterations event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.model3d.iterations = value
        self.set_preview_model()

    def _on_aggressiveness(self, evt):
        """Handle the aggressiveness event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.model3d.aggressiveness = value
        self.set_preview_model()

    def __init__(self, parent):
        """Initialise the :class:`Model3DControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Model3DMixin = None

        super().__init__(parent, '3D Model')

        self.nb = QTabWidget(self)
        self.nb.setTabPosition(QTabWidget.TabPosition.North)
        self.nb.setUsesScrollButtons(True)

        self.addWidget(self.nb)

        general_page = _prop_ctrls.Category(self.nb, 'General')
        self.path_ctrl = _prop_ctrls.PathProperty(general_page, 'Model Location')
        self.data_path_ctrl = _prop_ctrls.StringProperty(general_page, 'DB Path', read_only=True)
        self.uuid_ctrl = _prop_ctrls.StringProperty(general_page, 'DB Path', read_only=True)

        general_page.addWidget(self.path_ctrl)
        general_page.addWidget(self.data_path_ctrl)
        general_page.addWidget(self.uuid_ctrl)

        self.path_ctrl.propertyChanged.connect(self._on_path)

        simplify_page = _prop_ctrls.Category(self.nb, 'Simplify')
        self.simplify_ctrl = _prop_ctrls.BoolProperty(general_page, 'Enable')
        self.target_count_ctrl = _prop_ctrls.IntProperty(simplify_page, 'Target Vertices Count', min_value=10000, max_value=500000)
        self.update_rate_ctrl = _prop_ctrls.IntProperty(simplify_page, 'Update Rate', min_value=1, max_value=100)
        self.iterations_ctrl = _prop_ctrls.IntProperty(simplify_page, 'Iterations', min_value=1, max_value=100)
        self.aggressiveness_ctrl = _prop_ctrls.FloatProperty(simplify_page, 'Aggressiveness', min_value=1.0, max_value=100.0, increment=0.1)

        simplify_page.addWidget(self.simplify_ctrl)
        simplify_page.addWidget(self.target_count_ctrl)
        simplify_page.addWidget(self.update_rate_ctrl)
        simplify_page.addWidget(self.iterations_ctrl)
        simplify_page.addWidget(self.aggressiveness_ctrl)

        self.simplify_ctrl.propertyChanged.connect(self._on_simplify)
        self.target_count_ctrl.propertyChanged.connect(self._on_target_count)
        self.update_rate_ctrl.propertyChanged.connect(self._on_update_rate)
        self.iterations_ctrl.propertyChanged.connect(self._on_iterations)
        self.aggressiveness_ctrl.propertyChanged.connect(self._on_aggressiveness)

        file_type_page = _prop_ctrls.Category(self.nb, 'File Type')
        self.name_ctrl = _prop_ctrls.StringProperty(file_type_page, 'Name', read_only=True)
        self.extension_ctrl = _prop_ctrls.StringProperty(file_type_page, 'File Extension', read_only=True)
        self.mimetype_ctrl = _prop_ctrls.StringProperty(file_type_page, 'Minetype', read_only=True)

        file_type_page.addWidget(self.name_ctrl)
        file_type_page.addWidget(self.extension_ctrl)
        file_type_page.addWidget(self.mimetype_ctrl)

        self.angle3d_page = _prop_ctrls.Angle3DProperty(self.nb, '3D Angle')
        self.position3d_page = _prop_ctrls.Angle3DProperty(self.nb, '3D Position')

        preview_page = _prop_ctrls.Category(self.nb, 'Model Preview')
        # self.model_preview = _model_preview.PreviewCanvas(preview_page)
        # preview_page.addWidget(self.model_preview)

        for page in (
            general_page,
            simplify_page,
            file_type_page,
            self.angle3d_page,
            self.position3d_page,
            preview_page
        ):
            self.nb.addTab(page, page.GetLabel())
