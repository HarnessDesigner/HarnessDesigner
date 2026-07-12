# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import cad as _cad_mod
    from .. import image as _image_mod
    from .. import datasheet as _datasheet_mod


class ResourceMixin(BaseMixin):
    """Represent a resource mixin in :mod:`harness_designer.database.global_db.mixins.resource`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_cad_obj: "DefaultStoredValueType | _cad_mod.CAD | None" = DefaultStoredValue

    def _get_cad_obj(self) -> "_cad_mod.CAD | None":
        """Return (and cache) the related CAD row, shared by ``cad``/``cad_type``."""
        if self._stored_cad_obj is DefaultStoredValue:
            cad_id = self.cad_id

            if cad_id is None:
                self._stored_cad_obj = None
            else:
                self._stored_cad_obj = self._table.db.cads_table[cad_id]

        return self._stored_cad_obj

    @property
    def cad(self) -> str | None:
        """Return the cad.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        cad = self._get_cad_obj()
        if cad is None:
            return None

        return cad.data_path

    @property
    def cad_type(self) -> str | None:
        """Return the cad type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        cad = self._get_cad_obj()

        if cad is not None and cad.data_path is not None:
            return cad.file_type.extension

    _stored_cad_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def cad_id(self) -> int:
        """Return the cad ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_cad_id is DefaultStoredValue:
            self._stored_cad_id = self._table.select('cad_id', id=self._db_id)[0][0]

        return self._stored_cad_id

    @cad_id.setter
    def cad_id(self, value: int):
        """Set the cad ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_cad_id = value
        self._stored_cad_obj = DefaultStoredValue
        self._table.update(self._db_id, cad_id=value)
        self._populate('cad_id')

    _stored_image_obj: "DefaultStoredValueType | _image_mod.Image | None" = DefaultStoredValue

    def _get_image_obj(self) -> "_image_mod.Image | None":
        """Return (and cache) the related Image row, shared by ``image``/``image_type``."""
        if self._stored_image_obj is DefaultStoredValue:
            image_id = self.image_id

            if image_id is None:
                self._stored_image_obj = None
            else:
                self._stored_image_obj = self._table.db.images_table[image_id]

        return self._stored_image_obj

    @property
    def image(self) -> str | None:
        """Return the image.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        image = self._get_image_obj()
        if image is None:
            return None

        return image.data_path

    @property
    def image_type(self) -> str:
        """Return the image type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        image = self._get_image_obj()

        if image is not None and image.data_path is not None:
            return image.file_type.extension

    _stored_image_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def image_id(self) -> int:
        """Return the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_image_id is DefaultStoredValue:
            self._stored_image_id = self._table.select('image_id', id=self._db_id)[0][0]

        return self._stored_image_id

    @image_id.setter
    def image_id(self, value: int):
        """Set the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_image_id = value
        self._stored_image_obj = DefaultStoredValue
        self._table.update(self._db_id, image_id=value)
        self._populate('image_id')

    _stored_datasheet_obj: "DefaultStoredValueType | _datasheet_mod.Datasheet | None" = DefaultStoredValue

    def _get_datasheet_obj(self) -> "_datasheet_mod.Datasheet | None":
        """Return (and cache) the related Datasheet row, shared by ``datasheet``/``datasheet_type``."""
        if self._stored_datasheet_obj is DefaultStoredValue:
            datasheet_id = self.datasheet_id

            if datasheet_id is None:
                self._stored_datasheet_obj = None
            else:
                self._stored_datasheet_obj = self._table.db.datasheets_table[datasheet_id]

        return self._stored_datasheet_obj

    @property
    def datasheet(self) -> str | None:
        """Return the datasheet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        datasheet = self._get_datasheet_obj()
        if datasheet is None:
            return None

        return datasheet.data_path

    @property
    def datasheet_type(self) -> str:
        """Return the datasheet type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        datasheet = self._get_datasheet_obj()

        if datasheet is not None and datasheet.data_path is not None:
            return datasheet.file_type.extension

    _stored_datasheet_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def datasheet_id(self) -> int:
        """Return the datasheet ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_datasheet_id is DefaultStoredValue:
            self._stored_datasheet_id = self._table.select('datasheet_id', id=self._db_id)[0][0]

        return self._stored_datasheet_id

    @datasheet_id.setter
    def datasheet_id(self, value: int):
        """Set the datasheet ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_datasheet_id = value
        self._stored_datasheet_obj = DefaultStoredValue
        self._table.update(self._db_id, datasheet_id=value)
        self._populate('datasheet_id')


class ResourcesControl(_prop_ctrls.Category):
    """Represent a resources control in :mod:`harness_designer.database.global_db.mixins.resource`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`ResourcesControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Resources')
        self.db_obj: ResourceMixin = None
        self.file_types: dict = None

        self.image_ctrl = _prop_ctrls.ImageProperty(self, 'Image')
        self.datasheet_ctrl = _prop_ctrls.DatasheetCADProperty(self, 'Datasheet')
        self.cad_ctrl = _prop_ctrls.DatasheetCADProperty(self, 'CAD')

        self.addWidget(self.image_ctrl)
        self.addWidget(self.datasheet_ctrl)
        self.addWidget(self.cad_ctrl)

        self.image_ctrl.propertyChanged.connect(self._on_image)
        self.datasheet_ctrl.propertyChanged.connect(self._on_datasheet)
        self.cad_ctrl.propertyChanged.connect(self._on_cad)

    def set_obj(self, db_obj: ResourceMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ResourceMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.image_ctrl.SetValue(['', None])
            self.datasheet_ctrl.SetValue(['', None])
            self.cad_ctrl.SetValue(['', None])

            self.image_ctrl.setEnabled(False)
            self.datasheet_ctrl.setEnabled(False)
            self.cad_ctrl.setEnabled(False)

        else:
            db_obj.table.execute('SELECT mimetype, extension FROM file_types WHERE is_model=0;')
            rows = db_obj.table.fetchall()

            self.file_types = {k: v for k, v in rows}

            self.image_ctrl.SetFileTypes(self.file_types)
            self.datasheet_ctrl.SetFileTypes(self.file_types)
            self.cad_ctrl.SetFileTypes(self.file_types)

            db_id = db_obj.image_id
            if db_id is None:
                self.image_ctrl.SetValue(['', None])
            else:
                image = db_obj.table.db.images_table[db_id]

                self.image_ctrl.SetValue([image.path, image.data_path])

            db_id = db_obj.cad_id
            if db_id is None:
                self.cad_ctrl.SetValue(['', None])
            else:
                image = db_obj.table.db.cads_table[db_id]

                self.cad_ctrl.SetValue([image.path, image.data_path])

            db_id = db_obj.datasheet_id
            if db_id is None:
                self.datasheet_ctrl.SetValue(['', None])
            else:
                image = db_obj.table.db.datasheets_table[db_id]

                self.datasheet_ctrl.SetValue([image.path, image.data_path])

            self.image_ctrl.setEnabled(True)
            self.datasheet_ctrl.setEnabled(True)
            self.cad_ctrl.setEnabled(True)

    def _on_image(self, evt):
        """Handle the image event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        path = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM images WHERE path=?;', (path,))
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.images_table.insert(path)
            db_id = db_obj.db_id

        self.db_obj.image_id = db_id

        image = self.db_obj.table.db.images_table[db_id]

        self.image_ctrl.SetValue([path, image.data_path])

    def _on_cad(self, evt):
        """Handle the cad event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        path = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM cads WHERE path=?;', (path,))
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.cads_table.insert(path)
            db_id = db_obj.db_id

        self.db_obj.cad_id = db_id

        cad = self.db_obj.table.db.cads_table[db_id]

        self.cad_ctrl.SetValue([path, cad.data_path])

    def _on_datasheet(self, evt):
        """Handle the datasheet event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        path = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM datasheets WHERE path=?;', (path,))
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.datasheets_table.insert(path)
            db_id = db_obj.db_id

        self.db_obj.datasheet_id = db_id

        datasheet = self.db_obj.table.db.datasheets_table[db_id]

        self.datasheet_ctrl.SetValue([path, datasheet.data_path])
