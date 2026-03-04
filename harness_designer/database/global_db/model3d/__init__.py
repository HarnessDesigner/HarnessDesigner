from typing import Iterable as _Iterable

import numpy as np
import os
import uuid
import wx

from ..bases import EntryBase, TableBase
from ....geometry import angle as _angle
from ....geometry import point as _point
from . import loader as _loader
from . import positioning as _positioning


class Models3DTable(TableBase):
    __table_name__ = 'models3d'

    def __iter__(self) -> _Iterable["Model3D"]:

        for db_id in TableBase.__iter__(self):
            yield Model3D(self, db_id)

    def __getitem__(self, item) -> "Model3D":
        if isinstance(item, int):
            if item in self:
                return Model3D(self, item)
            raise IndexError(str(item))
        raise KeyError(item)

    def insert(self, url: str) -> "Model3D":
        db_id = TableBase.insert(self, uuid=str(uuid.uuid4()), url=url)

        return Model3D(self, db_id)


class Model3D(EntryBase):
    _table: Models3DTable = None
    _angle3d_id: str = None
    _position3d_id: str = None

    @property
    def uuid(self) -> str:
        return self._table.select('uuid', id=self._db_id)[0][0]

    @uuid.setter
    def uuid(self, value: str):
        self._table.update(self._db_id, uuid=value)

    @property
    def url(self) -> str:
        return self._table.select('url', id=self._db_id)[0][0]

    @url.setter
    def url(self, value: str):
        self._table.update(self._db_id, url=value)

    @property
    def file(self) -> str:
        model_path = self._table.db.settings_table['model_path']

        if self.type_id == 0:
            file_exists = False
        else:
            file = os.path.join(model_path, self.uuid + self.extension)
            file_exists = os.path.exists(file)

        if not file_exists:
            self._table.execute('SELECT extension FROM model_types;')
            extensions = ['.' + row[0] for row in self._table.fetchall()]
            url = self.url

            if url:
                from . import model_download as _model_download
                import wx

                try:
                    dialog = _model_download.ModelDownloadDialog(self._table.db.mainframe, url, extensions)

                    if dialog.ShowModal() == wx.OK:
                        data, extension = dialog.GetValues()
                    else:
                        data = None
                        extension = None

                    dialog.Destroy()

                    if extension is not None and data is not None:
                        self._table.execute(f'SELECT id FROM model_types WHERE extension="{extension[1:]}";')
                        type_id = self._table.fetchall()[0][0]
                        filename = self.uuid + extension
                        file = os.path.join(model_path, filename)

                        with open(file, 'wb') as f:
                            f.write(data)

                        file_exists = True
                        self.type_id = type_id

                except ValueError:
                    pass

        if file_exists:
            return os.path.join(model_path, self.uuid + self.extension)

        return None

    def __update_angle3d(self, angle: _angle.Angle):
        quat = [float(item) for item in angle.as_quat]
        euler = [angle.x, angle.y, angle.z]

        self._table.update(self._db_id, angle3d=str(euler))
        self._table.update(self._db_id, quat3d=str(quat))

    @property
    def angle3d(self) -> _angle.Angle:
        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_id)
        angle.bind(self.__update_angle3d)
        return angle

    def __update_position3d(self, offset: _point.Point):
        self._table.update(self._db_id, offset=str(list(offset.as_float)))

    @property
    def point3d(self) -> _point.Point:
        if self._position3d_id is None:
            self._position3d_id = str(uuid.uuid4())

        value = eval(self._table.select('point3d', id=self._db_id)[0][0])
        x, y, z = value
        position = _point.Point(x, y, z, db_id=self._position3d_id)
        position.bind(self.__update_position3d)
        return position

    def __update_scale(self, scale: _point.Point):
        self._table.update(self._db_id, scale=str(list(scale.as_float)))

    @property
    def scale(self) -> _point.Point:
        value = eval(self._table.select('scale', id=self._db_id)[0][0])

        x, y, z = value
        scale = _point.Point(x, y, z)
        scale.bind(self.__update_scale)
        return scale

    @property
    def extension(self) -> str:
        type_id = self.type_id

        self._table.execute(f'SELECT extension FROM model_types WHERE id={type_id};')
        res = self._table.fetchall()[0][0]
        return '.' + res

    @property
    def type_id(self) -> str:
        return self._table.select('type_id', id=self._db_id)[0][0]

    @type_id.setter
    def type_id(self, value: str):
        self._table.update(self._db_id, type_id=value)

    @property
    def target_count(self) -> int:
        return self._table.select('target_count', id=self._db_id)[0][0]

    @target_count.setter
    def target_count(self, value: int):
        self._table.update(self._db_id, target_count=value)

    @property
    def aggressiveness(self) -> float:
        return float(self._table.select('aggressiveness', id=self._db_id)[0][0])

    @aggressiveness.setter
    def aggressiveness(self, value: float):
        self._table.update(self._db_id, aggressiveness=value)

    @property
    def update_rate(self) -> int:
        return self._table.select('update_rate', id=self._db_id)[0][0]

    @update_rate.setter
    def update_rate(self, value: int):
        self._table.update(self._db_id, update_rate=value)

    @property
    def simplify(self) -> bool:
        return bool(self._table.select('simplify', id=self._db_id)[0][0])

    @simplify.setter
    def simplify(self, value: bool):
        self._table.update(self._db_id, simplify=int(value))

    @property
    def iterations(self) -> int:
        return self._table.select('iterations', id=self._db_id)[0][0]

    @iterations.setter
    def iterations(self, value: int):
        self._table.update(self._db_id, iterations=value)

    @property
    def path(self) -> str:
        return self._table.select('path', id=self._db_id)[0][0]

    @path.setter
    def path(self, value: str):
        self._table.update(self._db_id, path=value)

    def modify_model(self):
        file = self.file
        if file is None:
            return

        try:
            vertices, faces = _loader.load(file)
        except _loader.ModelLoadError:
            return

        dialog = _positioning.PositioningDialog(self._table.db.mainframe, vertices, faces, self)

        if dialog.ShowModal() == wx.OK:
            (
                simplify,
                target_count,
                aggressiveness,
                update_rate,
                iterations,
                position,
                angle,
                scale
            ) = dialog.GetValues()

            if simplify:
                self.target_count = target_count
                self.aggressiveness = aggressiveness
                self.update_rate = update_rate
                self.iterations = iterations

            p = self.point3d
            with p:
                p.x = position.x
                p.y = position.y
            p.z = position.z

            s = self.scale
            with s:
                s.x = scale.x
                s.y = scale.y
            s.z = scale.z

            a = self.angle3d
            with a:
                a.x = angle.x
                a.y = angle.y

            a.z = angle.z

        dialog.Destroy()

    def load(self):
        file = self.file
        if file is None:
            return None

        try:
            vertices, faces = _loader.load(file)
        except _loader.ModelLoadError:
            return None

        if self.simplify:
            target_count = self.target_count
            aggressiveness = self.aggressiveness
            update_rate = self.update_rate
            iterations = self.iterations
            vertices, faces = _loader.reduce_triangles(vertices, faces, target_count, aggressiveness, update_rate, iterations)

        scale = self.scale
        angle = self.angle3d
        position = self.point3d

        vertices *= scale
        vertices @= angle
        vertices += position

        return vertices, faces
