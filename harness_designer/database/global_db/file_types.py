from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class FileTypesTable(TableBase):
    __table_name__ = 'file_types'

    def _table_needs_update(self) -> bool:
        from ..create_database import file_types

        return file_types.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import file_types

        file_types.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        file_types.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import file_types

        file_types.table.update_fields(self)

    def __iter__(self) -> _Iterable["FileType"]:
        for db_id in TableBase.__iter__(self):
            yield FileType(self, db_id)

    def __getitem__(self, item) -> "FileType":
        if isinstance(item, int):
            if item in self:
                return FileType(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return FileType(self, db_id[0][0])

        raise KeyError(item)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str, mfg_id: int, description: str) -> "FileType":
        db_id = TableBase.insert(self, name=name, mfg_id=mfg_id, description=description)
        return FileType(self, db_id)


class FileType(EntryBase, NameMixin):
    _table: FileTypesTable = None

    def build_monitor_packet(self):
        packet = {
            'file_types': [self.db_id],
        }

        return packet

    @property
    def extension(self) -> str:
        return self._table.select('extension', id=self._db_id)[0][0]

    @extension.setter
    def extension(self, value: str):
        self._table.update(self._db_id, extension=value)

    @property
    def mimetype(self) -> str:
        return self._table.select('mimetype', id=self._db_id)[0][0]

    @mimetype.setter
    def mimetype(self, value: str):
        self._table.update(self._db_id, mimetype=value)

    @property
    def is_model(self) -> bool:
        return bool(self._table.select('is_model', id=self._db_id)[0][0])

    @is_model.setter
    def is_model(self, value: bool):
        self._table.update(self._db_id, is_model=int(value))

    @property
    def propgrid(self) -> wxpg.PGProperty:
        from ...ui.editor_obj.prop_grid import combobox_prop as _combobox_prop
        from ...ui.editor_obj.prop_grid import bool_prop as _bool_prop

        file_type_prop = wxpg.PGProperty('File Type')

        rows = self.table.select('mimetype')

        choices = [item[0] for item in rows]
        mimetype_prop = _combobox_prop.ComboboxProperty('MimeType', 'mimetype', self.name, choices)
        rows = self.table.select('extension')

        choices = [item[0] for item in rows]
        extension_prop = _combobox_prop.ComboboxProperty('Extension', 'extension', self.name, choices)
        is_model_prop = _bool_prop.BoolProperty('Is Model', 'is_model', self.is_model)

        file_type_prop.AppendChild(mimetype_prop)
        file_type_prop.AppendChild(extension_prop)
        file_type_prop.AppendChild(is_model_prop)

        return file_type_prop

