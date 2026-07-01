# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
import weakref
import numpy as np
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import angle as _angle
from ...geometry import point as _point
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


if TYPE_CHECKING:
    from . import pjt_seal as _pjt_seal
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_point3d as _pjt_point3d
    from ..global_db import cavity as _cavity
    from ...objects import cavity as _cavity_obj


class PJTCavitiesTable(PJTTableBase):
    """
    Represent a PJT cavities table in :mod:`harness_designer.database.project_db.pjt_cavity`.
    """

    __table_name__ = 'pjt_cavities'
    _control: "PJTCavityControl" = None

    @property
    def control(self) -> "PJTCavityControl":
        """
        Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCavityControl`

        :raises RuntimeError: Raised when the operation cannot be completed.
        """

        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        """
        Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """

        cls._control = PJTCavityControl(mainframe)
        cls._control.hide()
        #
        # for i in range(20):
        #     control = PJTCavityControl(mainframe)
        #     control.hide()
        #     control.SetIndex(i + 1)
        #     cls._controls.append(control)

    _controls: list["PJTCavityControl"] = []

    def get_control(self, index):
        """
        Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        while len(self._controls) < index + 1:
            ctrl = PJTCavityControl(self.db.mainframe)
            ctrl.SetIndex(len(self._controls))
            ctrl.hide()
            self._controls.append(ctrl)

        return self._controls[index]

    def get_from_position3d_id(self, position3d_id) -> "PJTCavity":
        """
        Return the from position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTCavity`
        """

        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

        rows = self.select('id', terminal_position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

    def get_from_position2d_id(self, position2d_id) -> "PJTCavity":
        """
        Return the from position 2D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param position2d_id: Identifier for the position 2D.
        :type position2d_id: UNKNOWN

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTCavity`
        """

        rows = self.select('id', position2d_id=position2d_id)
        if rows:
            return self[rows[0][0]]

    def _table_needs_update(self) -> bool:
        """
        Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """

        from ..create_database import cavities

        return cavities.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """
        Add a table to database.
        """

        from ..create_database import cavities

        cavities.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """
        Update the table in database.
        """

        from ..create_database import cavities

        cavities.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCavity"]:
        """
        Iterate over the available items.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTCavity']
        """

        for db_id in PJTTableBase.__iter__(self):
            yield PJTCavity(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCavity":
        """
        Return the requested item.

        :param item: Item identifier or value.
        :type item: UNKNOWN

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTCavity`

        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """

        if isinstance(item, int):
            if item in self:
                return PJTCavity(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, housing_id: int, name: str = "") -> "PJTCavity":
        """
        Execute the insert operation.

        :param part_id: Identifier for the part.
        :type part_id: int

        :param housing_id: Identifier for the housing.
        :type housing_id: int

        :param name: name of the cavity
        :type name: str

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTCavity`
        """

        g_cavity = self.db.global_db.cavities_table[part_id]

        aabb = g_cavity.aabb
        obb = g_cavity.obb

        c_position2d = g_cavity.position2d
        c_position3d = g_cavity.position3d

        c_angle2d = g_cavity.angle2d
        c_angle3d = g_cavity.angle3d

        housing = self.db.pjt_housings_table[housing_id]

        h_angle2d = housing.angle2d
        h_angle3d = housing.angle3d

        h_position2d = housing.position2d
        h_position3d = housing.position3d

        position2d = h_position2d + c_position2d
        position3d = h_position3d + c_position3d

        angle2d = h_angle2d + c_angle2d
        angle3d = h_angle3d + c_angle3d

        inverse_h_angle3d = h_angle3d.inverse

        aabb -= h_position3d
        obb -= h_position3d

        aabb @= inverse_h_angle3d
        obb @= inverse_h_angle3d

        aabb @= angle3d
        obb @= angle3d

        aabb += position3d
        obb += position3d

        aabb = [[float(str(item)) for item in items]
                for items in aabb.tolist()]

        obb = [[float(str(item)) for item in items]
               for items in obb.tolist()]

        quat2d = list(angle2d.as_quat_float)
        angle2d = list(angle2d.as_euler_float)

        quat3d = list(angle3d.as_quat_float)
        angle3d = list(angle3d.as_euler_float)

        position2d = self.db.pjt_points2d_table.insert(*position2d.as_float[:-1])
        position3d = self.db.pjt_points3d_table.insert(*position3d.as_float)

        db_id = PJTTableBase.insert(self, part_id=part_id, housing_id=housing_id,
                                    name=name, quat2d=str(quat2d), angle2d=str(angle2d),
                                    quat3d=str(quat3d), angle3d=str(angle3d),
                                    point3d_id=position3d.db_id,
                                    point2d_id=position2d.db_id, aabb=str(aabb), obb=str(obb))

        return PJTCavity(self, db_id, self.project_id)


class PJTCavity(PJTEntryBase, Position3DMixin, Position2DMixin, HousingMixin,
                PartMixin, NameMixin, NotesMixin, Visible2DMixin, Visible3DMixin,
                Angle2DMixin, Angle3DMixin):
    """
    Represent a PJT cavity in :mod:`harness_designer.database.project_db.pjt_cavity`.
    """

    _table: PJTCavitiesTable = None

    def build_monitor_packet(self):
        """
        Build the monitor packet.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

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
        """
        Return the object.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_cavity_obj.Cavity`
        """

        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        """
        Release the obj ref.
        """

        self._obj = None

    def set_object(self, obj: "_cavity_obj.Cavity"):
        """
        Set the object.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity_obj.Cavity`
        """

        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTCavitiesTable:
        """
        Return the table.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTCavitiesTable`
        """

        return self._table

    @property
    def aabb(self) -> np.ndarray:
        value = self._table.select('aabb', id=self._db_id)[0][0]
        value = np.array(eval(value), dtype=np.float32)
        return value

    @aabb.setter
    def aabb(self, value: np.ndarray):
        value = [[float(str(item)) for item in items]
                 for items in value.tolist()]

        self._table.update(self._db_id, aabb=str(value))

    @property
    def obb(self) -> np.ndarray:
        value = self._table.select('obb', id=self._db_id)[0][0]
        value = np.array(eval(value), dtype=np.float32)
        return value

    @obb.setter
    def obb(self, value: np.ndarray):
        value = [[float(str(item)) for item in items]
                 for items in value.tolist()]

        self._table.update(self._db_id, obb=str(value))

    _stored_terminal: "_pjt_terminal.PJTTerminal" = None

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        """
        Return the terminal.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_terminal.PJTTerminal`
        """

        if self._stored_terminal is not None:
            return self._stored_terminal

        terminal_ids = self._table.db.pjt_terminals_table.select(
            'id', cavity_id=self._db_id)

        if not terminal_ids:
            return None

        self._stored_terminal = self._table.db.pjt_terminals_table[terminal_ids[0][0]]
        return self._stored_terminal

    _stored_terminal_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def terminal_position3d(self) -> "_point.Point":
        """
        Return the terminal position 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_terminal_position3d is None:
            point_id = self.terminal_position3d_id

            self._stored_terminal_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_terminal_position3d.add_object(self._obj())

        return self._stored_terminal_position3d.point

    @property
    def terminal_position3d_id(self) -> int:
        """
        Return the terminal position 3D ID.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

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
        """
        Set the terminal position 3D ID.

        :param value: Value to store or process.
        :type value: int
        """

        self._table.update(self._db_id, terminal_point3d_id=value)
        self._populate('terminal_position3d_id')

    @property
    def terminal_position2d(self) -> "_point.Point":
        """
        Return the terminal position 2D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        return self.position2d

    @property
    def terminal_position2d_id(self) -> int:
        """
        Return the terminal position 2D ID.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        return self.position2d_id

    @terminal_position2d_id.setter
    def terminal_position2d_id(self, value: int):
        """
        Set the terminal position 2D ID.

        :param value: Value to store or process.
        :type value: int
        """

        self.position2d_id = value
        self._populate('terminal_position2d_id')

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        """
        Return the seal.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_seal.PJTSeal`
        """

        seal_ids = self._table.db.pjt_seals_table.select(
            'id', cavity_id=self._db_id)

        if not seal_ids:
            return None

        return self._table.db.pjt_seals_table[seal_ids[0][0]]

    @property
    def seal_position3d(self) -> "_point.Point":
        """
        Return the seal position 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.terminal_position3d

    @property
    def seal_position3d_id(self) -> int:
        """
        Return the seal position 3D ID.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """

        return self.terminal.position3d_id

    _stored_part: "_cavity.Cavity" = None

    @property
    def part(self) -> "_cavity.Cavity":
        """
        Return the part.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_cavity.Cavity`
        """

        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.cavities_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    def _update_angle2d(self, angle: _angle.Angle):
        """
        Update the angle 2D.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])
        euler = eval(self._table.select('angle2d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(quat, euler)

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat2d=quat)
        self._table.update(self._db_id, angle2d=euler)

        delta = angle - o_angle

        terminal = self.terminal
        if terminal is not None:
            t_angle = terminal.angle2d
            t_angle += delta

        self._populate('angle2d')

    def _update_angle3d(self, angle: _angle.Angle):
        """
        Update the angle 3D.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """

        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(quat, euler)
        inverse_angle = o_angle.inverse
        position = self.position3d

        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat3d=quat)
        self._table.update(self._db_id, angle3d=euler)

        accessory = self.terminal or self.seal
        if accessory is not None:
            a_position = accessory.position3d
            pos = a_position.copy()
            pos -= position
            pos @= inverse_angle
            pos @= angle
            pos += position

            delta = pos - a_position
            a_position += delta

            old_angle = accessory.angle3d
            quat = angle.as_quat_numpy

            with old_angle:
                old_angle._q.w = quat[0]
                old_angle._q.x = quat[1]
                old_angle._q.y = quat[2]
                old_angle._q.z = quat[3]

                old_angle.x = angle.x
                old_angle.y = angle.y
                old_angle.z = angle.z

                old_angle._matrix[:] = angle.as_matrix_numpy.copy()  # NOQA

            old_angle._process_callbacks()  # NOQA

        aabb = self.aabb
        obb = self.obb

        aabb -= position
        obb -= position

        aabb @= inverse_angle
        obb @= inverse_angle

        aabb @= angle
        obb @= angle

        aabb += position
        obb += position

        self.aabb = aabb
        self.obb = obb

        self._populate('angle3d')

    @property
    def angle3d(self) -> _angle.Angle:
        """
        Return the angle 3D.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """

        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])
        euler = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        if self._angle3d_db_id is None:
            self._angle3d_db_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, euler, db_id=self._angle3d_db_id)
        angle.bind(self._update_angle3d)

        return angle


class PJTCavityControl(_prop_ctrls.Category):
    """
    Represent a PJT cavity control in :mod:`harness_designer.database.project_db.pjt_cavity`.
    """

    def SetIndex(self, index):
        """
        Execute the set index operation.

        :param index: Index value.
        :type index: UNKNOWN
        """

        self.SetLabel(f'Cavity {index}')

        print('creating cavity:', index)

    def __init__(self, parent):
        """
        Initialise the :class:`PJTCavityControl` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTCavity = None

        super().__init__(parent, 'Cavity')

        self.nb = QTabWidget(self)
        self.nb.setTabPosition(QTabWidget.TabPosition.North)
        self.nb.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self.nb, 'General')
        self.name_ctrl = NameControl(general_page)
        self.notes_ctrl = NotesControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.notes_ctrl)

        angle_page = _prop_ctrls.Category(self.nb, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        angle_page.addWidget(self.angle2d_ctrl)
        angle_page.addWidget(self.angle3d_ctrl)

        position_page = _prop_ctrls.Category(self.nb, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        visible_page = _prop_ctrls.Category(self.nb, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

        terminal_page = _prop_ctrls.Category(self.nb, 'Terminal')

        from . import pjt_terminal as _pjt_terminal  # NOQA

        self.terminal_ctrl = _pjt_terminal.PJTTerminalControl(terminal_page)

        terminal_page.addWidget(self.terminal_ctrl)

        seal_page = _prop_ctrls.Category(self.nb, 'Seal')

        from . import pjt_seal as _pjt_seal  # NOQA

        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        seal_page.addWidget(self.seal_ctrl)

        part_page = _prop_ctrls.Category(self.nb, 'Part')
        from ..global_db import cavity as _cavity  # NOQA

        self.part_ctrl = _cavity.CavityControl(part_page)

        part_page.addWidget(self.part_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            terminal_page,
            seal_page,
            part_page
        ):
            self.nb.addTab(page, page.GetLabel())

    def set_obj(self, db_obj: PJTCavity):
        """
        Set the obj.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTCavity`
        """
        
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
