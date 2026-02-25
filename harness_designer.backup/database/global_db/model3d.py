import weakref
from typing import Iterable as _Iterable

import numpy as np
import tempfile
import os
import uuid
import shutil


from . import EntryBase, TableBase
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal


# TODO: Rework collecting the models from the web to include additional types.
#       Add dialog to load the model and add controls for the user to set how
#       agressive the triangle reduction is.
#       Also add controls to set the offset and the angle of the model so it
#       appears like it should.
#       the dialog needs to be tailored to the type of model being loaded
#       housing, boot, seal, etc...


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

    def insert(self, angle: _angle.Angle, idx: int, offset: _point.Point, data: bytes | None) -> "Model3D":
        db_id = TableBase.insert(self, angle=str(angle.quat), idx=idx,
                                 offset=str(list(offset.as_float)), data=data)

        return Model3D(self, db_id)


class ModelData:

    def __init__(self, data: list):
        self._data = data

    def __iter__(self):
        return iter(self._data)


class Model3D(EntryBase):
    _table: Models3DTable = None
    _angle_id = None
    _offset_id = None
    _model = None

    def __update_angle(self, angle: _angle.Angle):
        self._table.update(self._db_id, angle=str(angle.as_quat))

    @property
    def angle(self) -> _angle.Angle:
        if self._angle_id is None:
            self._angle_id = str(uuid.uuid4())

        value = eval(self._table.select('angle', id=self._db_id)[0][0])
        quat = np.array(value, dtype=np.dtypes.Float64DType)
        angle = _angle.Angle.from_quat(quat, order='YXZ', db_id=self._angle_id)
        angle.bind(self.__update_angle)
        return angle

    def __update_offset(self, offset: _point.Point):
        self._table.update(self._db_id, offset=str(list(offset.as_float)))

    @property
    def offset(self) -> _point.Point:
        if self._offset_id is None:
            self._offset_id = str(uuid.uuid4())

        value = eval(self._table.select('offset', id=self._db_id)[0][0])
        x, y, z = value
        offset = _point.Point(_decimal(x), _decimal(y), _decimal(z), db_id=self._offset_id)
        offset.bind(self.__update_offset)
        return offset

    @property
    def type(self) -> str:
        return self._table.select('type', id=self._db_id)[0][0]

    @type.setter
    def type(self, value: str):
        self._table.update(self._db_id, type=value)

    @property
    def target_count(self) -> int:
        return self._table.select('target_count', id=self._db_id)[0][0]

    @target_count.setter
    def target_count(self, value: int):
        self._table.update(self._db_id, target_count=value)

    @property
    def agressive(self) -> float:
        return self._table.select('agressive', id=self._db_id)[0][0]

    @agressive.setter
    def agressive(self, value: float):
        self._table.update(self._db_id, agressive=value)

    @property
    def path(self) -> str:
        return self._table.select('path', id=self._db_id)[0][0]

    @path.setter
    def path(self, value: str):
        self._table.update(self._db_id, path=value)

    def __remove_model_ref(self, ref):
        if ref == self._model:
            self._model = None

    @property
    def model(self) -> ModelData | None:
        if self._model is not None and self._model() is not None:
            return self._model()

        data_type = self.type
        path = self._table.db.settings_table['model_path']
        infile = os.path.join(path, self.path)

        path = tempfile.gettempdir()
        file = os.path.join(path, f'{self.path}.{data_type}')

        if data_type in ('stp', 'step'):  # Standard for the Exchange of Product model data
            from ...model_loaders import stp as loader
        elif data_type == '3mf':  # 3D Manufacturing Format
            from ...model_loaders import _3mf as loader  # NOQA
        elif data_type == 'gltf':  # Graphics Library Transmission Format
            from ...model_loaders import gltf as loader
        elif data_type == 'iges' or file.endswith('igs'):  # IGES
            from ...model_loaders import iges as loader
        elif data_type in ('wrl', 'wrz'):  # Virtual Reality Modeling Language
            from ...model_loaders import vrml as loader
        elif data_type == 'obj':
            from ...model_loaders import obj as loader
        elif data_type == 'stl':  # 'Stereolithography File'
            from ...model_loaders import stl as loader
        elif data_type == 'ply':  # 'Polygon File Format/Stanford Triangle Format'
            from ...model_loaders import ply as loader
        elif data_type == 'off':
            from ...model_loaders import off as loader
        elif data_type == 'glb':
            from ...model_loaders import glb as loader
        elif data_type == 'ifc':
            from ...model_loaders import ifc as loader
        else:
            raise RuntimeError('sanity check')

        shutil.copyfile(infile, file)

        model_data = loader.load(file)

        offset = self.offset
        angle = self.angle

        from ... import model_loaders

        for i, (vertices, faces) in enumerate(model_data):
            if len(faces) > 20000:
                vertices, faces = model_loaders.reduce_triangles(
                    vertices, faces, self.target_count, self.agressive)

            vertices @= angle
            vertices += offset
            model_data[i] = [vertices, faces]

        model_data = ModelData(model_data)

        self._model = weakref.ref(model_data, self.__remove_model_ref)

        return model_data
