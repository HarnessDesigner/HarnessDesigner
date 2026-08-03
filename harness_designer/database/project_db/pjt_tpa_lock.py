# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ..global_db import tpa_lock as _tpa_lock
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Position3DMixin, Position3DControl,
    PartMixin,
    HousingMixin,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl,
    Scale3DMixin, Scale3DControl
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...objects import tpa_lock as _tpa_lock_obj


class PJTTPALocksTable(PJTTableBase):
    """Represent a pjttpa locks table in :mod:`harness_designer.database.project_db.pjt_tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_tpa_locks'

    _control: "PJTTPALockControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTTPALockControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTPALockControl`
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
        cls._control = PJTTPALockControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import tpa_locks

        return tpa_locks.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import tpa_locks

        tpa_locks.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import tpa_locks

        tpa_locks.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTTPALock"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTTPALock']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTPALock(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTTPALock":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTPALock`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in self:
                return PJTTPALock(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, position3d_id: bytes, idx: int, housing_id: bytes = None) -> "PJTTPALock":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: bytes
        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: bytes
        :param housing_id: Identifier for the housing.
        :type housing_id: bytes
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTPALock`
        """
        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name, point3d_id=position3d_id, housing_id=housing_id, idx=idx)

        return PJTTPALock(self, db_id)


class PJTTPALock(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin, Scale3DMixin,
                 HousingMixin, Visible3DMixin, NameMixin, NotesMixin, SmoothMixin):
    """Represent a pjttpa lock in :mod:`harness_designer.database.project_db.pjt_tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTTPALocksTable = None

    @_check_types.do
    def get_object(self) -> "_tpa_lock_obj.TPALock":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_tpa_lock_obj.TPALock`
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
    def set_object(self, obj: "_tpa_lock_obj.TPALock"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock_obj.TPALock`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    _stored_idx: int | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def idx(self) -> int:
        """Return the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_idx is DefaultStoredValue:
            self._stored_idx = self._table.select('idx', id=self._db_id)[0][0]

        return self._stored_idx

    @idx.setter
    @_check_types.do
    def idx(self, value: int):
        """Set the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_idx = value
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    @_check_types.do
    def table(self) -> PJTTPALocksTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTPALocksTable`
        """
        return self._table

    _stored_part: "_tpa_lock.TPALock | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def part(self) -> _tpa_lock.TPALock:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_tpa_lock.TPALock`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id

            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.cpa_locks_table[part_id]

        if self._stored_part is not None:
            if self._obj is not None:
                self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTTPALockControl(QTabWidget, LazyTabMixin):
    """Represent a pjttpa lock control in :mod:`harness_designer.database.project_db.pjt_tpa_lock`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTTPALock):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTTPALock`
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
            self.tpa_lock_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`PJTTPALockControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTTPALock = None

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
        self.tpa_lock_ctrl = _tpa_lock.TPALockControl(part_page)

        part_page.addWidget(self.tpa_lock_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
