# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin


class FileTypesTable(TableBase):
    """Represent a file types table in :mod:`harness_designer.database.global_db.file_types`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'file_types'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import file_types

        return file_types.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import file_types

        file_types.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        file_types.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import file_types

        file_types.table.update_fields(self)

    def __iter__(self) -> _Iterable["FileType"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['FileType']
        """
        for db_id in TableBase.__iter__(self):
            yield FileType(self, db_id)

    def __getitem__(self, item) -> "FileType":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FileType`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
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
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]

    def insert(self, name: str, mfg_id: int, description: str) -> "FileType":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param mfg_id: Identifier for the mfg.
        :type mfg_id: int
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`FileType`
        """
        db_id = TableBase.insert(self, name=name, mfg_id=mfg_id, description=description)
        return FileType(self, db_id)


class FileType(EntryBase, NameMixin):
    """Represent a file type in :mod:`harness_designer.database.global_db.file_types`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: FileTypesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'file_types': [self.db_id],
        }

        return packet

    @property
    def extension(self) -> str:
        """Return the extension.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('extension', id=self._db_id)[0][0]

    @extension.setter
    def extension(self, value: str):
        """Set the extension.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, extension=value)
        self._populate('extension')

    @property
    def mimetype(self) -> str:
        """Return the mimetype.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('mimetype', id=self._db_id)[0][0]

    @mimetype.setter
    def mimetype(self, value: str):
        """Set the mimetype.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, mimetype=value)
        self._populate('mimetype')

    @property
    def is_model(self) -> bool:
        """Return the is model.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_model', id=self._db_id)[0][0])

    @is_model.setter
    def is_model(self, value: bool):
        """Set the is model.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_model=int(value))
        self._populate('is_model')
