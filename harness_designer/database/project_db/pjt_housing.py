# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import math

import numpy as np
import weakref
from PySide6.QtWidgets import QTabWidget, QWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import pjt_cover as _pjt_cover
from . import pjt_tpa_lock as _pjt_tpa_lock
from . import pjt_cpa_lock as _pjt_cpa_lock
from . import pjt_seal as _pjt_seal
from . import pjt_boot as _pjt_boot
from . import pjt_cavity as _pjt_cavity
from . import pjt_point3d as _pjt_point3d

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
    Angle3DMixin, Angle3DControl,
    SmoothMixin, SmoothControl,
    Scale3DMixin, Scale3DControl
)


if TYPE_CHECKING:
    # from . import pjt_accessory as _pjt_accessory
    from . import pjt_point3d as _pjt_point3d
    from ..global_db import housing as _housing
    from ...objects import housing as _housing_obj


def _obb_face_direction(
        current_obb: np.ndarray,
        local_obb: np.ndarray,
        face_idx: int) -> "np.ndarray | None":
    """Return the normalized outward normal of *face_idx* using *current_obb*.

    Face membership is determined by sorting *local_obb* corners along the
    face axis (axis 0 → faces 0/1, axis 1 → 2/3, axis 2 → 4/5).
    The same corner indices are then read from *current_obb* (fully rotated).
    """
    axis = face_idx // 2
    sign = face_idx % 2
    sorted_i = np.argsort(local_obb[:, axis])
    corner_i = sorted_i[:4] if sign == 0 else sorted_i[4:]
    center = current_obb.mean(axis=0)
    fc = current_obb[corner_i].mean(axis=0) - center
    n = float(str(np.linalg.norm(fc)))

    return (fc / n) if n > 1e-8 else None


def _euler_from_matrix_continuous(
        rot_mat: np.ndarray,
        prev_euler_deg: "list[float] | None") -> list:
    """YXZ Euler decomposition matching :meth:`Quaternion.as_euler`.

    *rot_mat* columns are ``[right, up, forward]``.  Each angle is
    continuity-wrapped to stay within ±180° of the corresponding value in
    *prev_euler_deg* so the displayed values never jump.
    """
    pitch = float(np.degrees(np.arcsin(np.clip(-rot_mat[1, 2], -1.0, 1.0))))
    yaw = float(np.degrees(np.arctan2(rot_mat[0, 2], rot_mat[2, 2])))
    roll = float(np.degrees(np.arctan2(rot_mat[1, 0], rot_mat[1, 1])))
    result = [pitch, yaw, roll]

    if prev_euler_deg and not any(math.isnan(v) for v in prev_euler_deg):
        for i in range(3):
            while result[i] - prev_euler_deg[i] > 180.0:
                result[i] -= 360.0
            while result[i] - prev_euler_deg[i] < -180.0:
                result[i] += 360.0

    return result


class PJTHousingsTable(PJTTableBase):
    """Represent a PJT housings table in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_housings'

    _control: "PJTHousingControl" = None

    @property
    def control(self) -> "PJTHousingControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTHousingControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import housings

        return housings.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import housings

        housings.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import housings

        housings.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTHousing"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTHousing']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTHousing(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTHousing":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTHousing`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTHousing(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str, position3d_id: int = None,
               position2d_id: int = None) -> "PJTHousing":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int

        :param name: Name for the part.
        :type name: str

        :param position3d_id: 3D position id.
        :type position3d_id: int | None

        :param position2d_id: 2D position id.
        :type position2d_id: int | None

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTHousing`
        """

        if position2d_id is None:
            position2d_id = self.db.pjt_points2d_table.insert(0.0, 0.0).db_id

        if position3d_id is None:
            position3d_id = self.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

        db_id = PJTTableBase.insert(self, name=name, point3d_id=position3d_id,
                                    point2d_id=position2d_id, part_id=part_id)

        db_obj = PJTHousing(self, db_id, self.project_id)

        pos3d = db_obj.position3d

        # add the cavities from the part to the project
        for cavity in db_obj.part.cavities:
            if cavity is None:
                continue

            self.db.pjt_cavities_table.insert(cavity.db_id, db_id, cavity.name)

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
                 Visible3DMixin, Visible2DMixin, NotesMixin, Angle2DMixin, Angle3DMixin,
                 SmoothMixin, Scale3DMixin):
    """Represent a PJT housing in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTHousingsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
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

    def update_cavities(self):
        for cavity in self.cavities:
            if cavity is not None:
                return

        from ...objects import cavity as _cavity

        # add the cavities from the part to the project
        for cavity in self.part.cavities:
            if cavity is None:
                continue

            db_obj = self._table.db.pjt_cavities_table.insert(cavity.db_id, self.db_id, cavity.name)

            cavity = _cavity.Cavity(self._table.db.mainframe, db_obj)
            self._table.db.mainframe.project.add_cavity(cavity)

        self._stored_cavities = None

    def get_object(self) -> "_housing_obj.Housing":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_housing_obj.Housing`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    def set_object(self, obj: "_housing_obj.Housing"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing_obj.Housing`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTHousingsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTHousingsTable`
        """
        return self._table

    _stored_cavities: list = None

    @property
    def cavities(self) -> list["_pjt_cavity.PJTCavity"]:
        """Return the cavities.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_cavity.PJTCavity']
        """
        if self._stored_cavities is not None:
            return self._stored_cavities

        cavities = []

        cavity_ids = self._table.db.pjt_cavities_table.select(
            'id', housing_id=self._db_id)

        for cavity_id in cavity_ids:
            cavity = self._table.db.pjt_cavities_table[cavity_id[0]]

            cavities.append(cavity)

        self._stored_cavities = cavities
        return cavities

    _stored_cover_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def cover_position3d(self) -> "_point.Point":
        """Return the cover position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_cover_position3d is None:
            point_id = self.cover_position3d_id

            self._stored_cover_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_cover_position3d.add_object(self._obj())

        return self._stored_cover_position3d.point

    @property
    def cover_position3d_id(self) -> int:
        """Return the cover position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('cover_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.cover_position3d_id = point_id

        return point_id

    @cover_position3d_id.setter
    def cover_position3d_id(self, value: int):
        """Set the cover position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, cover_point3d_id=value)
        self._populate('cover_position3d_id')

    _stored_seal_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def seal_position3d(self) -> "_point.Point":
        """Return the seal position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_seal_position3d is None:
            point_id = self.seal_position3d_id

            if point_id is None:
                point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self._stored_seal_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_seal_position3d.add_object(self._obj())

        return self._stored_seal_position3d.point

    @property
    def seal_position3d_id(self) -> int:
        """Return the seal position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('seal_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.seal_position3d_id = point_id

        return point_id

    @seal_position3d_id.setter
    def seal_position3d_id(self, value: int):
        """Set the seal position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, seal_point3d_id=value)
        self._populate('seal_position3d_id')

    _stored_boot_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def boot_position3d(self) -> "_point.Point":
        """Return the boot position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_boot_position3d is None:
            point_id = self.boot_position3d_id

            if point_id is None:
                point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self._stored_boot_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_boot_position3d.add_object(self._obj())

        return self._stored_boot_position3d.point

    @property
    def boot_position3d_id(self) -> int:
        """Return the boot position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('boot_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.boot_position3d_id = point_id

        return point_id

    @boot_position3d_id.setter
    def boot_position3d_id(self, value: int):
        """Set the boot position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, boot_point3d_id=value)
        self._populate('boot_position3d_id')

    _stored_tpa_lock_1_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def tpa_lock_1_position3d(self) -> "_point.Point":
        """Return the TPA lock 1 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_tpa_lock_1_position3d is None:
            point_id = self.tpa_lock_1_position3d_id

            if point_id is None:
                point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self._stored_tpa_lock_1_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_tpa_lock_1_position3d.add_object(self._obj())

        return self._stored_tpa_lock_1_position3d.point

    @property
    def tpa_lock_1_position3d_id(self) -> int:
        """Return the TPA lock 1 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('tpa_lock_1_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.tpa_lock_1_position3d_id = point_id

        return point_id

    @tpa_lock_1_position3d_id.setter
    def tpa_lock_1_position3d_id(self, value: int):
        """Set the TPA lock 1 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, tpa_lock_1_point3d_id=value)
        self._populate('tpa_lock_1_position3d_id')

    _stored_tpa_lock_2_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def tpa_lock_2_position3d(self) -> "_point.Point":
        """Return the TPA lock 2 position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_tpa_lock_2_position3d is None:
            point_id = self.tpa_lock_2_position3d_id

            if point_id is None:
                point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self._stored_tpa_lock_2_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_tpa_lock_2_position3d.add_object(self._obj())

        return self._stored_tpa_lock_2_position3d.point

    @property
    def tpa_lock_2_position3d_id(self) -> int:
        """Return the TPA lock 2 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('tpa_lock_2_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.tpa_lock_2_position3d_id = point_id

        return point_id

    @tpa_lock_2_position3d_id.setter
    def tpa_lock_2_position3d_id(self, value: int):
        """Set the TPA lock 2 position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, tpa_lock_2_point3d_id=value)
        self._populate('tpa_lock_2_position3d_id')

    _stored_cpa_lock_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def cpa_lock_position3d(self) -> "_point.Point":
        """Return the CPA lock position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_cpa_lock_position3d is None:
            point_id = self.cpa_lock_position3d_id

            if point_id is None:
                point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self._stored_cpa_lock_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._obj is not None:
            self._stored_cpa_lock_position3d.add_object(self._obj())

        return self._stored_cpa_lock_position3d.point

    @property
    def cpa_lock_position3d_id(self) -> int:
        """Return the CPA lock position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('cpa_lock_point3d_id', id=self._db_id)[0][0]

        if point_id is None:
            point_id = self._table.db.pjt_points3d_table.insert(0.0, 0.0, 0.0).db_id

            self.cpa_lock_position3d_id = point_id

        return point_id

    @cpa_lock_position3d_id.setter
    def cpa_lock_position3d_id(self, value: int):
        """Set the CPA lock position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, cpa_lock_point3d_id=value)
        self._populate('cpa_lock_position3d_id')

    def add_cavity(self, index, name):
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :param name: Name value.
        :type name: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        cavities = self.cavities
        assert cavities[index] is None, 'Sanity Check'

        part = self.part
        cavity_part = part.cavities[index]

        if name is None:
            name = cavity_part.name

        cavity = self._table.db.pjt_cavities_table.insert(cavity_part.db_id, self.db_id)

        cavity.name = name
        self._stored_cavities = None
        return cavity

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        """Return the seal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_seal.PJTSeal`
        """
        db_ids = self._table.db.pjt_seals_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    def cpa_lock(self) -> "_pjt_cpa_lock.PJTCPALock":
        """Return the CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cpa_lock.PJTCPALock`
        """
        db_ids = self._table.db.pjt_cpa_locks_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cpa_lock = self._table.db.pjt_cpa_locks_table[db_id[0]]
            except IndexError:
                continue

            return cpa_lock

    @property
    def tpa_lock1(self) -> "_pjt_tpa_lock.PJTTPALock":
        """Return the TPA lock 1.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_tpa_lock.PJTTPALock`
        """
        rows = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id, idx=1)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    def tpa_lock2(self) -> "_pjt_tpa_lock.PJTTPALock":
        """Return the TPA lock 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_tpa_lock.PJTTPALock`
        """
        rows = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id, idx=2)

        if rows:
            db_id = rows[0][0]
            return self._table.db.pjt_tpa_locks_table[db_id]

    @property
    def tpa_locks(self) -> list["_pjt_tpa_lock.PJTTPALock"]:
        """Return the TPA locks.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_tpa_lock.PJTTPALock']
        """
        res = []
        db_ids = self._table.db.pjt_tpa_locks_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                tpa_lock = self._table.db.pjt_tpa_locks_table[db_id[0]]
            except IndexError:
                continue

            res.append(tpa_lock)
        return res

    @property
    def cover(self) -> "_pjt_cover.PJTCover":
        """Return the cover.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cover.PJTCover`
        """
        db_ids = self._table.db.pjt_covers_table.select('id', housing_id=self.db_id)

        for db_id in db_ids:
            try:
                cover = self._table.db.pjt_covers_table[db_id[0]]
            except IndexError:
                continue

            return cover

    @property
    def boot(self) -> "_pjt_boot.PJTBoot":
        """Return the boot.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_boot.PJTBoot`
        """
        db_ids = self._table.db.pjt_boots_table.select('id', housing_id=self.db_id)

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
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_housing.Housing`
        """
        if self._stored_part is None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.housings_table[part_id]

        if self._obj is not None:
            self._stored_part.add_object(self._obj())

        return self._stored_part

    def _update_position3d(self, point: _point.Point):
        """Update the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """

        delta = point - self._o_position3d
        self._o_position3d = point.copy()

        cavities = [c for c in self.cavities if c is not None]

        # Cavity + accessory positions: use _skip_db_write (no seal cascade).
        cavity_positions = [cavity.position3d for cavity in cavities]

        accessory_positions = [self.cover_position3d, self.seal_position3d,
                               self.boot_position3d, self.tpa_lock_1_position3d,
                               self.tpa_lock_2_position3d, self.cpa_lock_position3d]

        # Terminal center positions: no _skip_db_write (seal cascade must reach DB).
        # Wire attachment points: stale-only, no callbacks.

        terminal_positions = []
        wire_positions = []
        for cavity in cavities:
            terminal = cavity.terminal

            if terminal is None:
                continue

            terminal_positions.append(cavity.terminal_position3d)
            terminal_positions.append(terminal.position3d)

            wp = terminal.wire_position3d
            if wp is not None:
                wire_positions.append(wp)

        all_positions = cavity_positions + accessory_positions + terminal_positions + wire_positions

        seen = {}
        for pos in all_positions:
            key = int(pos.db_id[:-2])
            if key not in seen:
                seen[key] = pos
        all_positions = list(seen.values())

        if not all_positions:
            return

        # changed the data type to a float32
        all_positions_array = np.array([pos.as_float for pos in all_positions], dtype=np.float32)

        # ONE numpy operation for all positions at once.
        # there is no need to turn the delta into a numpy array. the code
        # already exists to directly apply a Point delta directly
        # to a numpy array.

        new_pos_arr = all_positions_array + delta

        # ONE batch DB write for everything (one executemany + one commit).
        db_ids = [int(p.db_id[:-2]) for p in all_positions]

        # The row handling seen commented below is inefficient and would produce
        # incorrect values because of how the conversion from a numpy array to a
        # float array was being done.
        # rows = [
        #     (float(new_pos_arr[i, 0]), float(new_pos_arr[i, 1]), float(new_pos_arr[i, 2]), db_ids[i])
        #     for i in range(len(all_positions))
        # ]
        f_position_array = [[float(str(axis)) for axis in point] for point in new_pos_arr]

        # each row is [x, y, z, db_id] — four elements matching the four ? placeholders
        rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]

        self._table.db.pjt_points3d_table.batch_update(['x', 'y', 'z'], rows)

        # TODO: We need to handle this in a better way. We do not want to
        #       specifically stop all database updated from occuring for points
        #       because there could be other points that end up getting modified
        #       as the result of a point moving. What we need to do is access
        #       the actual point database object directly and set a marker in
        #       that instance to not update. This will allow all of the original
        #       mechanics to run properly without updating the database.
        #       for the time being I am not going to allow any updates to occur
        #       and we will mark the Point instance as stale. This way we can
        #       override the render functions in the 3d object classes that use
        #       these points so they can update their obb, aabb and any other
        #       stored data that needs to be updated at render time.
        for i, pos in enumerate(all_positions):
            pos.stale = True
            with pos:
                pos.x = f_position_array[i][0]
                pos.y = f_position_array[i][1]
                pos.z = f_position_array[i][2]

    _o_position3d: "_point.Point" = None

    @property
    def position3d(self) -> "_point.Point":
        """Return the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position3d is None:
            point_id = self.position3d_id

            self._stored_position3d = self._table.db.pjt_points3d_table[point_id]

            point = self._stored_position3d.point
            point.bind(self._update_position3d)
            self._o_position3d = point.copy()
        else:
            point = self._stored_position3d.point

        if self._obj is not None:
            self._stored_position3d.add_object(self._obj())

        return point

    def _update_position2d(self, point: _point.Point):
        """Update the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
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
        """Return the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """

        if self._stored_position2d is None:
            point_id = self.position2d_id

            self._stored_position2d = self._table.db.pjt_points2d_table[point_id]

            point = self._stored_position2d.point
            point.bind(self._update_position2d)
            self._o_position2d = point.copy()
        else:
            point = self._stored_position2d.point

        if self._obj is not None:
            self._stored_position2d.add_object(self._obj())

        return point

    _o_quat3d: list = None
    _o_euler3d: list = None

    def _update_angle3d(self, angle: _angle.Angle):
        """Update the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        if self._o_quat3d is None:
            self._o_quat3d = eval(self._table.select('quat3d', id=self._db_id)[0][0])
            self._o_euler3d = eval(self._table.select('angle3d', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(self._o_quat3d, self._o_euler3d)

        new_quat = list(angle.as_quat_float)
        new_euler = list(angle.as_euler_float)
        quat = str(new_quat)
        euler = str(new_euler)

        self._table.update(self._db_id, quat3d=quat, angle3d=euler)

        if 'nan' in euler or 'nan' in quat:
            return

        self._o_quat3d = new_quat
        self._o_euler3d = new_euler

        # Compute the true world-space rotation delta as q_new ⊗ q_old⁻¹.
        # Using the Euler-path (angle - o_angle) gives a component-wise
        # difference that is only correct when the non-rotated axes are zero.
        actual_delta_q = angle._q - o_angle._q  # NOQA
        position = self.position3d
        cavities = [c for c in self.cavities if c is not None]

        w_d, x_d, y_d, z_d = actual_delta_q.as_float
        qvec_d = np.array([x_d, y_d, z_d], dtype=np.float32)
        center = position.as_numpy.copy()

        # ── Collect all positions for one vectorized rotation ─────────────────
        all_positions = []
        for cavity in cavities:
            all_positions.append(cavity.position3d)
            terminal = cavity.terminal
            if terminal is not None:
                all_positions.append(cavity.terminal_position3d)
                all_positions.append(terminal.position3d)
                wp = terminal.wire_position3d
                if wp is not None:
                    all_positions.append(wp)

        all_positions.extend([self.tpa_lock_1_position3d, self.seal_position3d,
                              self.tpa_lock_2_position3d, self.boot_position3d,
                              self.cpa_lock_position3d, self.cover_position3d])

        seen = {}
        for pos in all_positions:
            key = int(pos.db_id[:-2])
            if key not in seen:
                seen[key] = pos

        all_positions = list(seen.values())

        if all_positions:
            pos_arr = np.array([list(p.as_float) for p in all_positions], dtype=np.float32)
            rel = pos_arr - center
            t_vec = np.cross(qvec_d, rel)
            new_pos_arr = rel + 2.0 * w_d * t_vec + 2.0 * np.cross(qvec_d, t_vec) + center

            f_position_array = [[float(str(axis)) for axis in point] for point in new_pos_arr]
            db_ids = [int(p.db_id[:-2]) for p in all_positions]
            rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]
            self._table.db.pjt_points3d_table.batch_update(['x', 'y', 'z'], rows)

            for i, pos in enumerate(all_positions):
                pos.stale = True
                with pos:
                    pos.x = f_position_array[i][0]
                    pos.y = f_position_array[i][1]
                    pos.z = f_position_array[i][2]

        # ── Per-cavity angle computation (OBB-based) ──────────────────────────
        angle_results = []  # [(cavity, q_acc_new, new_euler), ...]

        for cavity in cavities:
            cavity_angle = cavity.angle3d
            old_euler = cavity_angle.as_euler_float
            q_acc_new = cavity_angle._q + actual_delta_q  # NOQA

            new_euler = None
            part = cavity.part
            local_obb = part.obb
            q_model3d = part.angle3d._q  # NOQA
            q_obb = q_model3d + q_acc_new

            w_o, x_o, y_o, z_o = q_obb.as_float
            qvec_o = np.array([x_o, y_o, z_o], dtype=np.float32)
            t_o = np.cross(qvec_o, local_obb)
            rotated = local_obb + 2.0 * w_o * t_o + 2.0 * np.cross(qvec_o, t_o)

            fwd = _obb_face_direction(rotated, local_obb, 4)
            up = _obb_face_direction(rotated, local_obb, 3)

            if fwd is None or up is None:
                continue

            right = np.cross(up, fwd)
            right_norm = float(str(np.linalg.norm(right)))
            if right_norm > 1e-8:
                right /= right_norm
                up = np.cross(fwd, right)
                rot_mat = np.column_stack([right, up, fwd])
                new_euler = _euler_from_matrix_continuous(rot_mat, old_euler)

            if new_euler is None:
                new_euler = _euler_from_matrix_continuous(q_acc_new.as_matrix, old_euler)

            angle_results.append((cavity, q_acc_new, new_euler))

        for cav, q_acc_new, new_euler in angle_results:
            cav_angle = cav.angle3d
            with cav_angle:
                cav_angle.x = new_euler[0]
                cav_angle.y = new_euler[1]
                cav_angle.z = new_euler[2]
                cav_angle._q.w = q_acc_new.w  # NOQA
                cav_angle._q.x = q_acc_new.x  # NOQA
                cav_angle._q.y = q_acc_new.y  # NOQA
                cav_angle._q.z = q_acc_new.z  # NOQA
                cav_angle._matrix[:] = q_acc_new.as_matrix  # NOQA

        if angle_results:
            angle_rows = [(str(list(q.as_float)), str(eu), cav._db_id)
                          for cav, q, eu in angle_results]

            angle_results[0][0].table.batch_update(['quat3d', 'angle3d'], angle_rows)

        # ── Accessory angle computation (OBB-based) ───────────────────────────
        acc_objs = [self.tpa_lock1, self.seal,
                    self.tpa_lock2, self.boot,
                    self.cpa_lock, self.cover]

        acc_angle_results = []  # [(obj, q_acc_new, new_euler), ...]

        for obj in acc_objs:
            if obj is None:
                continue

            obj_angle = obj.angle3d
            old_euler = obj_angle.as_euler_float
            q_acc_new = obj_angle._q + actual_delta_q  # NOQA

            new_euler = None
            part = obj.part
            if part is not None:
                model3d = part.model3d
                if model3d is not None:
                    local_obb = model3d.obb
                    fwd_face, up_face = model3d.forward_up
                    if fwd_face == -1 or up_face == -1:
                        continue

                    q_model3d = model3d.angle3d._q  # NOQA
                    q_obb = q_model3d + q_acc_new

                    w_o, x_o, y_o, z_o = q_obb.as_float
                    qvec_o = np.array([x_o, y_o, z_o], dtype=np.float32)
                    t_o = np.cross(qvec_o, local_obb)
                    rotated = local_obb + 2.0 * w_o * t_o + 2.0 * np.cross(qvec_o, t_o)

                    fwd = _obb_face_direction(rotated, local_obb, fwd_face)
                    up = _obb_face_direction(rotated, local_obb, up_face)

                    if fwd is None or up is None:
                        continue

                    right = np.cross(up, fwd)
                    right_norm = float(str(np.linalg.norm(right)))
                    if right_norm > 1e-8:
                        right /= right_norm
                        up = np.cross(fwd, right)
                        rot_mat = np.column_stack([right, up, fwd])
                        new_euler = _euler_from_matrix_continuous(rot_mat, old_euler)

            if new_euler is None:
                new_euler = _euler_from_matrix_continuous(q_acc_new.as_matrix, old_euler)

            acc_angle_results.append((obj, q_acc_new, new_euler))

        for obj, q_acc_new, new_euler in acc_angle_results:
            obj_angle = obj.angle3d
            with obj_angle:
                obj_angle.x = new_euler[0]
                obj_angle.y = new_euler[1]
                obj_angle.z = new_euler[2]
                obj_angle._q.w = q_acc_new.w  # NOQA
                obj_angle._q.x = q_acc_new.x  # NOQA
                obj_angle._q.y = q_acc_new.y  # NOQA
                obj_angle._q.z = q_acc_new.z  # NOQA
                obj_angle._matrix[:] = q_acc_new.as_matrix  # NOQA

        if acc_angle_results:
            from collections import defaultdict as _dd
            table_angle_rows = _dd(list)
            for obj, q, eu in acc_angle_results:
                table_angle_rows[obj.table].append((str(list(q.as_float)), str(eu), obj._db_id))
            for table, rows in table_angle_rows.items():
                table.batch_update(['quat3d', 'angle3d'], rows)

        self._populate('angle3d')

    def _update_angle2d(self, angle: _angle.Angle):
        """Update the angle 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        quat = str(list(angle.as_quat_float))
        euler = str(list(angle.as_euler_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, quat2d=quat)
        self._table.update(self._db_id, angle2d=euler)
        self._populate('angle2d')


class PJTHousingControl(QTabWidget, LazyTabMixin):
    """Represent a PJT housing control in :mod:`harness_designer.database.project_db.pjt_housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTHousing):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTHousing`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle2d_ctrl.set_obj(self.db_obj)
            self.angle3d_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._cover_page:
            self.cover_ctrl.set_obj(None if self.db_obj is None else self.db_obj.cover)
        elif page is self._boot_page:
            self.boot_ctrl.set_obj(None if self.db_obj is None else self.db_obj.boot)
        elif page is self._cpa_lock_page:
            self.cpa_lock_ctrl.set_obj(None if self.db_obj is None else self.db_obj.cpa_lock)
        elif page is self._tpa_lock1_page:
            self.tpa_lock1_ctrl.set_obj(None if self.db_obj is None else self.db_obj.tpa_lock1)
        elif page is self._tpa_lock2_page:
            self.tpa_lock2_ctrl.set_obj(None if self.db_obj is None else self.db_obj.tpa_lock2)
        elif page is self._seal_page:
            self.seal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.seal)
        elif page is self._cavities_page:
            while self.cavities_notebook.count():
                self.cavities_notebook.removeTab(0)

            self.cavity_pages = {}
            self.cavity_pages_loaded = set()

            if self.db_obj is not None:
                cavities = self.db_obj.cavities
                for cavity in cavities:
                    if cavity is None:
                        continue

                    placeholder = QWidget()
                    index = self.cavities_notebook.addTab(placeholder, cavity.name)

                    self.cavity_pages[index] = cavity

            if self.cavity_pages:
                index = min(list(self.cavity_pages.keys()))

                self.cavity_pages_loaded.add(index)
                cavity = self.cavity_pages.pop(index)

                widget = _pjt_cavity.PJTCavityControl(self.cavities_notebook)
                widget.set_obj(cavity)
                name = self.cavities_notebook.tabText(index)
                self.cavities_notebook.removeTab(index)
                self.cavities_notebook.insertTab(index, widget, name)
                self.cavities_notebook.setCurrentIndex(index)

        elif page is self._part_page:
            self.part_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def _on_cavity_tab_changed(self, index: int):
        if index in self.cavity_pages_loaded or index not in self.cavity_pages:
            return

        self.cavity_pages_loaded.add(index)
        cavity = self.cavity_pages.pop(index)

        widget = _pjt_cavity.PJTCavityControl(self.cavities_notebook)
        widget.set_obj(cavity)
        name = self.cavities_notebook.tabText(index)
        self.cavities_notebook.removeTab(index)
        self.cavities_notebook.insertTab(index, widget, name)
        self.cavities_notebook.setCurrentIndex(index)

    def __init__(self, parent):
        """Initialise the :class:`PJTHousingControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTHousing = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.note_ctrl)
        general_page.addWidget(self.smooth_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        angle_page.addWidget(self.angle2d_ctrl)
        angle_page.addWidget(self.angle3d_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._cavities_page = cavities_page = _prop_ctrls.Category(self, 'Cavities')
        self.cavities_notebook = QTabWidget(cavities_page)
        self.cavities_notebook.setTabPosition(QTabWidget.TabPosition.North)
        self.cavities_notebook.setUsesScrollButtons(True)
        self.cavity_pages = {}
        self.cavity_pages_loaded = set()
        self.cavities_notebook.currentChanged.connect(self._on_cavity_tab_changed)

        cavities_page.addWidget(self.cavities_notebook)

        self._cover_page = cover_page = _prop_ctrls.Category(self, 'Cover')
        self.cover_ctrl = _pjt_cover.PJTCoverControl(cover_page)

        cover_page.addWidget(self.cover_ctrl)

        self._boot_page = boot_page = _prop_ctrls.Category(self, 'Boot')
        self.boot_ctrl = _pjt_boot.PJTBootControl(boot_page)

        boot_page.addWidget(self.boot_ctrl)

        self._cpa_lock_page = cpa_lock_page = _prop_ctrls.Category(self, 'CPA Lock')
        self.cpa_lock_ctrl = _pjt_cpa_lock.PJTCPALockControl(cpa_lock_page)

        cpa_lock_page.addWidget(self.cpa_lock_ctrl)

        self._tpa_lock1_page = tpa_lock1_page = _prop_ctrls.Category(self, 'TPA Lock 1')
        self.tpa_lock1_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock1_page)

        tpa_lock1_page.addWidget(self.tpa_lock1_ctrl)

        self._tpa_lock2_page = tpa_lock2_page = _prop_ctrls.Category(self, 'TPA Lock 2')
        self.tpa_lock2_ctrl = _pjt_tpa_lock.PJTTPALockControl(tpa_lock2_page)

        tpa_lock2_page.addWidget(self.tpa_lock2_ctrl)

        self._seal_page = seal_page = _prop_ctrls.Category(self, 'Seal')
        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        seal_page.addWidget(self.seal_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.part_ctrl = _housing.HousingControl(part_page)

        part_page.addWidget(self.part_ctrl)

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
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
