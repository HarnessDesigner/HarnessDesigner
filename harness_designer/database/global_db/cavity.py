import uuid
from typing import Iterable as _Iterable, TYPE_CHECKING

import numpy as np

from .bases import EntryBase, TableBase
from .mixins import NameMixin

from ...geometry import point as _point
from ...geometry import angle as _angle

if TYPE_CHECKING:
    from . import housing as _housing
    from . import terminal as _terminal


class CavitiesTable(TableBase):
    __table_name__ = 'cavities'

    def _table_needs_update(self) -> bool:
        from ..create_database import cavities

        return cavities.table.is_ok(self)

    def _add_table_to_db(self, _):
        from ..create_database import cavities

        cavities.table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import cavities

        cavities.table.update_fields(self)

    def __getitem__(self, item) -> "Cavity":
        if isinstance(item, int):
            if item in self:
                return Cavity(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def __iter__(self) -> _Iterable["Cavity"]:
        for db_id in TableBase.__iter__(self):
            yield Cavity(self, db_id)

    def insert(self, housing_id: int, idx: int) -> "Cavity":
        db_id = TableBase.insert(self, housing_id=housing_id, idx=idx)

        return Cavity(self, db_id)


class Cavity(EntryBase, NameMixin):
    _table: CavitiesTable = None

    def build_monitor_packet(self):
        packet = {
            'cavities': [self.db_id]
        }

        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

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
    def terminal_sizes(self) -> list[float]:
        return eval(self._table.select('terminal_sizes', id=self._db_id)[0][0])

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        for i, item in enumerate(value):
            value[i] = round(item, 6)

        self._table.update(self._db_id, terminal_sizes=str(value))

    _position3d_id: str = None

    def __update_position3d(self, point: _point.Point):
        self._table.update(self._db_id, point3d=str(list(point.as_float)))

    @property
    def position3d(self) -> _point.Point:
        """
        This is relitive to the housing location
        """
        if self._position3d_id is None:
            self._position3d_id = str(uuid.uuid4())

        x, y, z = eval(self._table.select('point3d', id=self._db_id)[0][0])
        point = _point.Point(x, y, z, self._position3d_id)
        point.bind(self.__update_position3d)

        return point

    _position2d_id: str = None

    def __update_position2d(self, point: _point.Point):
        self._table.update(self._db_id, point2d=str(list(point.as_float[:-1])))

    @property
    def position2d(self) -> _point.Point:
        """
        This is relitive to the housing location
        """
        if self._position2d_id is None:
            self._position2d_id = str(uuid.uuid4())

        x, y = eval(self._table.select('point2d', id=self._db_id)[0][0])
        point = _point.Point(x, y, db_id=self._position3d_id)

        point.bind(self.__update_position2d)

        return point

    _angle3d_id: str = None

    def _update_angle3d(self, angle: _angle.Angle):
        euler = list(angle.as_euler_float)
        quat = list(angle.as_quat_float)
        self._table.update(self._db_id, angle3d=str(euler), quat3d=str(quat))

    @property
    def angle3d(self) -> _angle.Angle:
        """
        This is relitive to the housing angle
        """
        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        euler = eval(self._table.select('angle3d', id=self._db_id)[0][0])
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler, self._angle3d_id)
        angle.bind(self._update_angle3d)

        return angle

    _angle2d_id: str = None

    def _update_angle2d(self, angle: _angle.Angle):
        euler = [angle.x, angle.y, angle.z]
        quat = angle.as_quat_float
        self._table.update(self._db_id, angle2d=str(euler), quat2d=str(quat))

    @property
    def angle2d(self):
        """
        This is relitive to the housing angle
        """
        if self._angle2d_id is None:
            self._angle2d_id = str(uuid.uuid4())

        euler = eval(self._table.select('angle2d', id=self._db_id)[0][0])
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler, self._angle2d_id)
        angle.bind(self._update_angle2d)

        return angle

    @property
    def round_terminal(self) -> bool:
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        self._table.update(self._db_id, round_terminal=int(value))

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=round(value, 6))

    @property
    def width(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                width = min(width, height)
                self._table.update(self._db_id, width=width, height=width)
            return width

        else:
            return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, width=round(value, 6))

    @property
    def height(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                height = min(width, height)
                self._table.update(self._db_id, width=height, height=height)

            return height

        else:
            return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, height=round(value, 6))

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            if self.round_terminal:
                if y > 0:
                    x = y

                    self._table.update(self._db_id, width=y)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, width=1.0)
                x = 1.0

        if y <= 0:
            if self.round_terminal:
                if x > 0:
                    y = x

                    self._table.update(self._db_id, height=x)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, height=1.0)
                y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        terminal_sizes = self.terminal_sizes
        round_terminal = self.round_terminal

        res = []

        for terminal in self.housing.compat_terminals:
            if (
                not terminal_sizes and
                terminal.round_terminal == round_terminal
            ):
                res.append(terminal)
            elif terminal_sizes:
                for terminal_size in terminal_sizes:
                    if (
                        terminal.blade_size == terminal_size and
                        terminal.round_terminal == round_terminal
                    ):
                        res.append(terminal)

        return res
