from ....ui.editor_obj import prop_grid as _prop_grid

import wx

from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point2d as _pjt_point2d


class StartStopPosition2DMixin(BaseMixin):

    _stored_start_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def start_position2d(self) -> _point.Point:
        if self._stored_start_position2d is None and self._obj is not None:
            point_id = self.start_position2d_id

            self._stored_start_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_start_position2d.add_object(self._obj)
            point = self._stored_start_position2d.point
        elif self._stored_start_position2d is not None:
            point = self._stored_start_position2d.point
        else:
            point = None

        return point

    @property
    def start_position2d_id(self) -> int:
        point_id = self._table.select('start_point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.start_position2d_id = point_id

        return point_id

    @start_position2d_id.setter
    def start_position2d_id(self, value: int):
        self._table.update(self._db_id, start_point2d_id=value)
        self._populate('start_position2d_id')

    _stored_stop_position2d: _pjt_point2d.PJTPoint2D = None

    @property
    def stop_position2d(self) -> _point.Point:
        if self._stored_stop_position2d is None and self._obj is not None:
            point_id = self.stop_position2d_id

            self._stored_stop_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_stop_position2d.add_object(self._obj)
            point = self._stored_stop_position2d.point
        elif self._stored_stop_position2d is not None:
            point = self._stored_stop_position2d.point
        else:
            point = None

        return point

    @property
    def stop_position2d_id(self) -> int:
        point_id = self._table.select('stop_point2d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points2d (project_id, x, y) VALUES (?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.stop_position2d_id = point_id

        return point_id

    @stop_position2d_id.setter
    def stop_position2d_id(self, value: int):
        self._table.update(self._db_id, stop_point2d_id=value)
        self._populate('stop_position2d_id')


class StartStopPosition2DControl(_prop_grid.Property):

    def __init__(self, parent):
        self.db_obj: StartStopPosition2DMixin = None

        super().__init__(parent, '2D Positions', orientation=wx.VERTICAL)

        self.start_ctrl = _prop_grid.Position2DProperty(self, 'Start')
        self.stop_ctrl = _prop_grid.Position2DProperty(self, 'Stop')

    def set_obj(self, db_obj: StartStopPosition2DMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.start_ctrl.SetValue(None)
            self.stop_ctrl.SetValue(None)
        else:

            self.start_ctrl.SetValue(db_obj.start_position2d)
            self.stop_ctrl.SetValue(db_obj.stop_position2d)
