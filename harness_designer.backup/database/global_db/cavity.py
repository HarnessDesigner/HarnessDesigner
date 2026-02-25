from typing import Iterable as _Iterable, TYPE_CHECKING

import numpy as np

from . import EntryBase, TableBase
from .mixins import NameMixin

if TYPE_CHECKING:
    from . import housing as _housing

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal


class CavitiesTable(TableBase):
    __table_name__ = 'cavities'

    def __iter__(self) -> _Iterable["Cavity"]:
        for db_id in TableBase.__iter__(self):
            yield Cavity(self, db_id)

    def insert(self, housing_id: int, idx: int, name: str, size: float, point2d: _point.Point,
               point3d: _point.Point, x_angle: _decimal, y_angle: _decimal, z_angle: _decimal) -> "Cavity":

        db_id = TableBase.insert(self, housing_id=housing_id, idx=idx, name=name, size=size,
                                 point2d=str(list(point2d.as_float[:-1])),
                                 point3d=str(list(point3d.as_float)),
                                 rotation3d=str([float(x_angle), float(y_angle), float(z_angle)]))

        return Cavity(self, db_id)


class Cavity(EntryBase, NameMixin):
    # ok so how the system with the cavities works is the point3d location
    # for a cavity should be set so a terminal will sit properly into a housing
    # when the point is centered in one of the ends of the terminal. This point
    # is also used as the attachment point for a wire.
    # the angle that is present is the angle or direction that the terminal
    # pin is going to be pointed. both the angle and the position of a cavity
    # are relitive to the housing when the housing is positioned at x=0, y=0, z=0
    # which should be set as lenght / 2, height / 2, depth / 2 for the housing size.
    # and after any default rotation has been applied to the the housing.
    # TODO: create a 3d view that will provide the user a way to set offsets
    #       and angle for the housing and also provide a way to set the cavity
    #       positions and angles. tool to do this will have controls to set the
    #       x, y and z axis offsets for the housing and controls to set the
    #       x, y and z rotation angles for the housing. The user will then be
    #       able to add cavities which will be displayed as a box that the user
    #       will be able to set the length, width and height of the box along
    #       with the position of the box relitive to the housing. Using
    #       transparency in opengl and creating a wireframe view of the cavities
    #       should make the process easier to do. I will provide proper mouse
    #       controls to so the user willbe able to move around the object to get
    #       the cavities set properly. I will also provide indicators to assist
    #       in positioning and direction. This is somethign that will need to
    #       be done for every housing that is added to the parts database.
    #       I will provide some import machinery so the information willbe able
    #       to be loaded using a json file since wuite a bit of it will be
    #       repetitive. If the centerline is provided prior to positioning the
    #       cavities that will be used as a way to "guess" what thenext cavity
    #       location is going to be. If the centerline has not been provided the
    #       guess will be made from the last adjacent cavities that have been set.
    #       If no centerline as been provided one will be created using the distance
    #       between center points of cavities that have the larges count that are
    #       of the same size and are adjacent to each other.

    _table: CavitiesTable = None

    @property
    def housing(self) -> "_housing.Housing":
        from .housing import Housing

        housing_id = self.housing_id
        return Housing(self._table.db.housings_table, housing_id)

    @property
    def housing_id(self) -> int:
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @property
    def idx(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        self._table.update(self._db_id, idx=value)
    
    @property
    def terminal_size(self) -> _decimal | None:
        obj = self._table.select('terminal_size', id=self._db_id)[0][0]

        if obj is None:
            return None

        return _decimal(obj)

    @terminal_size.setter
    def terminal_size(self, value: _decimal | None):
        if value is not None:
            value = float(value)

        self._table.update(self._db_id, terminal_size=value)

    @property
    def point2d(self):
        db_id = self.point2d_id
        if db_id is None:
            return

        return self._table.db.cavity_points2d_table[db_id]

    @property
    def point2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    def point2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)

    @property
    def point3d(self):
        db_id = self.point3d_id
        if db_id is None:
            return

        return self._table.db.cavity_points3d_table[db_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)

    @property
    def quat(self) -> np.ndarray:
        quat = eval(self._table.select('quat', id=self._db_id)[0][0])
        return np.array(quat, dtype=np.dtypes.Float64DType)

    @quat.setter
    def quat(self, value: np.ndarray):
        self._table.update(self._db_id, quat=str(value.tolist()))

    @property
    def length(self) -> _decimal:
        return _decimal(self._table.select('length', id=self._db_id)[0][0])

    @length.setter
    def length(self, value: _decimal):
        self._table.update(self._db_id, length=float(value))
