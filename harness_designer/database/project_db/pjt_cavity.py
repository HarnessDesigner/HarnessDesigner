
from typing import Iterable as _Iterable, TYPE_CHECKING

from ...ui.editor_obj import prop_grid as _prop_grid

import uuid
import weakref
import wx

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    HousingMixin,
    PartMixin,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    Visible2DMixin, Visible2DControl,
    Visible3DMixin, Visible3DControl,
    Angle2DMixin, Angle2DControl,
    Angle3DMixin, Angle3DControl
)

from ...geometry import angle as _angle
from ...geometry import point as _point


if TYPE_CHECKING:
    from . import pjt_seal as _pjt_seal
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_point3d as _pjt_point3d

    from ..global_db import cavity as _cavity

    from ...objects import cavity as _cavity_obj


class PJTCavitiesTable(PJTTableBase):
    __table_name__ = 'pjt_cavities'

    _control: "PJTCavityControl" = None

    @property
    def control(self) -> "PJTCavityControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTCavityControl(mainframe)
        cls._control.Show(False)

        # for i in range(20):
        #     control = PJTCavityControl(mainframe)
        #     control.Show(False)
        #     control.SetIndex(i + 1)
        #     cls._controls.append(control)

    _controls: list["PJTCavityControl"] = []

    def get_control(self, index):

        controls_len = len(self._controls)

        if controls_len - 1 < index:
            for i in range(controls_len - 1, index):
                ctrl = PJTCavityControl(self.db.mainframe)
                ctrl.SetIndex(i + 1)
                ctrl.Show(False)
                self._controls.append(ctrl)

        return self._controls[index]

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
                PartMixin, NameMixin, NotesMixin, Visible2DMixin, Visible3DMixin,
                Angle2DMixin, Angle3DMixin):

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
        self._populate('terminal_position3d_id')

    @property
    def terminal_position2d(self) -> "_point.Point":
        return self.position2d

    @property
    def terminal_position2d_id(self) -> int:
        return self.position2d_id

    @terminal_position2d_id.setter
    def terminal_position2d_id(self, value: int):
        self.position2d_id = value
        self._populate('terminal_position2d_id')

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

    def _update_angle2d(self, angle: _angle.Angle):
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
        self._populate('angle2d')

    def _update_angle3d(self, angle: _angle.Angle):
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
        self._populate('angle3d')

    @property
    def angle3d(self) -> _angle.Angle:
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler_angle = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler_angle, db_id=self._angle3d_db_id)
        angle.bind(self._update_angle3d)

        return angle


class PJTCavityControl(_prop_grid.Category):

    def SetIndex(self, index):
        self.SetLabel(f'Cavity {index}')

    def __init__(self, parent):
        self.db_obj: PJTCavity = None

        super().__init__(parent, 'Cavity')

        self.nb = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self.nb, 'General')
        self.name_ctrl = NameControl(general_page)
        self.notes_ctrl = NotesControl(general_page)

        angle_page = _prop_grid.Category(self.nb, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self.nb, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self.nb, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        terminal_page = _prop_grid.Category(self.nb, 'Terminal')

        from . import pjt_terminal as _pjt_terminal  # NOQA

        self.terminal_ctrl = _pjt_terminal.PJTTerminalControl(terminal_page)

        seal_page = _prop_grid.Category(self.nb, 'Seal')

        from . import pjt_seal as _pjt_seal  # NOQA

        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        part_page = _prop_grid.Category(self.nb, 'Part')
        from ..global_db import cavity as _cavity  # NOQA

        self.part_ctrl = _cavity.CavityControl(part_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            terminal_page,
            seal_page,
            part_page
        ):
            self.nb.AddPage(page, page.GetLabel())
            page.Realize()

    def set_obj(self, db_obj: PJTCavity):
        self.db_obj = db_obj
        self.name_ctrl.set_obj(db_obj)
        self.notes_ctrl.set_obj(db_obj)
        self.angle2d_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)
        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.terminal_ctrl.set_obj(None)
            self.seal_ctrl.set_obj(None)
            self.part_ctrl.set_obj(None)
        else:
            self.terminal_ctrl.set_obj(db_obj.terminal)
            self.seal_ctrl.set_obj(db_obj.seal)
            self.part_ctrl.set_obj(db_obj.part)
