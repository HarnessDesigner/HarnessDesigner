from .base import BaseMixin


class ResourceMixin(BaseMixin):

    def __get_resource(self, db_id):
        if db_id is None:
            return None

        resource = self._table.db.resources_table[db_id]
        return resource.data

    def __set_resource(self, db_id, value) -> int:

        if isinstance(value, (bytes, None)):
            if db_id is None:
                resource = self._table.db.resources_table.insert(path=None, data=value, type='')
                db_id = resource.db_id
            else:
                resource = self._table.db.resources_table[db_id]
                resource.data = value
        else:
            if db_id is None:
                resource = self._table.db.resources_table.insert(path=value, data=None, type='')
                db_id = resource.db_id
            else:
                resource = self._table.db.resources_table[db_id]
                if value.startswith('http'):
                    resource.http = value
                else:
                    resource.path = value
        return db_id

    def __get_resource_type(self, db_id):
        if db_id is None:
            return ''
        resource = self._table.db.resources_table[db_id]
        return resource.type

    def __set_resource_type(self, db_id, value):
        if db_id is None:
            resource = self._table.db.resources_table.insert(path=None, data=None, type=value)
            db_id = resource.db_id
        else:
            resource = self._table.db.resources_table[db_id]
            resource.type = value

        return db_id

    @property
    def cad(self) -> bytes | None:
        return self.__get_resource(self.cad_id)

    @cad.setter
    def cad(self, value: bytes | str | None):
        self.cad_id = self.__set_resource(self.cad_id, value)

    @property
    def cad_type(self) -> str:
        return self.__get_resource_type(self.cad_id)

    @cad_type.setter
    def cad_type(self, value: str):
        self.cad_id = self.__set_resource_type(self.cad_id, value)

    @property
    def cad_id(self) -> int:
        return self._table.select('cad_id', id=self._db_id)[0][0]

    @cad_id.setter
    def cad_id(self, value: int):
        self._table.update(self._db_id, cad_id=value)

    @property
    def image(self) -> bytes | None:
        return self.__get_resource(self.image_id)

    @image.setter
    def image(self, value: bytes | str | None):
        self.image_id = self.__set_resource(self.image_id, value)

    @property
    def image_type(self) -> str:
        return self.__get_resource_type(self.image_id)

    @image_type.setter
    def image_type(self, value: str):
        self.image_id = self.__set_resource_type(self.image_id, value)

    @property
    def image_id(self) -> int:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @image_id.setter
    def image_id(self, value: int):
        self._table.update(self._db_id, image_id=value)

    @property
    def datasheet(self) -> bytes | None:
        return self.__get_resource(self.datasheet_id)

    @datasheet.setter
    def datasheet(self, value: bytes | str | None):
        self.datasheet_id = self.__set_resource(self.datasheet_id, value)

    @property
    def datasheet_type(self) -> str:
        return self.__get_resource_type(self.datasheet_id)

    @datasheet_type.setter
    def datasheet_type(self, value: str):
        self.datasheet_id = self.__set_resource_type(self.datasheet_id, value)

    @property
    def datasheet_id(self) -> int:
        return self._table.select('datasheet_id', id=self._db_id)[0][0]

    @datasheet_id.setter
    def datasheet_id(self, value: int):
        self._table.update(self._db_id, datasheet_id=value)
