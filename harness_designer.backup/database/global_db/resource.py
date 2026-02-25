from typing import Iterable as _Iterable
import requests
import zipfile
import io

from . import EntryBase, TableBase


class ResourcesTable(TableBase):
    __table_name__ = 'resources'

    def __iter__(self) -> _Iterable["Resource"]:
        for db_id in TableBase.__iter__(self):
            yield Resource(self, db_id)

    def __getitem__(self, item) -> "Resource":
        if isinstance(item, int):
            if item in self:
                return Resource(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str, data: bytes | None, type: str) -> "Resource":  # NOQA
        db_id = TableBase.insert(self, path=path, data=data)
        return Resource(self, db_id)


class Resource(EntryBase):
    _table: ResourcesTable = None

    @property
    def http(self) -> str | None:
        path = self._table.select('path', id=self._db_id)[0][0]
        if path is None or not path.startswith('http'):
            return None

        return path

    @http.setter
    def http(self, value: str | None):
        path = self._table.select('path', id=self._db_id)[0][0]
        if value is None:
            if path is None or path.startswith('http'):
                self._table.update(self._db_id, path=value)
                self.data = None
                self.type = ''
        elif value.startswith('http'):
            self._table.update(self._db_id, path=value)
            self.data = None
            self.type = ''

    @property
    def path(self) -> str | None:
        path = self._table.select('path', id=self._db_id)[0][0]

        if path is None or path.startswith('http'):
            return None

        return path

    @path.setter
    def path(self, value:  str | None):
        if value is not None and not value.startswith('http'):
            self._table.update(self._db_id, path=value)
            self.data = None
            self.type = ''
        elif value is None:
            self._table.update(self._db_id, path=value)
            self.type = ''

    @property
    def data(self) -> bytes | None:
        data = self._table.select('data', id=self._db_id)[0][0]

        if data is None:
            http = self.http
            if http is not None:
                response = requests.get(http)
                data = response.content
                file_type = self.type

                content_type_mapping = {
                    'application/x-bzip2': 'bz2',
                    'application/x-7z-compressed': '7z',
                    'application/pdf': 'pdf',
                    'image/vnd.dxf': 'dxf',
                    'model/vnd.dwf': 'dwf',
                    'image/bmp': 'bmp',
                    'model/vnd.collada+xml': 'dae',
                    'image/vnd.dwg': 'dwg',
                    'application/x-gtar': 'gtar',
                    'image/gif': 'gif',
                    'application/gzip': 'gz',
                    'image/jpeg': 'jpg',
                    'model/mesh': 'msh',
                    'image/png': 'png',
                    'image/x-png': 'png',
                    'image/svg+xml': 'svg',
                    'application/x-tar': 'tar',
                    'image/webp': 'webp',
                    'application/zip': 'zip',
                    'image/tiff': 'tiff',
                }

                content_type = response.headers.get('Content-Type', None)
                if content_type is not None:
                    content_type = content_type_mapping.get(content_type.split(';')[0], None)

                    if file_type is None:
                        file_type = self.type = content_type

                if content_type == 'zip':
                    data = io.BytesIO(data)
                    data.seek(0)
                    zf = zipfile.ZipFile(data)
                    files = {name: zf.read(name) for name in zf.namelist()}
                    zf.close()
                    data.close()
                    types = list(content_type_mapping.values())
                    for fn, data in files.items():
                        if file_type is None:
                            ext = fn.rsplit('.', 1)[-1]
                            if ext in types:
                                self.type = ext
                                return data

                        elif fn.endswith(file_type):
                            return data

                    return None

                elif file_type is not None:
                    if file_type == self.type:
                        return data

                return data

            path = self.path

            if path is not None:
                return open(path, 'rb').read()

        return data

    @data.setter
    def data(self, value: bytes | None):
        path = self.path

        if path is not None and value is not None:
            with open(path, 'wb') as f:
                f.write(value)
        else:
            self._table.update(self._db_id, data=value)

    @property
    def type(self) -> str:
        return self._table.select('type', id=self._db_id)[0][0]

    @type.setter
    def type(self, value: str):
        self._table.update(self._db_id, type=value)
