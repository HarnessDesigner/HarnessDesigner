from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d


class Position2DMixin(BaseMixin):
    
    _stored_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def position2d(self) -> _point.Point:
        if self._stored_position2d is None and self._obj is not None:
            point_id = self.position2d_id

            self._stored_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_position2d.add_object(self._obj())

            point = self._stored_position2d.point
        elif self._stored_position2d is None:
            point = None
        else:
            point = self._stored_position2d.point

        return point

    @property
    def position2d_id(self) -> int:
        point_id = self._table.select('point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.position2d_id = point_id

        return point_id

    @position2d_id.setter
    def position2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)


class Position2DControl(_prop_grid.Position2DProperty):

    def __init__(self, parent):
        self.db_obj: Position2DMixin = None

        super().__init__(parent, '2D Position')

    def set_obj(self, db_obj: Position2DMixin):
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(None)
        else:
            self.SetValue(db_obj.position2d)
