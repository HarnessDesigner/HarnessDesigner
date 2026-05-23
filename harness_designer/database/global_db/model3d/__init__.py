# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import os
from PySide6.QtWidgets import QDialog
import uuid

from .... import resources as _resources
from ...create_database import models3d as _models3d

from ....geometry import angle as _angle
from ....geometry import point as _point

from . import loader as _loader
from . import positioning as _positioning

from ..bases import EntryBase, TableBase

if TYPE_CHECKING:
    from .. import file_types as _file_types


class Models3DTable(TableBase):
    """Represent a models 3dtable in :mod:`harness_designer.database.global_db.model3d.__init__`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'models3d'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return _models3d.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        _models3d.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        _models3d.table.update_fields(self)

    def __iter__(self) -> _Iterable["Model3D"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Model3D']
        """
        for db_id in TableBase.__iter__(self):
            yield Model3D(self, db_id)

    def __getitem__(self, item) -> "Model3D":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

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
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

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
    """Represent a model 3D in :mod:`harness_designer.database.global_db.model3d.__init__`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: Models3DTable = None
    _angle3d_id: str = None
    _position3d_id: str = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

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
        """Return the data path.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str | None
        """
        file_id = self.uuid
        if file_id is None:
            values = _resources.collect_resource(
                self._table, _resources.IMAGE_TYPE_MODEL, self.path)

            if values is None:
                return None

            file_id, file_type_id = values

            self._table.update(self._db_id, file_type_id=file_type_id)
            self._table.update(self._db_id, uuid=file_id)

        file_type = self.file_type

        cad_path = self._table.db.settings_table['model_path']
        return os.path.join(cad_path, f'{file_id}.{file_type.extension}')

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

    def __update_angle3d(self, angle: _angle.Angle):
        """Update the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        quat = list(angle.as_quat_float)
        euler = list(angle.as_euler_float)

        self._table.update(self._db_id, angle3d=str(euler))
        self._table.update(self._db_id, quat3d=str(quat))

    @property
    def angle3d(self) -> _angle.Angle:
        """Return the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

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
        """Update the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param offset: Value for ``offset``.
        :type offset: :class:`_point.Point`
        """
        self._table.update(self._db_id, offset=str(list(offset.as_float)))

    @property
    def position3d(self) -> _point.Point:
        """Return the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

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
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        self._table.update(self._db_id, scale=str(list(scale.as_float)))

    @property
    def scale(self) -> _point.Point:
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

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
        """Return the target count.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('target_count', id=self._db_id)[0][0]

    @target_count.setter
    def target_count(self, value: int):
        """Set the target count.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, target_count=value)

    @property
    def aggressiveness(self) -> float:
        """Return the aggressiveness.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return float(self._table.select('aggressiveness', id=self._db_id)[0][0])

    @aggressiveness.setter
    def aggressiveness(self, value: float):
        """Set the aggressiveness.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, aggressiveness=value)

    @property
    def update_rate(self) -> int:
        """Return the update rate.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('update_rate', id=self._db_id)[0][0]

    @update_rate.setter
    def update_rate(self, value: int):
        """Set the update rate.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, update_rate=value)

    @property
    def simplify(self) -> bool:
        """Return the simplify.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('simplify', id=self._db_id)[0][0])

    @simplify.setter
    def simplify(self, value: bool):
        """Set the simplify.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, simplify=int(value))

    @property
    def iterations(self) -> int:
        """Return the iterations.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('iterations', id=self._db_id)[0][0]

    @iterations.setter
    def iterations(self, value: int):
        """Set the iterations.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, iterations=value)

    def modify_model(self):
        """Execute the modify model operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        file = self.data_path
        if file is None:
            return

        try:
            vertices, faces = _loader.load(file)
        except _loader.ModelLoadError:
            return

        dialog = _positioning.PositioningDialog(
            self._table.db.mainframe, vertices, faces, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
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

            p = self.position3d
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

        dialog.deleteLater()

    def load(self):
        """Execute the load operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        file = self.data_path
        if file is None:
            return None

        try:
            vertices, faces = _loader.load(file)
        except _loader.ModelLoadError:
            return None

        # this code block makes sure the model has 0, 0 as the center of
        # the model. I have found that the models that are loaded from
        # the manufacturers don't always have 0, 0 as the center of the model
        # and for alignment of objects we need to make sure that the centers are
        # used.
        vertices_reshaped = vertices.reshape(-1, 3)
        centroid = vertices_reshaped.mean(axis=0)
        vertices_reshaped -= centroid
        vertices_reshaped = vertices_reshaped.ravel()
        vertices = vertices_reshaped.reshape(-1, 3)

        # If the user has a GPU that doesn't have a large amount of
        # memory available or the GPU doesn't have a lot of processing power
        # the user has the ability to reduce the quality by reducing the number
        # of vertices a model has. This will shrink the amount of memory used
        # on the GPU as well as increasing the speed in which the GPU renders
        # a model
        if self.simplify:
            target_count = self.target_count
            aggressiveness = self.aggressiveness
            update_rate = self.update_rate
            iterations = self.iterations
            vertices, faces = _loader.reduce_triangles(vertices, faces, target_count,
                                                       aggressiveness, update_rate,
                                                       iterations)

        scale = self.scale
        angle = self.angle3d
        position = self.position3d

        vertices *= scale
        vertices @= angle
        vertices += position

        vertices = vertices.reshape(-1, 3)
        faces = faces.reshape(-1, 3)

        return vertices, faces
