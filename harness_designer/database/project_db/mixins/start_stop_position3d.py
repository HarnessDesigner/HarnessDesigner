from ....ui.editor_obj import prop_grid as _prop_grid

import wx

from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point3d as _pjt_point3d


class StartStopPosition3DMixin(BaseMixin):

    _stored_start_position3d: _pjt_point3d.PJTPoint3D = None

    @property
    def start_position3d(self) -> _point.Point:
        if self._stored_start_position3d is None and self._obj is not None:
            point_id = self.start_position3d_id

            self._stored_start_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_start_position3d.add_object(self._obj)
            point = self._stored_start_position3d.point
        elif self._stored_start_position3d is not None:
            point = self._stored_start_position3d.point
        else:
            point = None

        return point

    @property
    def start_position3d_id(self) -> int:
        point_id = self._table.select('start_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.start_position3d_id = point_id

        return point_id

    @start_position3d_id.setter
    def start_position3d_id(self, value: int):
        self._table.update(self._db_id, start_point3d_id=value)
        self._populate('start_position3d_id')

    _stored_stop_position3d: _pjt_point3d.PJTPoint3D = None

    @property
    def stop_position3d(self) -> _point.Point:
        if self._stored_stop_position3d is None and self._obj is not None:
            point_id = self.stop_position3d_id

            self._stored_stop_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_stop_position3d.add_object(self._obj)
            point = self._stored_stop_position3d.point
        elif self._stored_stop_position3d is not None:
            point = self._stored_stop_position3d.point
        else:
            point = None

        return point

    @property
    def stop_position3d_id(self) -> int:
        point_id = self._table.select('stop_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.stop_position3d_id = point_id

        return point_id

    @stop_position3d_id.setter
    def stop_position3d_id(self, value: int):
        self._table.update(self._db_id, stop_point3d_id=value)
        self._populate('stop_position3d_id')


class StartStopPosition3DControl(_prop_grid.Property):

    def __init__(self, parent):
        self.db_obj: StartStopPosition3DMixin = None

        super().__init__(parent, '3D Positions', orientation=wx.VERTICAL)

        self.start_ctrl = _prop_grid.Position3DProperty(self, 'Start')
        self.stop_ctrl = _prop_grid.Position3DProperty(self, 'Stop')

    def set_obj(self, db_obj: StartStopPosition3DMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.start_ctrl.SetValue(None)
            self.stop_ctrl.SetValue(None)
        else:

            self.start_ctrl.SetValue(db_obj.start_position3d)
            self.stop_ctrl.SetValue(db_obj.stop_position3d)

