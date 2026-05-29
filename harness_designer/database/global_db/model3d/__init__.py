# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import weakref
from typing import Iterable as _Iterable, TYPE_CHECKING

import os
import uuid

from ...create_database import models3d as _models3d
from ....geometry import angle as _angle
from ....geometry import point as _point
from .... import model_data as _model_data
from ..bases import EntryBase, TableBase


if TYPE_CHECKING:
    from .. import file_types as _file_types


class Models3DTable(TableBase):
    """
    Represent a models 3dtable in :mod:`harness_designer.database.global_db.model3d.__init__`.
    """

    __table_name__ = 'models3d'

    def _table_needs_update(self) -> bool:
        """
        Execute the table needs update operation.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """

        return _models3d.table.is_ok(self)

    def _add_table_to_db(self, _):
        """
        Add a table to database.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """

        _models3d.table.add_to_db(self)

    def _update_table_in_db(self):
        """
        Update the table in database.
        """

        _models3d.table.update_fields(self)

    def __iter__(self) -> _Iterable["Model3D"]:
        """
        Iterate over the available items.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Model3D']
        """

        for db_id in TableBase.__iter__(self):
            yield Model3D(self, db_id)

    def __getitem__(self, item) -> "Model3D":
        """
        Return the requested item.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Model3D`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """

        if isinstance(item, int):
            if item in self:
                return Model3D(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, path: str) -> "Model3D":  # NOQA
        """
        Execute the insert operation.

        :param path: Filesystem path.
        :type path: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Model3D`
        """

        self._con.execute(f'SELECT id FROM models3d WHERE path="{path}";')
        rows = self._con.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_id = _models3d.get_model3d_id(self._con, path)
            if db_id is None:
                return None

        return Model3D(self, db_id)


class Model3D(EntryBase):
    """
    Represent a model 3D in :mod:`harness_designer.database.global_db.model3d.__init__`.
    """

    _table: Models3DTable = None
    _angle3d_id: str = None
    _position3d_id: str = None

    def build_monitor_packet(self):
        """
        Build the monitor packet.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        packet = {
            'models3d': [self.db_id]
        }

        file_type_id = self.file_type_id
        if file_type_id is not None:
            packet['file_types'] = [file_type_id]

        return packet

    @property
    def data_path(self) -> str | None:
        """
        Return the data path.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """

        file_id = self.uuid

        if file_id is None:
            return None

        model_path = self._table.db.settings_table['model_path']
        path = os.path.join(model_path, f'{file_id}.hdz')

        if not os.path.exists(path):
            file_type = self.file_type
            path = os.path.join(model_path, f'{file_id}.{file_type.extension}')

            if os.path.exists(path):
                self._table.update(self._db_id, path=path)

            return None

        return path

    @property
    def path(self) -> str:
        """
        Return the path.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """

        path = self._table.select('path', id=self._db_id)[0][0]
        return path

    @property
    def uuid(self) -> str | None:
        """
        Return the uuid.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """

        return self._table.select('uuid', id=self._db_id)[0][0]

    @property
    def file_type(self) -> "_file_types.FileType":
        """
        Return the file type.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_file_types.FileType`
        """
        db_id = self.file_type_id
        if db_id is None:
            return None

        return self._table.db.file_types_table[db_id]

    @property
    def file_type_id(self) -> int | None:
        """
        Return the file type ID.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """

        return self._table.select('file_type_id', id=self._db_id)[0][0]

    @file_type_id.setter
    def file_type_id(self, value: int):
        """
        Set the file type ID.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, file_type_id=value)

    def __update_angle3d(self, angle: _angle.Angle):
        """
        Update the angle 3D.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        quat = list(angle.as_quat_float)
        euler = list(angle.as_euler_float)

        self._table.update(self._db_id, angle3d=str(euler))
        self._table.update(self._db_id, quat3d=str(quat))

    @property
    def angle3d(self) -> _angle.Angle:
        """
        Return the angle 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """

        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_id)
        angle.bind(self.__update_angle3d)
        return angle

    def __update_position3d(self, offset: _point.Point):
        """
        Update the position 3D.

        :param offset: Value for ``offset``.
        :type offset: :class:`_point.Point`
        """

        self._table.update(self._db_id, offset=str(list(offset.as_float)))

    @property
    def position3d(self) -> _point.Point:
        """
        Return the position 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._position3d_id is None:
            self._position3d_id = str(uuid.uuid4())

        value = eval(self._table.select('point3d', id=self._db_id)[0][0])
        x, y, z = value
        position = _point.Point(x, y, z, db_id=self._position3d_id)
        position.bind(self.__update_position3d)
        return position

    def __update_scale(self, scale: _point.Point):
        """
        Update the scale.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """

        self._table.update(self._db_id, scale=str(list(scale.as_float)))

    @property
    def scale(self) -> _point.Point:
        """
        Return the scale.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        value = eval(self._table.select('scale', id=self._db_id)[0][0])

        x, y, z = value
        scale = _point.Point(x, y, z)
        scale.bind(self.__update_scale)
        return scale

    @property
    def target_count(self) -> int:
        """
        Return the target count.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        return self._table.select('target_count', id=self._db_id)[0][0]

    @target_count.setter
    def target_count(self, value: int):
        """
        Set the target count.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, target_count=value)

    @property
    def aggressiveness(self) -> float:
        """
        Return the aggressiveness.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """

        return float(self._table.select('aggressiveness', id=self._db_id)[0][0])

    @aggressiveness.setter
    def aggressiveness(self, value: float):
        """
        Set the aggressiveness.

        :param value: Value to store or process.
        :type value: float
        """

        self._table.update(self._db_id, aggressiveness=value)

    @property
    def update_rate(self) -> int:
        """
        Return the update rate.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        return self._table.select('update_rate', id=self._db_id)[0][0]

    @update_rate.setter
    def update_rate(self, value: int):
        """
        Set the update rate.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, update_rate=value)

    @property
    def simplify(self) -> bool:
        """
        Return the simplify.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """

        return bool(self._table.select('simplify', id=self._db_id)[0][0])

    @simplify.setter
    def simplify(self, value: bool):
        """
        Set the simplify.

        :param value: Value to store or process.
        :type value: bool
        """

        self._table.update(self._db_id, simplify=int(value))

    @property
    def iterations(self) -> int:
        """
        Return the iterations.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        return self._table.select('iterations', id=self._db_id)[0][0]

    @iterations.setter
    def iterations(self, value: int):
        """
        Set the iterations.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, iterations=value)

    def load(self, mfg, part_number, callback) -> _model_data.ModelData:
        """
        Load a 3d model.

        This function schedules the loading to take place using a child process.
        The reason why this is done is because a model can be quite large in size
        and they come in many different formats. The subprocess loads the model
        and then converts it into a format that streamlines the loading process
        from then on. This only occurs a single time per model. The use of the
        child process to do this is to keep the UI free and it allows the user
        to continue working on other things while the model is being loaded and
        converted instead of having to sit there and wait. The new format of the
        data can be larger than the original but not always. The new format
        packages both the smooth normals as well as face normals with it and
        both of these get uploaded to the GPU. This allows for realtime quick
        changing of smooth shading and and this is now able to be done on a
        per object basis. I have found that some models regardless of type will
        look better with smooth shading while others will not and this is not
        specific to a type. It's mostly about user preferance.

        :param mfg: Manufacturer of the part.
        :type mfg: str

        :param part_number: Part number of part that uses this model.
        :type part_number: str

        :param callback: callback that takes :class:`Model3D` and
                         :class:`_model_data.ModelData` instances as parameters.
        :type callback: callable

        :returns: ``None``.
        :rtype: None
        """

        file = self.data_path

        if file is None:
            model_dir = self._table.db.settings_table['model_path']

            self._table.db.mainframe.process_manager.get_model(
                callback, id=self.db_id, mfg=mfg,
                part_number=part_number, model_dir=model_dir)
        else:
            md = _model_data.ModelData(file)

            callback(self, md)
