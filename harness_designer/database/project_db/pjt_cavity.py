
from typing import Iterable as _Iterable, TYPE_CHECKING

from ...ui.editor_obj import prop_grid as _prop_grid

import uuid
import weakref

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (Position3DMixin, Position2DMixin, HousingMixin, PartMixin,
                     NameMixin, NotesMixin, Visible2DMixin, Visible3DMixin)
from ...geometry import angle as _angle
from ...geometry import point as _point


if TYPE_CHECKING:
    from . import pjt_seal as _pjt_seal
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point2d as _pjt_point2d

    from ..global_db import cavity as _cavity

    from ...objects import cavity as _cavity_obj


class PJTCavitiesTable(PJTTableBase):
    __table_name__ = 'pjt_cavities'

    def get_from_position3d_id(self, position3d_id) -> "PJTCavity":
        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

        rows = self.select('id', terminal_position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

    def get_from_position2d_id(self, position2d_id) -> "PJTCavity":
        rows = self.select('id', position2d_id=position2d_id)
        if rows:
            return self[rows[0][0]]

    def _table_needs_update(self) -> bool:
        from ..create_database import cavities

        return cavities.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import cavities

        cavities.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import cavities

        cavities.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCavity"]:

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCavity(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCavity":
        if isinstance(item, int):
            if item in self:
                return PJTCavity(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int) -> "PJTCavity":

        g_cavity = self.db.global_db.cavities_table[part_id]
        p3d = g_cavity.position3d
        p2d = g_cavity.position2d

        position3d = self.db.pjt_points3d_table.insert(*p3d.as_float)
        position2d = self.db.pjt_points2d_table.insert(*p2d.as_float[:-1])

        db_id = PJTTableBase.insert(
            self, part_id=part_id, housing_id=housing_id,
            point3d_id=position3d.db_id, point2d_id=position2d.db_id)

        return PJTCavity(self, db_id, self.project_id)


class PJTCavity(PJTEntryBase, Position3DMixin, Position2DMixin, HousingMixin,
                PartMixin, NameMixin, NotesMixin, Visible2DMixin, Visible3DMixin):

    _table: PJTCavitiesTable = None

    def build_monitor_packet(self):
        housing = self.housing

        packet = {
            'pjt_cavities': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id],
            'pjt_housings': [housing.db_id]
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(housing.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_cavity_obj.Cavity":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_cavity_obj.Cavity"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTCavitiesTable:
        return self._table

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        terminal_ids = self._table.db.pjt_terminals_table.select(
            'id', cavity_id=self._db_id)

        if not terminal_ids:
            return None

        return self._table.db.pjt_terminals_table[terminal_ids[0][0]]

    _stored_terminal_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def terminal_position3d(self) -> "_point.Point":
        if self._stored_terminal_position3d is None and self._obj is not None:
            point_id = self.terminal_position3d_id

            self._stored_terminal_position3d = self.table.db.pjt_points3d_table[point_id]
            self._stored_terminal_position3d.add_object(self._obj())

        return self._stored_terminal_position3d.point

    @property
    def terminal_position3d_id(self) -> int:
        point_id = self._table.select('terminal_point3d_id', id=self._db_id)[0][0]
        if point_id is None:

            cavity = self.part

            length = cavity.length

            ref = _point.Point(0.0, 0.0, length)

            position = self.position3d

            ref @= self.angle3d
            ref += position

            x, y, z = (position + ((ref - position) / 2.0)).as_float

            self._table.execute(
                f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                (self._table.project_id, x, y, z))

            self._table.commit()
            point_id = self._table.lastrowid
            self.terminal_position3d_id = point_id

        return point_id

    @terminal_position3d_id.setter
    def terminal_position3d_id(self, value: int):
        self._table.update(self._db_id, terminal_point3d_id=value)

    @property
    def terminal_position2d(self) -> "_point.Point":
        return self.position2d

    @property
    def terminal_position2d_id(self) -> int:
        return self.position2d_id

    @terminal_position2d_id.setter
    def terminal_position2d_id(self, value: int):
        self.position2d_id = value

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        seal_ids = self._table.db.pjt_seals_table.select(
            'id', cavity_id=self._db_id)

        if not seal_ids:
            return None

        return self._table.db.pjt_seals_table[seal_ids[0][0]]

    _stored_part: "_cavity.Cavity" = None

    @property
    def part(self) -> "_cavity.Cavity":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.covers_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    _angle2d_db_id: str = None

    def __update_angle2d(self, angle: _angle.Angle):
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle2d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(quat, euler_angle)

        delta = angle - o_angle

        terminal = self.terminal
        if terminal is not None:
            t_angle = terminal.angle2d
            t_angle += delta

        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat2d=str(quat))
        self._table.update(self._db_id, angle2d=str(euler_angle))

    @property
    def angle2d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle2d', id=self._db_id)[0][0])

        if self._angle2d_db_id is None:
            self._angle2d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle2d_db_id)
        angle.bind(self.__update_angle2d)

        return angle

    _angle3d_db_id: str = None

    def __update_angle3d(self, angle: _angle.Angle):
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(quat, euler_angle)

        delta = angle - o_angle

        terminal = self.terminal
        if terminal is not None:
            t_angle = terminal.angle3d
            t_angle += delta

        seal = self.seal
        if seal is not None:
            s_angle = seal.angle3d
            s_angle += delta

        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat3d=str(quat))
        self._table.update(self._db_id, angle3d=str(euler_angle))

    @property
    def angle3d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_db_id)
        angle.bind(self.__update_angle3d)

        return angle

    @property
    def _angle2d_propgrid(self) -> _prop_grid.Property:
        angle = self.angle2d

        angle_prop = _prop_grid.FloatProperty('Angle 2D', 'angle2d.z', angle.z,
                                              min_value=-180.0, max_value=180.0, increment=0.01, units='°')
        return angle_prop

    @property
    def _angle3d_propgrid(self) -> _prop_grid.Property:
        angle = self.angle3d

        group = _prop_grid.Property('Angle 3D', 'angle3d')
        x = _prop_grid.FloatProperty(
            'X', 'x', angle.x, min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        y = _prop_grid.FloatProperty(
            'Y', 'y', angle.y,  min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        z = _prop_grid.FloatProperty(
            'Z', 'z', angle.z, min_value=-180.0,
            max_value=180.0, increment=0.01, units='°')

        group.Append(x)
        group.Append(y)
        group.Append(z)

        return group

    @property
    def propgrid(self) -> tuple[_prop_grid.Category, _prop_grid.Category]:
        group = _prop_grid.Category('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid

        angle_prop = _prop_grid.Property('Angle')
        angle2d_prop = self._angle2d_propgrid
        angle3d_prop = self._angle3d_propgrid
        angle2d_prop.SetLabel('2D')
        angle3d_prop.SetLabel('3D')
        angle_prop.Append(angle2d_prop)
        angle_prop.Append(angle3d_prop)

        position_prop = _prop_grid.Property('Position')
        position2d_prop = self._position2d_propgrid
        position3d_prop = self._position3d_propgrid
        position2d_prop.SetLabel('2D')
        position3d_prop.SetLabel('3D')
        position_prop.Append(position2d_prop)
        position_prop.Append(position3d_prop)

        visible_prop = _prop_grid.Property('Visible')
        visible2d_prop = self._visible2d_propgrid
        visible3d_prop = self._visible3d_propgrid
        visible2d_prop.SetLabel('2D')
        visible3d_prop.SetLabel('3D')
        visible_prop.Append(visible2d_prop)
        visible_prop.Append(visible3d_prop)

        housing_prop = self._housing_propgrid

        _ = self.terminal_position3d
        terminal_position_prop = self._stored_terminal_position3d.propgrid
        terminal_position_prop.SetLabel('Terminal 3D Position')
        terminal_position_prop.SetName('terminal_position3d')

        position_prop.Append(terminal_position_prop)

        group.Append(name_prop)
        group.Append(notes_prop)
        group.Append(position_prop)
        group.Append(angle_prop)
        group.Append(housing_prop)
        group.Append(visible_prop)

        part_prop = self._part_propgrid

        return group, part_prop
