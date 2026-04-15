from typing import TYPE_CHECKING, Iterable as _Iterable

import wx
import numpy as np
import weakref

from ...ui.editor_obj import prop_grid as _prop_grid
from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point
from ...geometry import angle as _angle

from . import pjt_cover as _pjt_cover
from . import pjt_tpa_lock as _pjt_tpa_lock
from . import pjt_cpa_lock as _pjt_cpa_lock
from . import pjt_seal as _pjt_seal
from . import pjt_boot as _pjt_boot

from ..global_db import housing as _housing

from .mixins import (
    NameMixin, NameControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NotesMixin, NotesControl,
    Position2DMixin, Position2DControl,
    Position3DMixin, Position3DControl,
    Angle2DMixin, Angle2DControl,
    Angle3DMixin, Angle3DControl
)


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_accessory as _pjt_accessory
    from . import pjt_point3d as _pjt_point3d

    from ..global_db import housing as _housing

    from ...objects import housing as _housing_obj


class PJTHousingsTable(PJTTableBase):
    __table_name__ = 'pjt_housings'

    _control: "PJTHousingControl" = None

    @property
    def control(self) -> "PJTHousingControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTHousingControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import housings

        return housings.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import housings

        housings.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import housings

        housings.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTHousing"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTHousing(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTHousing":
        if isinstance(item, int):
            if item in self:
                return PJTHousing(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d: "_point.Point" = None,
               position2d: "_point.Point" = None) -> "PJTHousing":

        if position2d is None:
            position2d = _point.Point(0, 0)

        if position3d is None:
            position3d = _point.Point(0.0, 0.0, 0.0)

        x, y = position2d.as_float[:-1]
        pos2d = self.db.pjt_points2d_table.insert(x, y)

        x, y, z = position3d.as_float
        pos3d = self.db.pjt_points3d_table.insert(x, y, z)

        db_id = PJTTableBase.insert(self, point3d_id=pos3d.db_id,
                                    point2d_id=pos2d.db_id, part_id=part_id)

        db_obj = PJTHousing(self, db_id, self.project_id)

        pos3d = pos3d.point
        pos2d = pos2d.point

        # add the cavities from the part to the project
        for cavity in db_obj.part.cavities:
            if cavity is None:
                continue

            pjt_cavity = self.db.pjt_cavities_table.insert(cavity.db_id, db_id)
            cpos3d = pjt_cavity.position3d
            cpos2d = pjt_cavity.position2d

            cpos3d += pos3d
            cpos2d += pos2d

            pjt_cavity.name = cavity.name

        pos = db_obj.cover_position3d
        pos += pos3d

        pos = db_obj.seal_position3d
        pos += pos3d

        pos = db_obj.boot_position3d
        pos += pos3d

        pos = db_obj.tpa_lock_1_position3d
        pos += pos3d

        pos = db_obj.tpa_lock_2_position3d
        pos += pos3d

        pos = db_obj.cpa_lock_position3d
        pos += pos3d

        return db_obj


class PJTHousing(PJTEntryBase, NameMixin, PartMixin, Position2DMixin, Position3DMixin,
                 Visible3DMixin, Visible2DMixin, NotesMixin, Angle2DMixin, Angle3DMixin):

    _table: PJTHousingsTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_housings': [self.db_id],
            'housings': [self.part_id],
            'pjt_points3d': [self.position3d_id, self.cover_position3d_id,
                             self.seal_position3d_id, self.boot_position3d_id,
                             self.tpa_lock_1_position3d_id, self.tpa_lock_2_position3d_id,
                             self.cpa_lock_position3d_id],
            'pjt_points2d': [self.position2d_id],

        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_housing_obj.Housing":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_housing_obj.Housing"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTHousingsTable:
        return self._table

    @property
    def cavities(self) -> list["_pjt_cavity.PJTCavity"]:
        cavities = []

        cavity_ids = self._table.db.pjt_cavities_table.select(
            'id', housing_id=self._db_id)

        for cavity_id in cavity_ids:
            cavity = self._table.db.pjt_cavities_table[cavity_id[0]]

            cavities.append(cavity)

        return cavities

    _stored_cover_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def cover_position3d(self) -> "_point.Point":
        if self._stored_cover_position3d is None and self._obj is not None:
            point_id = self.cover_position3d_id

            self._stored_cover_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_cover_position3d.add_object(self._obj())

        return self._stored_cover_position3d.point

    @property
    def cover_position3d_id(self) -> int:
        point_id = self._table.select('cover_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.cover_position3d_id = point_id

        return point_id

    @cover_position3d_id.setter
    def cover_position3d_id(self, value: int):
        self._table.update(self._db_id, cover_point3d_id=value)

    _stored_seal_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def seal_position3d(self) -> "_point.Point":
        if self._stored_seal_position3d is None and self._obj is not None:

            point_id = self.seal_position3d_id

            self._stored_seal_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_seal_position3d.add_object(self._obj())

        return self._stored_seal_position3d.point

    @property
    def seal_position3d_id(self) -> int:
        point_id = self._table.select('seal_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.seal_position3d_id = point_id

        return point_id

    @seal_position3d_id.setter
    def seal_position3d_id(self, value: int):
        self._table.update(self._db_id, seal_point3d_id=value)

    _stored_boot_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def boot_position3d(self) -> "_point.Point":
        if self._stored_boot_position3d is None and self._obj is not None:

            point_id = self.boot_position3d_id

            self._stored_boot_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_boot_position3d.add_object(self._obj())

        return self._stored_boot_position3d.point

    @property
    def boot_position3d_id(self) -> int:
        point_id = self._table.select('boot_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.boot_position3d_id = point_id

        return point_id

    @boot_position3d_id.setter
    def boot_position3d_id(self, value: int):
        self._table.update(self._db_id, boot_point3d_id=value)

    _stored_tpa_lock_1_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def tpa_lock_1_position3d(self) -> "_point.Point":
        if self._stored_tpa_lock_1_position3d is None and self._obj is not None:

            point_id = self.tpa_lock_1_position3d_id

            self._stored_tpa_lock_1_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_tpa_lock_1_position3d.add_object(self._obj())

        return self._stored_tpa_lock_1_position3d.point

    @property
    def tpa_lock_1_position3d_id(self) -> int:
        point_id = self._table.select('tpa_lock_1_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.tpa_lock_1_position3d_id = point_id

        return point_id

    @tpa_lock_1_position3d_id.setter
    def tpa_lock_1_position3d_id(self, value: int):
        self._table.update(self._db_id, tpa_lock_1_point3d_id=value)

    _stored_tpa_lock_2_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def tpa_lock_2_position3d(self) -> "_point.Point":
        if self._stored_tpa_lock_2_position3d is None and self._obj is not None:

            point_id = self.tpa_lock_2_position3d_id

            self._stored_tpa_lock_2_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_tpa_lock_2_position3d.add_object(self._obj())

        return self._stored_tpa_lock_2_position3d.point

    @property
    def tpa_lock_2_position3d_id(self) -> int:
        point_id = self._table.select('tpa_lock_2_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.tpa_lock_2_position3d_id = point_id

        return point_id

    @tpa_lock_2_position3d_id.setter
    def tpa_lock_2_position3d_id(self, value: int):
        self._table.update(self._db_id, tpa_lock_2_point3d_id=value)

    _stored_cpa_lock_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def cpa_lock_position3d(self) -> "_point.Point":
        if self._stored_cpa_lock_position3d is None and self._obj is not None:

            point_id = self.cpa_lock_position3d_id

            self._stored_cpa_lock_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_cpa_lock_position3d.add_object(self._obj())

        return self._stored_cpa_lock_position3d.point

    @property
    def cpa_lock_position3d_id(self) -> int:
        point_id = self._table.select('cpa_lock_point3d_id',
                                      id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(
                0.0, 0.0, 0.0).db_id

            self.cpa_lock_position3d_id = point_id

        return point_id

    @cpa_lock_position3d_id.setter
    def cpa_lock_position3d_id(self, value: int):
        self._table.update(self._db_id, cpa_lock_point3d_id=value)

    def add_cavity(self, index, name):
        cavities = self.cavities
        assert cavities[index] is None, 'Sanity Check'

        part = self.part
        cavity_part = part.cavities[index]

        if name is None:
            name = cavity_part.name

        cavity = self._table.db.pjt_cavities_table.insert(cavity_part.db_id,
                                                          self.db_id)

        cavity.name = name

        self._process_callbacks()
        return cavity

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        db_ids = self._table.db.pjt_seals_table.select('id',
                                                       housing_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    def cpa_lock(self) -> "_pjt_cpa_lock.PJTCPALock":
        db_ids = self._table.db.pjt_cpa_locks_table.select('id',
                                                           housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cpa_lock = self._table.db.pjt_cpa_locks_table[db_id[0]]
            except IndexError:
                continue

            return cpa_lock

    @property
    def tpa_lock1(self) -> "_pjt_tpa_lock.PJTTPALock":
        rows = self._table.db.pjt_tpa_locks_table.select(
            'id', housing_id=self.db_id, idx=1)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    def tpa_lock2(self) -> "_pjt_tpa_lock.PJTTPALock":
        rows = self._table.db.pjt_tpa_locks_table.select(
            'id', housing_id=self.db_id, idx=2)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    def tpa_locks(self) -> list["_pjt_tpa_lock.PJTTPALock"]:
        res = []
        db_ids = self._table.db.pjt_tpa_locks_table.select('id',
                                                           housing_id=self.db_id)

        for db_id in db_ids:
            try:
                tpa_lock = self._table.db.pjt_tpa_locks_table[db_id[0]]
            except IndexError:
                continue

            res.append(tpa_lock)
        return res

    @property
    def cover(self) -> "_pjt_cover.PJTCover":
        db_ids = self._table.db.pjt_covers_table.select('id',
                                                        housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cover = self._table.db.pjt_covers_table[db_id[0]]
            except IndexError:
                continue

            return cover

    @property
    def boot(self) -> "_pjt_boot.PJTBoot":
        db_ids = self._table.db.pjt_boots_table.select('id',
                                                       housing_id=self.db_id)

        for db_id in db_ids:
            try:
                boot = self._table.db.pjt_boots_table[db_id[0]]
            except IndexError:
                continue

            return boot

    # @property
    # def accessories(self) -> list["_pjt_accessory.PJTAccessory"]:
    #     res = []
    #     db_ids = self._table.db.pjt_accessories_table.select('id',
    #                                                          housing_id=self.db_id)
    #
    #     for db_id in db_ids:
    #         try:
    #             accessory = self._table.db.pjt_accessories_table[db_id]
    #         except IndexError:
    #             continue
    #
    #         res.append(accessory)
    #     return res

    _stored_part: "_housing.Housing" = None

    @property
    def part(self) -> "_housing.Housing":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.housings_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    def _update_position3d(self, point: _point.Point):

        # when the position of a housing is changed all of the objects that
        # attach to the housing also need to change. That update should happen
        # in a location where the points for those accessory items change even if
        # there is no accessory attached to them. The positions of the accessories
        # are set in the housing editor dialog and those positions are calculated
        # with the housing center positioned at (0, 0, 0). This makes updating the
        # the positions easier to do because we simply calculate the difference
        # between the old housing position and the new position and apply that
        # difference to each of the accessory points.

        delta = point - self._o_position3d
        self._o_position3d = point.copy()

        for cavity in self.cavities:
            if cavity is None:
                continue

            c_position = cavity.position3d
            c_position += delta

        pos = self.cover_position3d
        pos += delta

        pos = self.seal_position3d
        pos += delta

        pos = self.boot_position3d
        pos += delta

        pos = self.tpa_lock_1_position3d
        pos += delta

        pos = self.tpa_lock_2_position3d
        pos += delta

        pos = self.cpa_lock_position3d
        pos += delta

    _o_position3d: "_point.Point" = None

    @property
    def position3d(self) -> "_point.Point":
        if self._stored_position3d is None and self._obj is not None:
            point_id = self.position3d_id

            self._stored_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_position3d.add_object(self._obj())

            point = self._stored_position3d.point
            point.bind(self._update_position3d)
            self._o_position3d = point.copy()

        elif self._stored_position3d is None:
            point = None
        else:
            point = self._stored_position3d.point

        return point

    def _update_position2d(self, point: _point.Point):
        delta = point - self._o_position2d
        self._o_position2d = point.copy()

        for cavity in self.cavities:
            if cavity is None:
                continue

            c_position = cavity.position2d
            c_position += delta

    _o_position2d: "_point.Point" = None

    @property
    def position2d(self) -> "_point.Point":
        if self._stored_position2d is None and self._obj is not None:

            point_id = self.position2d_id

            self._stored_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_position2d.add_object(self._obj())

            point = self._stored_position2d.point
            point.bind(self._update_position2d)
            self._o_position2d = point.copy()

        elif self._stored_position2d is None:
            print('This should not be happening')
            point = None
        else:
            point = self._stored_position2d.point

        return point

    def _update_angle3d(self, angle: _angle.Angle):
        quat = eval(self._table.select('quat3d',
                                       id=self._db_id)[0][0])

        euler_angle = eval(self._table.select('angle3d',
                                              id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(quat, euler_angle)

        delta = angle - o_angle

        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat3d=str(quat))
        self._table.update(self._db_id, angle3d=str(euler_angle))

        cavities = [c for c in self.cavities if c is not None]
        if cavities:
            housing_pos = self.position3d.as_numpy

            # Get all cavity centers: shape (N, 3)
            centers = np.array(
                [cavity.position3d.as_numpy for cavity in cavities],
                dtype=np.float64)

            # Create reference offset vector for all cavities
            reference_vector = np.array([0.0, 0.0, 10.0], dtype=np.float64)

            # Rotate reference vector by each cavity's current angle to get offset
            # Then add to centers to get reference points
            offsets = np.array(
                [cavity.angle3d @ reference_vector for cavity in cavities],
                dtype=np.float64)

            references = centers + offsets

            # Stack centers and references: shape (N*2, 3)
            all_points = np.empty((len(cavities) * 2, 3), dtype=np.float64)
            all_points[0::2] = centers      # Even indices: centers
            all_points[1::2] = references   # Odd indices: references

            # Vectorized transformation
            all_points -= housing_pos
            all_points @= delta
            all_points += housing_pos

            # Extract and update
            for i, cavity in enumerate(cavities):
                rotated_center = all_points[i * 2]
                rotated_reference = all_points[i * 2 + 1]

                # Update position
                c_position = cavity.position3d
                c_position.x = float(rotated_center[0])
                c_position.y = float(rotated_center[1])
                c_position.z = float(rotated_center[2])

                # Calculate new angle
                new_cavity_angle = _angle.Angle.from_points(
                    _point.Point(*rotated_center),
                    _point.Point(*rotated_reference)
                )

                c_angle = cavity.angle3d
                angle_delta = new_cavity_angle - c_angle
                c_angle += angle_delta

        position = self.position3d
        cover_pos = self.cover_position3d
        cpa_pos = self.cpa_lock_position3d
        tpa1_pos = self.tpa_lock_1_position3d
        tpa2_pos = self.tpa_lock_2_position3d
        seal_pos = self.seal_position3d
        boot_pos = self.boot_position3d

        objs = [self.tpa_lock1, self.tpa_lock2,
                self.cover, self.cpa_lock, self.boot, self.seal]

        objs = zip(objs, [tpa1_pos, tpa2_pos, cover_pos,
                          cpa_pos, boot_pos, seal_pos])

        reference_vector = _point.Point(0.0, 0.0, 10.0)

        for obj, pos in objs:
            if obj is not None:
                reference_point = reference_vector @ obj.angle3d
                reference_point += pos

                reference_point -= position
                new_pos = pos - position
                reference_point @= delta
                new_pos @= delta
                reference_point += position
                new_pos += position

                new_angle = _angle.Angle.from_points(new_pos, reference_point)

                obj_angle = obj.angle3d
                angle_delta = new_angle - obj_angle
                obj_angle += angle_delta
            else:
                new_pos = pos - position
                new_pos @= delta
                new_pos += position

            pos_delta = new_pos - pos
            pos += pos_delta

    def _update_angle2d(self, angle: _angle.Angle):
        quat = list(angle.as_quat_float)
        euler_angle = list(angle.as_euler_float)

        self._table.update(self._db_id, quat2d=str(quat))
        self._table.update(self._db_id, angle2d=str(euler_angle))


class PJTHousingControl(wx.Notebook):

    def set_obj(self, db_obj: PJTHousing):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)

        self.visible3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)

        self.angle2d_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)

        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)

        self.cover_ctrl.set_obj(db_obj.cover)
        self.boot_ctrl.set_obj(db_obj.boot)
        self.cpa_lock_ctrl.set_obj(db_obj.cpa_lock)
        self.tpa_lock1_ctrl.set_obj(db_obj.tpa_lock1)
        self.tpa_lock2_ctrl.set_obj(db_obj.tpa_lock2)
        self.seal_ctrl.set_obj(db_obj.seal)
        self.part_ctrl.set_obj(db_obj.part)

        for i in range(self.cavities_notebook.GetPageCount()):
            self.cavities_notebook.RemovePage(i)

        for page in self.cavity_pages:
            page.Reparent(db_obj.table.db.mainframe)
            page.Show(False)

        self.cavity_pages = []

        for i, cavity in enumerate(db_obj.cavities):
            if cavity is None:
                continue

            ctrl = db_obj.table.db.pjt_cavities_table.get_control(i)
            ctrl.Reparent(self.cavities_notebook)
            self.cavities_notebook.AddPage(ctrl, ctrl.GetLabel())
            ctrl.set_obj(cavity)
            self.cavity_pages.append(ctrl)

    def __init__(self, parent):
        self.db_obj: PJTHousing = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        angle_page = _prop_grid.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        cavities_page = _prop_grid.Category(self, 'Cavities')
        self.cavities_notebook = wx.Notebook(cavities_page, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)
        self.cavity_pages = []

        cover_page = _prop_grid.Category(self, 'Cover')
        self.cover_ctrl = _pjt_cover.PJTCoverControl(cover_page)

        boot_page = _prop_grid.Category(self, 'Boot')
        self.boot_ctrl = _pjt_boot.PJTBootControl(boot_page)

        cpa_lock_page = _prop_grid.Category(self, 'CPA Lock')
        self.cpa_lock_ctrl = _pjt_cpa_lock.PJTCPALockControl(cpa_lock_page)

        tpa_lock1_page = _prop_grid.Category(self, 'TPA Lock 1')
        self.tpa_lock1_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock1_page)

        tpa_lock2_page = _prop_grid.Category(self, 'TPA Lock 2')
        self.tpa_lock2_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock2_page)

        seal_page = _prop_grid.Category(self, 'Seal')
        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.part_ctrl = _housing.HousingControl(part_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            cover_page,
            boot_page,
            cpa_lock_page,
            tpa_lock1_page,
            tpa_lock2_page,
            seal_page,
            cavities_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
