# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import os
from PySide6 import QtGui
import weakref

from ... import resources as _resources
from ..create_database import images as _images
from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from . import file_types as _file_types


class ImagesTable(TableBase):
    """Represent an images table in :mod:`harness_designer.database.global_db.image`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'images'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return _images.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        _images.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        _images.table.update_fields(self)

    def __iter__(self) -> _Iterable["Image"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Image']
        """
        for db_id in TableBase.__iter__(self):
            yield Image(self, db_id)

    def __getitem__(self, item) -> "Image":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Image`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Image(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str) -> "Image":  # NOQA
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Image`
        """
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
    """Represent an image in :mod:`harness_designer.database.global_db.image`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: ImagesTable = None
    _download_callbacks = {}

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'images': [self.db_id]
        }

        file_type_id = self.file_type_id
        if file_type_id is not None:
            packet['file_types'] = [file_type_id]

        return packet

    def download_complete(self):
        if self.db_id not in self._download_callbacks:
            return

        file_ = self.data_path
        if file_ is not None:
            pixmap_ = QtGui.QPixmap(file_)

            for ref_, _ in self._download_callbacks[self.db_id]:
                cb_ = ref_()
                if cb_ is None:
                    continue

                cb_(self, pixmap_)

            del self._download_callbacks[self.db_id]

    def set_progress(self, step):

        if self.db_id not in self._download_callbacks:
            return

        for _, ref_ in self._download_callbacks[self.db_id]:
            cb_ = ref_()
            if cb_ is None:
                continue

            cb_(self, step)

    def load(self, mfg, part_number, done_callback, progress_callback):
        """
        Load an image.

        This function schedules the loading to take place using a child process.
        The reason why this is done is for multi seat environments and not
        duplicating image downloads and also to provide a way to audit failed
        downloads so a system administrator can fix what is wrong.

        :param mfg: Manufacturer of the part.
        :type mfg: str

        :param part_number: Part number of part that uses this model.
        :type part_number: str

        :param done_callback: callback that takes :class:`Image` and
                         :class:`QtGui.QPixmap` instances as parameters.
        :type done_callback: callable

        :param progress_callback: callback that takes :class:`Image` and `int`
                                  as parameters.
        :type progress_callback: callable

        :returns: ``None``.
        :rtype: None
        """
        file = self.data_path

        if file is None:
            if (_resources.RESOURCE_TYPE_IMAGE, self.db_id) in self._table.db.resource_state_table:
                resource_state = self._table.db.resource_state_table[(_resources.RESOURCE_TYPE_IMAGE, self.db_id)]
            else:
                resource_state = self._table.db.resource_state_table.insert(_resources.RESOURCE_TYPE_IMAGE, self.db_id)

            if resource_state.allow_retry:
                if resource_state.progress == -1:
                    resource_state.progress = 0

                if self.db_id not in self._download_callbacks:
                    self._download_callbacks[self.db_id] = []

                self._download_callbacks[self.db_id].append((
                    weakref.WeakMethod(done_callback),
                    weakref.WeakMethod(progress_callback)))

                image_path = self._table.db.settings_table['image_path']

                self._table.db.mainframe.process_manager.get_image(
                    10, self, resource_state, mfg, part_number, image_path)
            else:
                progress_callback(self, -1)
        else:
            if self.db_id not in self._download_callbacks:
                self._download_callbacks[self.db_id] = []

            self._download_callbacks[self.db_id].append((
                weakref.WeakMethod(done_callback),
                weakref.WeakMethod(progress_callback)))
            self.set_progress(5)
            self.download_complete()

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

        image_path = self._table.db.settings_table['image_path']

        hex_path = file_id[:2]
        path = os.path.join(image_path, hex_path, f'{file_id}.png')

        if not os.path.exists(path):
            return None

        return path

    _stored_path: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def path(self) -> str:
        """Return the path.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_path is DefaultStoredValue:
            self._stored_path = self._table.select('path', id=self._db_id)[0][0]

        return self._stored_path

    _stored_uuid: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def uuid(self) -> str | None:
        """Return the uuid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        if self._stored_uuid is DefaultStoredValue:
            self._stored_uuid = self._table.select('uuid', id=self._db_id)[0][0]

        return self._stored_uuid

    _stored_file_type: "DefaultStoredValueType | _file_types.FileType | None" = DefaultStoredValue

    @property
    def file_type(self) -> "_file_types.FileType":
        """Return the file type.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_file_types.FileType`
        """
        if self._stored_file_type is DefaultStoredValue:
            db_id = self.file_type_id
            if db_id is None:
                self._stored_file_type = None
            else:
                self._stored_file_type = self._table.db.file_types_table[db_id]

        return self._stored_file_type

    _stored_file_type_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def file_type_id(self) -> int | None:
        """Return the file type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        if self._stored_file_type_id is DefaultStoredValue:
            self._stored_file_type_id = self._table.select('file_type_id', id=self._db_id)[0][0]

        return self._stored_file_type_id

    @file_type_id.setter
    def file_type_id(self, value: int):
        """Set the file type ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_file_type_id = value
        self._stored_file_type = DefaultStoredValue

        self._table.update(self._db_id, file_type_id=value)
        self._populate('file_type_id')
