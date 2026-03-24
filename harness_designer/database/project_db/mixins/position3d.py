

from .base import BaseMixin
from ....geometry import point as _point


class Position3DMixin(BaseMixin):

    def _update_position3d(self, point: _point.Point):
        x, y, z = point.as_float
        point_id = int(point.db_id[:-2])

        self._table.execute(f'UPDATE pjt_points3d SET x=?, y=?, z=? WHERE id = {point_id};', (x, y, z))
        self._table.commit()

    @property
    def position3d(self) -> "_point.Point":
        point_id = self.position3d_id

        self._table.execute(f'SELECT x, y, z FROM pjt_points3d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id) + '3d')
            point.bind(self._update_position3d)
            return point

    @property
    def position3d_id(self) -> int:
        point_id = self._table.select('point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.position3d_id = point_id

        return point_id

    @position3d_id.setter
    def position3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
