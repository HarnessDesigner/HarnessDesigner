from wx import propgrid as wxpg

from .base import BaseMixin
from ....geometry import point as _point


class Position2DMixin(BaseMixin):

    def _update_position2d(self, point: _point.Point):
        x, y = point.as_float[:-1]
        point_id = int(point.db_id[:-2])

        self._table.execute(f'UPDATE pjt_points2d SET x=?, y=? WHERE id = {point_id};', (x, y))
        self._table.commit()

    @property
    def position2d(self) -> "_point.Point":
        point_id = self.position2d_id

        self._table.execute(f'SELECT x, y FROM pjt_points2d WHERE id={point_id};')
        rows = self._table.fetchall()

        if rows:
            point = _point.Point(*rows[0], db_id=str(point_id) + '2d')
            point.bind(self._update_position2d)
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
        
    @property
    def _position2d_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import position_prop as _position_prop

        position_prop = _position_prop.Position2DProperty('Position 2D', 'position2d', self.position2d)

        return position_prop
