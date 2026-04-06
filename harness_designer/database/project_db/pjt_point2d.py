from typing import Iterable as _Iterable

from wx import propgrid as wxpg

from .pjt_bases import PJTEntryBase, PJTTableBase

from ...geometry import point as _point


class PJTPoints2DTable(PJTTableBase):
    __table_name__ = 'pjt_points2d'

    def _table_needs_update(self) -> bool:
        from ..create_database import points2d

        return points2d.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import points2d

        points2d.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import points2d

        points2d.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTPoint2D"]:

        for db_id in PJTTableBase.__iter__(self):
            point = PJTPoint2D(self, db_id, self.project_id)
            yield point

    def __getitem__(self, item) -> "PJTPoint2D":
        if isinstance(item, int):
            if item in self:
                return PJTPoint2D(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, x: float, y: float) -> "PJTPoint2D":
        db_id = PJTTableBase.insert(self, x=x, y=y)
        return PJTPoint2D(self, db_id, self.project_id)


class PJTPoint2D(PJTEntryBase):
    _table: PJTPoints2DTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_points2d': [self.db_id],
        }

        return packet

    @property
    def table(self) -> PJTPoints2DTable:
        return self._table

    @property
    def x(self) -> float:
        return self._table.select('x', id=self._db_id)[0][0]

    @x.setter
    def x(self, value: float):
        self._table.update(self._db_id, x=value)
        self._process_callbacks()

    @property
    def y(self) -> float:
        return self._table.select('y', id=self._db_id)[0][0]

    @y.setter
    def y(self, value: float):
        self._table.update(self._db_id, y=value)
        self._process_callbacks()

    @property
    def point(self) -> _point.Point:

        point = _point.Point(self.x, self.y, db_id=str(self.db_id) + '2d')
        point.bind(self.__update_point)
        return point

    def __update_point(self, point: _point.Point):
        x, y, z = point.as_float
        self._table.update(self._db_id, x=x, y=y)
        self._process_callbacks()

    @property
    def propgrid(self) -> wxpg.PGProperty:
        group = wxpg.PropertyCategory('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid
        angle_prop = self._angle3d_propgrid
        position_prop = self._position3d_propgrid
        housing_prop = self._housing_propgrid
        visible_prop = self._visible3d_propgrid

        group.AppendChild(name_prop)
        group.AppendChild(notes_prop)
        group.AppendChild(angle_prop)
        group.AppendChild(position_prop)
        group.AppendChild(visible_prop)
        group.AppendChild(housing_prop)

        part_prop = self._part_propgrid

        return group, part_prop
