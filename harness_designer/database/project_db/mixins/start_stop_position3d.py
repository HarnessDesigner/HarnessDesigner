from .base import BaseMixin

from ....geometry import point as _point


class StartStopPosition3DMixin(BaseMixin):

    def _update_start_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def start_position3d(self) -> _point.Point:
        point_id = self.start_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self._update_start_position3d)
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

    def _update_stop_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id)

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def stop_position3d(self) -> _point.Point:
        point_id = self.stop_position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id))
            point.bind(self._update_stop_position3d)
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
