from typing import Iterable as _Iterable, TYPE_CHECKING

from ...ui.editor_obj import prop_grid as _prop_grid
import os

from ... import resources as _resources
from ..create_database import cads as _cads

from .bases import EntryBase, TableBase

if TYPE_CHECKING:
    from . import file_types as _file_types


class CADsTable(TableBase):
    __table_name__ = 'cads'

    def _table_needs_update(self) -> bool:
        return _cads.table.is_ok(self)

    def _add_table_to_db(self, _):
        _cads.table.add_to_db(self)

    def _update_table_in_db(self):
        _cads.table.update_fields(self)

    def __iter__(self) -> _Iterable["CAD"]:
        for db_id in TableBase.__iter__(self):
            yield CAD(self, db_id)

    def __getitem__(self, item) -> "CAD":
        if isinstance(item, int):
            if item in self:
                return CAD(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str) -> "CAD":  # NOQA
        self._con.execute(f'SELECT id FROM cads WHERE path="{path}";')
        rows = self._con.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_id = _cads.get_cad_id(self._con, path)
            if db_id is None:
                return None

        return CAD(self, db_id)


class CAD(EntryBase):
    _table: CADsTable = None

    def build_monitor_packet(self):
        packet = {
            'cads': [self.db_id]
        }

        file_type_id = self.file_type_id
        if file_type_id is not None:
            packet['file_types'] = [file_type_id]

        return packet

    @property
    def data_path(self) -> str | None:
        file_id = self.uuid
        if file_id is None:
            values = _resources.collect_resource(self._table, _resources.IMAGE_TYPE_CAD, self.path)
            if values is None:
                return None

            file_id, file_type_id = values

            self._table.update(self._db_id, file_type_id=file_type_id)
            self._table.update(self._db_id, uuid=file_id)

        file_type = self.file_type

        cad_path = self._table.db.settings_table['cad_path']
        return os.path.join(cad_path, f'{file_id}.{file_type.extension}')

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

    @property
    def propgrid(self) -> _prop_grid.Property:
        file_types = self._table.db.file_types_table.select('mimetype', 'extension', is_model=0)

        file_types = {k: v for k, v in file_types}
        cad_prop = _prop_grid.DatasheetCADProperty('CAD', 'cad', self.path, file_types, self.data_path)

        return cad_prop
