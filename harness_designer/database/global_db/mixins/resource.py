from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class ResourceMixin(BaseMixin):

    @property
    def cad(self) -> str | None:
        db_id = self.cad_id

        if db_id is None:
            return None

        cad = self._table.db.cads_table[db_id]
        return cad.data_path

    @property
    def cad_type(self) -> str | None:
        cad_id = self.cad_id

        if cad_id is None:
            return None

        cad = self._table.db.cads_table[cad_id]
        if cad.data_path is not None:
            return cad.file_type.extension

    @property
    def cad_id(self) -> int:
        return self._table.select('cad_id', id=self._db_id)[0][0]

    @cad_id.setter
    def cad_id(self, value: int):
        self._table.update(self._db_id, cad_id=value)

    @property
    def image(self) -> str | None:
        db_id = self.image_id
        if db_id is None:
            return None

        image = self._table.db.images_table[db_id]
        return image.data_path

    @property
    def image_type(self) -> str:
        image_id = self.image_id

        if image_id is None:
            return None

        image = self._table.db.images_table[image_id]
        if image.data_path is not None:
            return image.file_type.extension

    @property
    def image_id(self) -> int:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @image_id.setter
    def image_id(self, value: int):
        self._table.update(self._db_id, image_id=value)

    @property
    def datasheet(self) -> str | None:
        db_id = self.datasheet_id
        if db_id is None:
            return None

        datasheet = self._table.db.datasheets_table[db_id]
        return datasheet.data_path

    @property
    def datasheet_type(self) -> str:
        datasheet_id = self.datasheet_id

        if datasheet_id is None:
            return None

        datasheet = self._table.db.datasheets_table[datasheet_id]
        if datasheet.data_path is not None:
            return datasheet.file_type.extension

    @property
    def datasheet_id(self) -> int:
        return self._table.select('datasheet_id', id=self._db_id)[0][0]

    @datasheet_id.setter
    def datasheet_id(self, value: int):
        self._table.update(self._db_id, datasheet_id=value)


class ResourcesControl(_prop_grid.Category):

    def __init__(self, parent):
        super().__init__(parent, 'Resources')
        self.db_obj: ResourceMixin = None
        self.file_types: dict = None

        self.image_ctrl = _prop_grid.ImageProperty(self, 'Image', '', {})
        self.datasheet_ctrl = _prop_grid.DatasheetCADProperty(self, 'Datasheet', '', {})
        self.cad_ctrl = _prop_grid.DatasheetCADProperty(self, 'CAD', '', {})

        self.image_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_image)
        self.datasheet_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_datasheet)
        self.cad_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_cad)

    def set_obj(self, db_obj: ResourceMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.image_ctrl.SetValue(['', None])
            self.datasheet_ctrl.SetValue(['', None])
            self.cad_ctrl.SetValue(['', None])

            self.image_ctrl.Enable(False)
            self.datasheet_ctrl.Enable(False)
            self.cad_ctrl.Enable(False)

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

            self.image_ctrl.Enable(True)
            self.datasheet_ctrl.Enable(True)
            self.cad_ctrl.Enable(True)

    def _on_image(self, evt):
        path = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM images WHERE path="{path}";')
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
        path = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM cads WHERE path="{path}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.cads_table.insert(path)
            db_id = db_obj.db_id

        self.db_obj.cad_id = db_id

        cad = self.db_obj.table.db.cads_table[db_id]

        self.image_ctrl.SetValue([path, cad.data_path])

    def _on_datasheet(self, evt):
        path = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM datasheets WHERE path="{path}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.datasheets_table.insert(path)
            db_id = db_obj.db_id

        self.db_obj.datasheet_id = db_id

        datasheet = self.db_obj.table.db.datasheet_table[db_id]

        self.image_ctrl.SetValue([path, datasheet.data_path])
