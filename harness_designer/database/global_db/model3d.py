# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import weakref
from typing import Iterable as _Iterable, TYPE_CHECKING

import os
import uuid
import numpy as np

from ..create_database import models3d as _models3d
from ...geometry import angle as _angle
from ...geometry import point as _point
from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from ... import resources as _resources

if TYPE_CHECKING:
    from . import file_types as _file_types


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

    _download_callbacks = {}

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

        hex_path = file_id[:2]

        path = os.path.join(model_path, hex_path, f'{file_id}.npy')

        if not os.path.exists(path):
            file_type = self.file_type
            path = os.path.join(model_path, hex_path, f'{file_id}.{file_type.extension}')

            if os.path.exists(path):
                self._table.update(self._db_id, path=path)

            return None

        return path

    _stored_path: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def path(self) -> str:
        """
        Return the path.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """

        if self._stored_path is DefaultStoredValue:
            self._stored_path = self._table.select('path', id=self._db_id)[0][0]

        return self._stored_path

    _stored_uuid: str | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def uuid(self) -> str | None:
        """
        Return the uuid.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """

        if self._stored_uuid is DefaultStoredValue:
            self._stored_uuid = self._table.select('uuid', id=self._db_id)[0][0]

        return self._stored_uuid

    _stored_vertex_count: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def vertex_count(self) -> int | None:
        """
        Return the cached mesh vertex count (triangle-soup vertices).

        :returns: Property value or ``None`` when the model has not been
                  converted yet.
        :rtype: int | None
        """

        if self._stored_vertex_count is DefaultStoredValue:
            self._stored_vertex_count = self._table.select('vertex_count', id=self._db_id)[0][0]

        return self._stored_vertex_count

    @vertex_count.setter
    def vertex_count(self, value: int):
        """
        Set the cached mesh vertex count.

        :param value: Value to store or process.
        :type value: int
        """

        self._stored_vertex_count = value
        self._table.update(self._db_id, vertex_count=value)

    _stored_aabb: list[
        list[float, float, float],
        list[float, float, float]] | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def aabb(self) -> np.ndarray | None:
        """
        Return the cached mesh axis-aligned bounding box.

        Calculated once when the model is converted and stored in the
        database. The cache holds plain lists of floats; a new numpy array
        is constructed on every access so callers that transform the array
        in place can never reach the cache.

        :returns: (2, 3) float32 array (min, max) or ``None`` when the
                  model has not been converted yet.
        :rtype: numpy.ndarray | None
        """

        if self._stored_aabb is DefaultStoredValue:
            value = self._table.select('aabb', id=self._db_id)[0][0]

            if value is None:
                self._stored_aabb = None
            else:
                self._stored_aabb = eval(value)

        if self._stored_aabb is None:
            return None

        return np.asarray(self._stored_aabb, dtype=np.float32)

    @aabb.setter
    def aabb(self, value):
        """
        Set the cached mesh axis-aligned bounding box.

        :param value: (2, 3) array-like of floats.
        :type value: numpy.ndarray | list
        """

        value = [[float(str(item)) for item in row] for row in np.asarray(value).tolist()]

        self._stored_aabb = value
        self._table.update(self._db_id, aabb=str(value))

    _stored_obb: list[
        list[float, float, float],
        list[float, float, float],
        list[float, float, float],
        list[float, float, float],
        list[float, float, float],
        list[float, float, float],
        list[float, float, float],
        list[float, float, float]] | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def obb(self) -> np.ndarray | None:
        """
        Return the cached mesh bounding-box corner coordinates.

        Calculated once when the model is converted and stored in the
        database. The cache holds plain lists of floats; a new numpy array
        is constructed on every access so callers that transform the array
        in place can never reach the cache.

        :returns: (8, 3) float32 array or ``None`` when the model has not
                  been converted yet.
        :rtype: numpy.ndarray | None
        """

        if self._stored_obb is DefaultStoredValue:
            value = self._table.select('obb', id=self._db_id)[0][0]

            if value is None:
                self._stored_obb = None
            else:
                self._stored_obb = eval(value)

        if self._stored_obb is None:
            return None

        return np.asarray(self._stored_obb, dtype=np.float32)

    @obb.setter
    def obb(self, value):
        """
        Set the cached mesh bounding-box corner coordinates.

        :param value: (8, 3) array-like of floats.
        :type value: numpy.ndarray | list
        """

        value = [[float(str(item)) for item in row] for row in np.asarray(value).tolist()]

        self._stored_obb = value
        self._stored_size = DefaultStoredValue
        self._table.update(self._db_id, obb=str(value))

    _stored_file_type: "DefaultStoredValueType | _file_types.FileType | None" = DefaultStoredValue

    @property
    def file_type(self) -> "_file_types.FileType":
        """
        Return the file type.

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
        """
        Return the file type ID.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """

        if self._stored_file_type_id is DefaultStoredValue:
            self._stored_file_type_id = self._table.select('file_type_id', id=self._db_id)[0][0]

        return self._stored_file_type_id

    @file_type_id.setter
    def file_type_id(self, value: int):
        """
        Set the file type ID.

        :param value: Value to store or process.
        :type value: int
        """

        self._stored_file_type_id = value
        self._stored_file_type = DefaultStoredValue

        self._table.update(self._db_id, file_type_id=value)

    def __update_angle3d(self, angle: _angle.Angle):
        """
        Update the angle 3D.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._stored_size = DefaultStoredValue

        self._table.update(self._db_id, angle3d=euler)
        self._table.update(self._db_id, quat3d=quat)

    _stored_angle3d: tuple[
        list[float, float, float, float],
        list[float, float, float]] | DefaultStoredValueType = DefaultStoredValue

    @property
    def angle3d(self) -> _angle.Angle:
        """
        Return the angle 3D.

        The cache holds plain lists of floats (quat, euler) and is never
        ``None`` - NULL columns mean the identity rotation. A new
        :class:`_angle.Angle` is constructed on every access.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """

        if self._stored_angle3d is DefaultStoredValue:

            if self._angle3d_id is None:
                self._angle3d_id = str(uuid.uuid4())

            quat = self._table.select('quat3d', id=self._db_id)[0][0]
            euler_angle = self._table.select('angle3d', id=self._db_id)[0][0]

            if quat is None or euler_angle is None:
                self._stored_angle3d = ([1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
            else:
                self._stored_angle3d = (eval(quat), eval(euler_angle))

        quat, euler_angle = self._stored_angle3d
        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_id)
        angle.bind(self.__update_angle3d)

        return angle

    @angle3d.setter
    def angle3d(self, value: list[float, float, float] | None):
        if value is None:
            quat = None
            euler = None
        else:
            angle = _angle.Angle.from_euler(*value)
            quat = str(list(angle.as_quat_float))
            euler = str(value)

            if 'nan' in euler.lower() or 'nan' in quat.lower():
                return

        self._stored_angle3d = DefaultStoredValue
        self._stored_size = DefaultStoredValue

        self._table.update(self._db_id, angle3d=euler)
        self._table.update(self._db_id, quat3d=quat)

    def __update_position3d(self, offset: _point.Point):
        """
        Update the position 3D.

        :param offset: Value for ``offset``.
        :type offset: :class:`_point.Point`
        """

        self._table.update(self._db_id, point3d=str(list(offset.as_float)))

    _stored_position3d: list[float, float, float] | DefaultStoredValueType = DefaultStoredValue

    @property
    def position3d(self) -> _point.Point:
        """
        Return the position 3D.

        The cache holds a plain list of floats and is never ``None`` - a
        NULL column means the world origin. A new :class:`_point.Point` is
        constructed on every access (PointMeta returns the shared live
        instance for ``db_id`` when one exists, and ``bind`` tolerates
        duplicate registrations).

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_position3d is DefaultStoredValue:

            if self._position3d_id is None:
                self._position3d_id = str(uuid.uuid4())

            value = self._table.select('point3d', id=self._db_id)[0][0]

            if value is None:
                self._stored_position3d = [0.0, 0.0, 0.0]
            else:
                self._stored_position3d = eval(value)

        x, y, z = self._stored_position3d
        position = _point.Point(x, y, z, db_id=self._position3d_id)
        position.bind(self.__update_position3d)

        return position

    @position3d.setter
    def position3d(self, value: list[float, float, float] | None):
        real_value: str | None = None

        if value is not None:
            real_value = str(value)

        self._stored_position3d = DefaultStoredValue

        self._table.update(self._db_id, point3d=real_value)

    def __update_scale(self, scale: _point.Point):
        """
        Update the scale.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """

        self._table.update(self._db_id, scale=str(list(scale.as_float)))

    _stored_scale3d: _point.Point | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def scale(self) -> _point.Point:
        """
        Return the scale.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_scale3d is DefaultStoredValue:
            value = self._table.select('scale', id=self._db_id)[0][0]

            if value is None:
                self._stored_scale3d = None
            else:
                x, y, z = eval(value)
                scale = _point.Point(x, y, z)
                scale.bind(self.__update_scale)
                self._stored_scale3d = scale

        return self._stored_scale3d

    @scale.setter
    def scale(self, value: list[float, float, float] | None):
        real_value: str | None = None

        if value is not None:
            real_value = str(value)

        self._stored_scale3d = DefaultStoredValue

        self._table.update(self._db_id, scale=real_value)

    _stored_forward_up: list[int, int] | DefaultStoredValueType = DefaultStoredValue

    @property
    def forward_up(self) -> list[int, int]:
        """
        Return the forward and up side indexes.

        :returns: Property value. UNKNOWN details.
        :rtype: list[int, int]
        """
        if self._stored_forward_up is DefaultStoredValue:
            value = self._table.select('forward_up', id=self._db_id)[0][0]
            self._stored_forward_up = eval(f'[{value}]')

        return list(self._stored_forward_up)

    @forward_up.setter
    def forward_up(self, value: list[int, int]):
        """
        Set the forward and up side indexes.

        :param value: Value to store or process.
        :type value: list[int, int]
        """
        self._stored_forward_up = value
        value = str(value)[1:-1]
        self._table.update(self._db_id, forward_up=value)

    _stored_target_count: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def target_count(self) -> int:
        """
        Return the target count.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        if self._stored_target_count is DefaultStoredValue:
            self._stored_target_count = self._table.select('target_count', id=self._db_id)[0][0]

        return self._stored_target_count

    @target_count.setter
    def target_count(self, value: int):
        """
        Set the target count.

        :param value: Value to store or process.
        :type value: int
        """

        self._stored_target_count = value
        self._table.update(self._db_id, target_count=value)

    _stored_aggressiveness: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def aggressiveness(self) -> float:
        """
        Return the aggressiveness.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """

        if self._stored_aggressiveness is DefaultStoredValue:
            self._stored_aggressiveness = float(self._table.select('aggressiveness', id=self._db_id)[0][0])

        return self._stored_aggressiveness

    @aggressiveness.setter
    def aggressiveness(self, value: float):
        """
        Set the aggressiveness.

        :param value: Value to store or process.
        :type value: float
        """

        self._stored_aggressiveness = value
        self._table.update(self._db_id, aggressiveness=value)

    _stored_update_rate: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def update_rate(self) -> int:
        """
        Return the update rate.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        if self._stored_update_rate is DefaultStoredValue:
            self._stored_update_rate = self._table.select('update_rate', id=self._db_id)[0][0]

        return self._stored_update_rate

    @update_rate.setter
    def update_rate(self, value: int):
        """
        Set the update rate.

        :param value: Value to store or process.
        :type value: int
        """

        self._stored_update_rate = value
        self._table.update(self._db_id, update_rate=value)

    _stored_simplify: bool | DefaultStoredValueType = DefaultStoredValue

    @property
    def simplify(self) -> bool:
        """
        Return the simplify.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """

        if self._stored_simplify is DefaultStoredValue:
            self._stored_simplify = bool(self._table.select('simplify', id=self._db_id)[0][0])

        return self._stored_simplify

    @simplify.setter
    def simplify(self, value: bool):
        """
        Set the simplify.

        :param value: Value to store or process.
        :type value: bool
        """

        self._stored_simplify = value
        self._table.update(self._db_id, simplify=int(value))

    _stored_iterations: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def iterations(self) -> int:
        """
        Return the iterations.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        if self._stored_iterations is DefaultStoredValue:
            self._stored_iterations = self._table.select('iterations', id=self._db_id)[0][0]

        return self._stored_iterations

    @iterations.setter
    def iterations(self, value: int):
        """
        Set the iterations.

        :param value: Value to store or process.
        :type value: int
        """

        self._stored_iterations = value
        self._table.update(self._db_id, iterations=value)

    _stored_size: tuple[float, float, float] | DefaultStoredValueType = DefaultStoredValue

    @property
    def size(self) -> tuple[float, float, float]:
        """
        Collects the length, width and height of a model from the obb after
        applying a user set rotation to the obb
        """
        if self._stored_size is DefaultStoredValue:

            obb = self.obb
            angle = self.angle3d

            if obb is None:
                return 0, 0, 0

            obb @= angle

            width = float(str(np.linalg.norm(obb[1] - obb[0])))  # X axis
            height = float(str(np.linalg.norm(obb[3] - obb[0])))  # Y axis
            length = float(str(np.linalg.norm(obb[4] - obb[0])))  # Z axis

            self._stored_size = (width, height, length)

        return self._stored_size

    def download_complete(self):
        if self.db_id not in self._download_callbacks:
            return

        file = self.data_path
        if file is not None:
            # The packed geometry is opened as a memory mapped array and
            # handed to the callback as-is; the VBO streams it straight
            # from the mapping into the GPU vertex buffer.

            # angle3d the property never returns None anymore (NULL means
            # identity), so "never oriented" has to be read from the raw
            # column - it is what gates the one-time orientation dialog.
            if self._table.select('angle3d', id=self._db_id)[0][0] is None:
                from ...ui.dialogs import part_orientation as _part_orientation
                from ... import app as _app

                self.angle3d = [0.0, 0.0, 0.0]
                self.position3d = [0.0, 0.0, 0.0]

                dlg = _part_orientation.PartOrientationDialog(self._table.db.mainframe)
                _app.CallAfter(dlg.SetValue, self)
                dlg.exec()

            for ref in self._download_callbacks[self.db_id]:
                cb = ref()

                if cb is None:
                    continue

                cb(self)

            del self._download_callbacks[self.db_id]

    def load(self, mfg, part_number, callback) -> None:
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

        :param callback: callback that takes the :class:`Model3D` instance
                         and the memory mapped packed geometry array
                         (:class:`numpy.memmap`) as parameters.
        :type callback: callable

        :returns: ``None``.
        :rtype: None
        """

        file = self.data_path

        if file is None:
            if (_resources.RESOURCE_TYPE_MODEL, self.db_id) in self._table.db.resource_state_table:
                resource_state = self._table.db.resource_state_table[(_resources.RESOURCE_TYPE_MODEL, self.db_id)]
            else:
                resource_state = self._table.db.resource_state_table.insert(_resources.RESOURCE_TYPE_MODEL, self.db_id)

            if resource_state.allow_retry:
                if resource_state.progress == -1:
                    resource_state.progress = 0

                if self.db_id not in self._download_callbacks:
                    self._download_callbacks[self.db_id] = []

                self._download_callbacks[self.db_id].append(weakref.WeakMethod(callback))

                model_dir = self._table.db.settings_table['model_path']

                self._table.db.mainframe.process_manager.get_model(
                    self, resource_state, mfg, part_number, model_dir)
        else:
            if self.db_id not in self._download_callbacks:
                self._download_callbacks[self.db_id] = []

            self._download_callbacks[self.db_id].append(weakref.WeakMethod(callback))
            self.download_complete()
