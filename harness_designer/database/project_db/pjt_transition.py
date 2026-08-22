# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import numpy as np
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import transition as _transition
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import pjt_point3d as _pjt_point3d
from . import pjt_point_pegboard as _pjt_point_pegboard
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Position3DMixin, Position3DControl,
    PositionPegboardMixin,
    AnglePegboardMixin,
    PartMixin,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin,
    SmoothMixin, SmoothControl
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branch
    from ...objects import transition as _transition_obj


class PJTTransitionsTable(PJTTableBase):
    """Represent a PJT transitions table in :mod:`harness_designer.database.project_db.pjt_transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_transitions'

    _control: "PJTTransitionControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTTransitionControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTTransitionControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import transitions

        return transitions.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transitions

        transitions.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transitions

        transitions.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTTransition"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTTransition']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTransition(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTTransition":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTransition`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTTransition or item in self:
                return PJTTransition(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, center_id: bytes, angle: _angle.Angle) -> "PJTTransition":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: bytes
        :param center_id: Identifier for the center.
        :type center_id: bytes
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        :param name: Name value.
        :type name: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTransition`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, name=name, point3d_id=center_id,
                                    quat3d=str(list(angle.as_quat_float)),
                                    angle3d=str(list(angle.as_euler_float)))

        return PJTTransition(self, db_id)


class PJTTransition(PJTEntryBase, Angle3DMixin, Position3DMixin, PositionPegboardMixin,
                    AnglePegboardMixin, PartMixin,
                    NameMixin, Visible3DMixin, VisiblePegboardMixin, NotesMixin, SmoothMixin):
    """Represent a PJT transition in :mod:`harness_designer.database.project_db.pjt_transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTTransitionsTable = None

    @_check_types.do
    def get_object(self) -> "_transition_obj.Transition":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_transition_obj.Transition`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_transition_obj.Transition"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition_obj.Transition`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def table(self) -> PJTTransitionsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionsTable`
        """
        return self._table

    @property
    @_check_types.do
    def branches(self) -> list["_pjt_transition_branch.PJTTransitionBranch"]:
        """Every non-``None`` branch (``branch1``..``branch6``) --
        shared by :meth:`_update_position3d`/:meth:`_update_angle3d`/
        :meth:`_update_position_pegboard`/:meth:`_update_angle_pegboard`
        to gather what needs to move/rotate along with the transition.
        """
        return [b for b in (self.branch1, self.branch2, self.branch3,
                            self.branch4, self.branch5, self.branch6) if b is not None]

    _o_position3d: _point.Point = None

    @property
    @_check_types.do
    def position3d(self) -> _point.Point:
        """Return the position 3D.

        Overrides :meth:`Position3DMixin.position3d` to additionally bind
        :meth:`_update_position3d` -- the base mixin has no cascade hook of
        its own (see ``mixins.position3d``), so a batch-cascading move
        needs this override, same as ``PJTHousing.position3d``.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position3d is DefaultStoredValue:
            point_id = self.position3d_id

            if point_id is None:
                self._stored_position3d = None
            else:
                self._stored_position3d = self._table.db.pjt_points3d_table[point_id]

                point = self._stored_position3d.point
                point.bind(self._update_position3d)
                self._o_position3d = point.copy()

        if self._stored_position3d is not None:
            if self._obj is not None:
                self._stored_position3d.add_object(self._obj())

            point = self._stored_position3d.point
        else:
            point = None

        return point

    @_check_types.do
    def _update_position3d(self, point: _point.Point):
        """Batch-cascade the transition's move to every branch's own
        ``position3d`` -- up to 6 branches (``branch1``..``branch6``).

        A branch's ``position3d`` row is not a clone of anything -- the
        bundle attached to a branch, and every wire inside that bundle,
        share this exact ``pjt_points3d`` row directly (``bundle_db.
        start_position3d_id = branch.position3d_id``, see
        ``handlers.transition_handler._insert_bundle``), so moving the
        branch's row here via one batch write is all that's needed for
        the bundle/wires to follow too -- no separate gathering, no
        ``parent_point_id`` clone lookup (unlike ``PJTHousing``'s
        terminal/wire cascade), since branches have no clone mechanism.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        delta = point - self._o_position3d
        self._o_position3d = point.copy()

        positions = [b.position3d for b in self.branches]

        if not positions:
            return

        positions_array = np.array([pos.as_float for pos in positions], dtype=np.float32)
        new_pos_arr = positions_array + delta

        db_ids = [p.db_id[:-2] for p in positions]
        f_position_array = [[float(str(axis)) for axis in pt] for pt in new_pos_arr]
        rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]

        self._table.db.pjt_points3d_table.batch_update(['x', 'y', 'z'], rows)

        # The DB row for each branch point was already batch-written above
        # in one shot -- suppress PJTPoint3D's own per-point DB write while
        # applying the same values to the live Point (still need
        # _process_callbacks() to fire so rendering/geometry recompute).
        _pjt_point3d.PJTPoint3D._skip_db_write = True
        try:
            for i, pos in enumerate(positions):
                with pos:
                    pos.x = f_position_array[i][0]
                    pos.y = f_position_array[i][1]
                    pos.z = f_position_array[i][2]

                pos._process_callbacks()  # NOQA
        finally:
            _pjt_point3d.PJTPoint3D._skip_db_write = False

    _o_position_pegboard: _point.Point = None

    @property
    @_check_types.do
    def position_pegboard(self) -> _point.Point:
        """Return the peg-board position.

        Overrides :meth:`PositionPegboardMixin.position_pegboard` to
        additionally bind :meth:`_update_position_pegboard` -- see
        :meth:`position3d`'s own docstring for why.

        :returns: Property value.
        :rtype: :class:`_point.Point`
        """
        if self._stored_position_pegboard is DefaultStoredValue:
            point_id = self.position_pegboard_id

            if point_id is None:
                self._stored_position_pegboard = None
            else:
                self._stored_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

                point = self._stored_position_pegboard.point
                point.bind(self._update_position_pegboard)
                self._o_position_pegboard = point.copy()

        if self._stored_position_pegboard is not None:
            if self._obj is not None:
                self._stored_position_pegboard.add_object(self._obj())

            point = self._stored_position_pegboard.point
        else:
            point = None

        return point

    @_check_types.do
    def _update_position_pegboard(self, point: _point.Point):
        """Peg-board equivalent of :meth:`_update_position3d` -- see its
        docstring for the full rationale (identical, minus the 3D/
        peg-board table swap).

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
        delta = point - self._o_position_pegboard
        self._o_position_pegboard = point.copy()

        positions = [b.position_pegboard for b in self.branches]

        if not positions:
            return

        positions_array = np.array([pos.as_float for pos in positions], dtype=np.float32)
        new_pos_arr = positions_array + delta

        db_ids = [p.db_id[:-8] for p in positions]
        f_position_array = [[float(str(axis)) for axis in pt] for pt in new_pos_arr]
        rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]

        self._table.db.pjt_points_pegboard_table.batch_update(['x', 'y', 'z'], rows)

        _pjt_point_pegboard.PJTPointPegboard._skip_db_write = True
        try:
            for i, pos in enumerate(positions):
                with pos:
                    pos.x = f_position_array[i][0]
                    pos.y = f_position_array[i][1]
                    pos.z = f_position_array[i][2]

                pos._process_callbacks()  # NOQA
        finally:
            _pjt_point_pegboard.PJTPointPegboard._skip_db_write = False

    _o_quat3d: list = None
    _o_euler3d: list = None

    @_check_types.do
    def _update_angle3d(self, angle: _angle.Angle):
        """Batch-cascade the transition's rotation to every branch's
        ``position3d`` -- same row-sharing rationale as
        :meth:`_update_position3d`. Branches have no angle of their own
        (no ``Angle3DMixin`` on ``PJTTransitionBranch`` -- a branch's own
        orientation is derived geometrically from its position relative
        to the transition center by ``objects_3d.transition.
        _build_model``), so only positions rotate here -- no per-branch
        OBB face-alignment step (mirrors ``PJTHousing.
        _update_angle_pegboard``'s own no-mesh fallback path, since a
        transition has no accessory mesh geometry to align a branch
        against either).

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

        actual_delta_q = angle._q - o_angle._q  # NOQA
        position = self.position3d

        positions = [b.position3d for b in self.branches]

        if not positions:
            return

        w_d, x_d, y_d, z_d = actual_delta_q.as_float
        qvec_d = np.array([x_d, y_d, z_d], dtype=np.float32)
        center = position.as_numpy.copy()

        pos_arr = np.array([list(p.as_float) for p in positions], dtype=np.float32)
        rel = pos_arr - center
        t_vec = np.cross(qvec_d, rel)
        new_pos_arr = rel + 2.0 * w_d * t_vec + 2.0 * np.cross(qvec_d, t_vec) + center

        f_position_array = [[float(str(axis)) for axis in pt] for pt in new_pos_arr]
        db_ids = [p.db_id[:-2] for p in positions]
        rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]
        self._table.db.pjt_points3d_table.batch_update(['x', 'y', 'z'], rows)

        _pjt_point3d.PJTPoint3D._skip_db_write = True
        try:
            for i, pos in enumerate(positions):
                with pos:
                    pos.x = f_position_array[i][0]
                    pos.y = f_position_array[i][1]
                    pos.z = f_position_array[i][2]

                pos._process_callbacks()  # NOQA
        finally:
            _pjt_point3d.PJTPoint3D._skip_db_write = False

    _o_quat_pegboard: list = None
    _o_euler_pegboard: list = None

    @_check_types.do
    def _update_angle_pegboard(self, angle: _angle.Angle):
        """Peg-board equivalent of :meth:`_update_angle3d` -- see its
        docstring for the full rationale (identical, minus the 3D/
        peg-board table swap).

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        if self._o_quat_pegboard is None:
            self._o_quat_pegboard = eval(self._table.select('quat_pegboard', id=self._db_id)[0][0])
            self._o_euler_pegboard = eval(self._table.select('angle_pegboard', id=self._db_id)[0][0])

        o_angle = _angle.Angle.from_quat(self._o_quat_pegboard, self._o_euler_pegboard)

        new_quat = list(angle.as_quat_float)
        new_euler = list(angle.as_euler_float)
        quat = str(new_quat)
        euler = str(new_euler)

        self._table.update(self._db_id, quat_pegboard=quat, angle_pegboard=euler)

        if 'nan' in euler or 'nan' in quat:
            return

        self._o_quat_pegboard = new_quat
        self._o_euler_pegboard = new_euler

        actual_delta_q = angle._q - o_angle._q  # NOQA
        position = self.position_pegboard

        positions = [b.position_pegboard for b in self.branches]

        if not positions:
            return

        w_d, x_d, y_d, z_d = actual_delta_q.as_float
        qvec_d = np.array([x_d, y_d, z_d], dtype=np.float32)
        center = position.as_numpy.copy()

        pos_arr = np.array([list(p.as_float) for p in positions], dtype=np.float32)
        rel = pos_arr - center
        t_vec = np.cross(qvec_d, rel)
        new_pos_arr = rel + 2.0 * w_d * t_vec + 2.0 * np.cross(qvec_d, t_vec) + center

        f_position_array = [[float(str(axis)) for axis in pt] for pt in new_pos_arr]
        db_ids = [p.db_id[:-8] for p in positions]
        rows = [[*pos, db_id] for pos, db_id in zip(f_position_array, db_ids)]
        self._table.db.pjt_points_pegboard_table.batch_update(['x', 'y', 'z'], rows)

        _pjt_point_pegboard.PJTPointPegboard._skip_db_write = True
        try:
            for i, pos in enumerate(positions):
                with pos:
                    pos.x = f_position_array[i][0]
                    pos.y = f_position_array[i][1]
                    pos.z = f_position_array[i][2]

                pos._process_callbacks()  # NOQA
        finally:
            _pjt_point_pegboard.PJTPointPegboard._skip_db_write = False

    _stored_branch1: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch1(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 1.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch1 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=1)

            if not db_ids:
                self._stored_branch1 = None
            else:
                self._stored_branch1 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch1

    _stored_branch2: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch2(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch2 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=2)

            if not db_ids:
                self._stored_branch2 = None
            else:
                self._stored_branch2 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch2

    _stored_branch3: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch3(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 3.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch3 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=3)

            if not db_ids:
                self._stored_branch3 = None
            else:
                self._stored_branch3 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch3

    _stored_branch4: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch4(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 4.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch4 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=4)

            if not db_ids:
                self._stored_branch4 = None
            else:
                self._stored_branch4 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch4

    _stored_branch5: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch5(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 5.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch5 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=5)

            if not db_ids:
                self._stored_branch5 = None
            else:
                self._stored_branch5 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch5

    _stored_branch6: "_pjt_transition_branch.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def branch6(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 6.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        if self._stored_branch6 is DefaultStoredValue:
            db_ids = self.table.db.pjt_transition_branches_table.select(
                'id', transition_id=self.db_id, branch_id=6)

            if not db_ids:
                self._stored_branch6 = None
            else:
                self._stored_branch6 = self.table.db.pjt_transition_branches_table[db_ids[0][0]]

        return self._stored_branch6

    _stored_part: "_transition.Transition | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def part(self) -> _transition.Transition:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_transition.Transition`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id

            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.transitions_table[part_id]

        if self._stored_part is not None:
            if self._obj is not None:
                self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTTransitionControl(QTabWidget, LazyTabMixin):
    """Represent a PJT transition control in :mod:`harness_designer.database.project_db.pjt_transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTTransition | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTTransition`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle3d_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.transition_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`PJTTransitionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTTransition | None = None

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

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle3d_ctrl = Angle3DControl(angle_page)

        angle_page.addWidget(self.angle3d_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position3d_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible3d_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.transition_ctrl = _transition.TransitionControl(part_page)

        part_page.addWidget(self.transition_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
