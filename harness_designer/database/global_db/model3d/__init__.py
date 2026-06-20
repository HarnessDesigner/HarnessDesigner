# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import weakref
from typing import Iterable as _Iterable, TYPE_CHECKING

import os
import uuid
import numpy as np

from ...create_database import models3d as _models3d
from ....geometry import angle as _angle
from ....geometry import point as _point
from ..bases import EntryBase, TableBase
from .... import resources as _resources

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
    def vertex_count(self) -> int | None:
        """
        Return the cached mesh vertex count (triangle-soup vertices).

        :returns: Property value or ``None`` when the model has not been
                  converted yet.
        :rtype: int | None
        """

        return self._table.select('vertex_count', id=self._db_id)[0][0]

    @vertex_count.setter
    def vertex_count(self, value: int):
        """
        Set the cached mesh vertex count.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, vertex_count=value)

    @property
    def aabb(self) -> np.ndarray | None:
        """
        Return the cached mesh axis-aligned bounding box.

        Calculated once when the model is converted and stored in the
        database.

        :returns: (2, 3) float32 array (min, max) or ``None`` when the
                  model has not been converted yet.
        :rtype: numpy.ndarray | None
        """

        value = self._table.select('aabb', id=self._db_id)[0][0]
        if not value:
            return None

        return np.asarray(eval(value), dtype=np.float32)

    @aabb.setter
    def aabb(self, value):
        """
        Set the cached mesh axis-aligned bounding box.

        :param value: (2, 3) array-like of floats.
        :type value: numpy.ndarray | list
        """

        self._table.update(self._db_id, aabb=str([[float(str(item)) for item in row] for row in np.asarray(value).tolist()]))

    @property
    def obb(self) -> np.ndarray | None:
        """
        Return the cached mesh bounding-box corner coordinates.

        Calculated once when the model is converted and stored in the
        database.

        :returns: (8, 3) float32 array or ``None`` when the model has not
                  been converted yet.
        :rtype: numpy.ndarray | None
        """

        value = self._table.select('obb', id=self._db_id)[0][0]
        if not value:
            return None

        return np.asarray(eval(value), dtype=np.float32)

    @obb.setter
    def obb(self, value):
        """
        Set the cached mesh bounding-box corner coordinates.

        :param value: (8, 3) array-like of floats.
        :type value: numpy.ndarray | list
        """

        self._table.update(self._db_id, obb=str([[float(str(item)) for item in row] for row in np.asarray(value).tolist()]))

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

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, angle3d=euler)
        self._table.update(self._db_id, quat3d=quat)

    @property
    def angle3d(self) -> _angle.Angle:
        """
        Return the angle 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """

        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        quat = self._table.select('quat3d', id=self._db_id)[0][0]
        euler_angle = self._table.select('angle3d', id=self._db_id)[0][0]

        if quat is None or euler_angle is None:
            return None

        angle = _angle.Angle.from_quat(eval(quat), eval(euler_angle), db_id=self._angle3d_id)
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

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, angle3d=euler)
        self._table.update(self._db_id, quat3d=quat)

    def __update_position3d(self, offset: _point.Point):
        """
        Update the position 3D.

        :param offset: Value for ``offset``.
        :type offset: :class:`_point.Point`
        """

        self._table.update(self._db_id, point3d=str(list(offset.as_float)))

    @property
    def position3d(self) -> _point.Point:
        """
        Return the position 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._position3d_id is None:
            self._position3d_id = str(uuid.uuid4())

        value = self._table.select('point3d', id=self._db_id)[0][0]
        if value is None:
            return None

        x, y, z = eval(value)
        position = _point.Point(x, y, z, db_id=self._position3d_id)
        position.bind(self.__update_position3d)
        return position

    @position3d.setter
    def position3d(self, value: list[float, float, float] | None):
        if value is not None:
            value = str(value)

        self._table.update(self._db_id, point3d=value)

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
    def forward_up(self) -> list[int, int]:
        """
        Return the forward and up side indexes.

        :returns: Property value. UNKNOWN details.
        :rtype: list[int, int]
        """
        value = self._table.select('forward_up', id=self._db_id)[0][0]
        return eval(f'[{value}]')

    @forward_up.setter
    def forward_up(self, value: list[int, int]):
        """
        Set the forward and up side indexes.

        :param value: Value to store or process.
        :type value: list[int, int]
        """
        value = str(value)[1:-1]
        self._table.update(self._db_id, forward_up=value)

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

    @property
    def size(self) -> tuple[float, float, float]:
        """
        Collects the length, width and height of a model from the obb after
        applying a user set rotation to the obb
        """
        import numpy as np

        obb = self.obb
        angle = self.angle3d
        if angle is None:
            return 0, 0, 0

        obb @= angle

        width = float(np.linalg.norm(obb[1] - obb[0]))  # X axis
        height = float(np.linalg.norm(obb[3] - obb[0]))  # Y axis
        length = float(np.linalg.norm(obb[4] - obb[0]))  # Z axis

        return width, height, length

    def download_complete(self):
        if self.db_id not in self._download_callbacks:
            return

        file = self.data_path
        if file is not None:
            # The packed geometry is opened as a memory mapped array and
            # handed to the callback as-is; the VBO streams it straight
            # from the mapping into the GPU vertex buffer.

            if self.angle3d is None:
                from ....ui.dialogs import part_orientation as _part_orientation
                from .... import app as _app

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
