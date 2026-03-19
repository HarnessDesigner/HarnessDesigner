from typing import Iterable as _Iterable, TYPE_CHECKING
import os

from ... import resources as _resources
from ..create_database import images as _images

from .bases import EntryBase, TableBase

if TYPE_CHECKING:
    from . import file_types as _file_types


class ImagesTable(TableBase):
    __table_name__ = 'images'

    def _table_needs_update(self) -> bool:
        return _images.table.is_ok(self)

    def _add_table_to_db(self, _):
        _images.table.add_to_db(self)

    def _update_table_in_db(self):
        _images.table.update_fields(self)

    def __iter__(self) -> _Iterable["Image"]:
        for db_id in TableBase.__iter__(self):
            yield Image(self, db_id)

    def __getitem__(self, item) -> "Image":
        if isinstance(item, int):
            if item in self:
                return Image(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str) -> "Image":  # NOQA
        self._con.execute(f'SELECT id FROM images WHERE path="{path}";')
        rows = self._con.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_id = _images.get_image_id(self._con, path)
            if db_id is None:
                return None

        return Image(self, db_id)


class Image(EntryBase):
    _table: ImagesTable = None

    @property
    def data_path(self) -> str | None:
        file_id = self.uuid
        if file_id is None:
            values = _resources.collect_resource(self, _resources.IMAGE_TYPE_IMAGE, self.path)
            if values is None:
                return None

            file_id, file_type_id = values

            self._table.update(self._db_id, file_type_id=file_type_id)
            self._table.update(self._db_id, uuid=file_id)

        file_type = self.file_type

        image_path = self._table.db.settings_table['image_path']
        return os.path.join(image_path, f'{file_id}.{file_type.extension}')

    @property
    def path(self) -> str:
        path = self._table.select('path', id=self._db_id)[0][0]
        return path

    @property
    def uuid(self) -> str | None:
        return self._table.select('uuid', id=self._db_id)[0][0]

    @property
    def file_type(self) -> "_file_types.FileType":
        db_id = self.file_type_id
        if db_id is None:
            return None

        return self._table.db.file_types_table[db_id]

    @property
    def file_type_id(self) -> int | None:
        return self._table.select('file_type_id', id=self._db_id)[0][0]

    @file_type_id.setter
    def file_type_id(self, value: int):
        self._table.update(self._db_id, file_type_id=value)
