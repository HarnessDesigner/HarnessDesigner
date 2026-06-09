# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import os
from PySide6 import QtGui
from PySide6 import QtPdf
from PySide6 import QtSvg
import ezdxf

import weakref

from ... import resources as _resources
from ..create_database import cads as _cads
from .bases import EntryBase, TableBase


if TYPE_CHECKING:
    from . import file_types as _file_types


class CADsTable(TableBase):
    """Represent a ca ds table in :mod:`harness_designer.database.global_db.cad`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'cads'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return _cads.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        _cads.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        _cads.table.update_fields(self)

    def __iter__(self) -> _Iterable["CAD"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['CAD']
        """
        for db_id in TableBase.__iter__(self):
            yield CAD(self, db_id)

    def __getitem__(self, item) -> "CAD":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CAD`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return CAD(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str) -> "CAD":  # NOQA
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`CAD`
        """
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
    """Represent a cad in :mod:`harness_designer.database.global_db.cad`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: CADsTable = None
    _callbacks = {}

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'cads': [self.db_id]
        }

        file_type_id = self.file_type_id
        if file_type_id is not None:
            packet['file_types'] = [file_type_id]

        return packet

    def load(self, mfg, part_number, callback) -> QtGui.QPixmap:
        """
        Load a CAD file.

        This function schedules the loading to take place using a child process.
        The reason why this is done is for multi seat environments and not
        duplicating image downloads and also to provide a way to audit failed
        downloads so a system administrator can fix what is wrong.

        :param mfg: Manufacturer of the part.
        :type mfg: str

        :param part_number: Part number of part that uses this model.
        :type part_number: str

        :param callback: callback that takes :class:`Image` and
                         :class:`QtPdf.QPdfDocument` |
                         :class:`ezdxf.Drawing` |
                         :class:`QtSvg.QSvgRenderer` |
                         :class:`QtGui.QPixmap`
                         instances as parameters.

        :type callback: callable

        :returns: ``None``.
        :rtype: None
        """

        file = self.data_path

        if file is None:

            if (_resources.RESOURCE_TYPE_CAD, self.db_id) in self._table.db.resource_state_table:
                resource_state = self._table.db.resource_state_table[(_resources.RESOURCE_TYPE_CAD, self.db_id)]
            else:
                resource_state = self._table.db.resource_state_table.insert(_resources.RESOURCE_TYPE_CAD, self.db_id)

            if resource_state.allow_retry:
                if resource_state.progress == -1:
                    resource_state.progress = 0

                def _do():
                    # ensures the callbacks only get called a simgle time
                    if self.db_id not in self._callbacks:
                        return

                    file_ = self.data_path
                    if file_ is not None:
                        # we need to determine the type of
                        # file type that is being used
                        if file_.endswith('.pdf'):
                            data_ = QtPdf.QPdfDocument()
                            data_.load(file_)
                        elif file_.endswith('.dxf'):
                            data_ = ezdxf.readfile(file_)
                        elif file_.endswith('.svg'):
                            data_ = QtSvg.QSvgRenderer(file_)
                        else:
                            data_ = QtGui.QPixmap(file_)

                        for ref_ in self._callbacks[self.db_id]:
                            cb_ = ref_()
                            if cb_ is None:
                                continue

                            cb_(self, data_)

                        del self._callbacks[self.db_id]

                if self.db_id not in self._callbacks:
                    self._callbacks[self.db_id] = []

                self._callbacks[self.db_id].append(weakref.WeakMethod(callback))

                cad_path = self._table.db.settings_table['cad_path']

                self._table.db.mainframe.process_manager.get_cad(
                    self, resource_state, mfg, part_number, cad_path, _do)
        else:
            # we need to determine the type of file type that is being used

            if file.endswith('.pdf'):
                data = QtPdf.QPdfDocument()
                data.load(file)
            elif file.endswith('.dxf'):
                data = ezdxf.readfile(file)
            elif file.endswith('.svg'):
                data = QtSvg.QSvgRenderer(file)
            else:
                data = QtGui.QPixmap(file)

            if self.db_id in self._callbacks:
                for ref in self._callbacks[self.db_id]:
                    cb = ref()
                    if cb is None:
                        continue

                    cb(self, data)

                del self._callbacks[self.db_id]

            callback(self, data)

    @property
    def data_path(self) -> str | None:
        """Return the data path.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        file_id = self.uuid
        if file_id is None:
            return None

        file_type = self.file_type

        cad_path = self._table.db.settings_table['cad_path']
        path = os.path.join(cad_path, file_id[:2], f'{file_id}.{file_type.extension}')

        if os.path.exists(path):
            return path

    @property
    def path(self) -> str:
        """Return the path.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        path = self._table.select('path', id=self._db_id)[0][0]
        return path

    @property
    def uuid(self) -> str | None:
        """Return the uuid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        return self._table.select('uuid', id=self._db_id)[0][0]

    @property
    def file_type(self) -> "_file_types.FileType":
        """Return the file type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_file_types.FileType`
        """
        db_id = self.file_type_id
        if db_id is None:
            return None

        return self._table.db.file_types_table[db_id]

    @property
    def file_type_id(self) -> int | None:
        """Return the file type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        return self._table.select('file_type_id', id=self._db_id)[0][0]

    @file_type_id.setter
    def file_type_id(self, value: int):
        """Set the file type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, file_type_id=value)
        self._populate('file_type_id')
