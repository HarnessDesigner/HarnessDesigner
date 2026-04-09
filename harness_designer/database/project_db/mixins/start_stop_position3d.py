from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point3d as _pjt_point3d


class StartStopPosition3DMixin(BaseMixin):

    def _update_start_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

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

    @property
    def _start_stop_position3d_propgrid(self) -> _prop_grid.Property:

        position_prop = _prop_grid.Property('3D Positions')

        _ = self.start_position3d
        _ = self.stop_position3d

        start_prop = self._stored_start_position3d.propgrid
        stop_prop = self._stored_stop_position3d.propgrid

        start_prop.SetLabel('Start')
        start_prop.SetName('start_position3d')
        stop_prop.SetLabel('Stop')
        stop_prop.SetName('stop_position3d')

        position_prop.Append(start_prop)
        position_prop.Append(stop_prop)

        return position_prop
