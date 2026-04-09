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

    @property
    def _resource_propgrid(self) -> _prop_grid.Property:
        group_prop = _prop_grid.Property('Resources', '')
        image_id = self.image_id
        datasheet_id = self.datasheet_id
        cad_id = self.cad_id

        image = self._table.db.images_table[image_id]
        image_prop = image.propgrid
        group_prop.Append(image_prop)

        datasheet = self._table.db.datasheets_table[datasheet_id]
        datasheet_prop = datasheet.propgrid
        group_prop.Append(datasheet_prop)

        cad = self._table.db.cads_table[cad_id]
        cad_prop = cad.propgrid
        group_prop.Append(cad_prop)

        return group_prop
