# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import seal as _seal
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Position3DMixin, Position3DControl,
    PositionPegboardMixin, PositionPegboardControl,
    AnglePegboardMixin, AnglePegboardControl,
    VisiblePegboardMixin,
    PartMixin,
    HousingMixin,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl,
    Scale3DMixin, Scale3DControl,
    ScalePegboardMixin, ScalePegboardControl
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_terminal as _pjt_terminal
    from ...objects import seal as _seal_obj
    from ... import ui as _ui


class PJTSealsTable(PJTTableBase):
    """Represent a PJT seals table in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_seals'

    _control: "PJTSealControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTSealControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSealControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe: "_ui.MainFrame") -> None:
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTSealControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import seals

        return seals.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seals

        seals.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seals

        seals.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTSeal"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTSeal']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSeal(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTSeal":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSeal`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTSeal or item in self:
                return PJTSeal(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, position3d_id: bytes, housing_id: bytes | None,
               terminal_id: bytes | None, cavity_id: bytes = None) -> "PJTSeal":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: bytes
        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: bytes
        :param housing_id: Identifier for the housing.
        :type housing_id: bytes | None
        :param terminal_id: Identifier for the terminal.
        :type terminal_id: bytes | None
        :param cavity_id: Identifier for the cavity.
        :type cavity_id: bytes
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSeal`
        """

        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name, point3d_id=position3d_id,
            housing_id=housing_id, terminal_id=terminal_id, cavity_id=cavity_id,
            scale3d_id=None, scale_pegboard_id=None, point_pegboard_id=None, notes='',
            quat3d='[1.0, 0.0, 0.0, 0.0]', angle3d='[0.0, 0.0, 0.0]',
            quat_pegboard='[1.0, 0.0, 0.0, 0.0]', angle_pegboard='[0.0, 0.0, 0.0]',
            is_visible3d=1, is_visible_pegboard=1, smooth=None)

        seal = PJTSeal(self, db_id)

        return seal


class PJTSeal(PJTEntryBase, Angle3DMixin, Position3DMixin, PositionPegboardMixin,
              AnglePegboardMixin, VisiblePegboardMixin, NotesMixin, Scale3DMixin,
              ScalePegboardMixin, PartMixin, HousingMixin, Visible3DMixin, NameMixin,
              SmoothMixin):
    """Represent a PJT seal in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTSealsTable = None

    @_check_types.do
    def delete(self) -> None:
        """Delete this seal.

        ``PJTCavity.seal`` has no local cache to clear any more -- it
        always reads straight through -- so nothing further is needed
        once the row itself is gone.
        """
        PJTEntryBase.delete(self)

    @_check_types.do
    def get_object(self) -> "_seal_obj.Seal":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_seal_obj.Seal`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_seal_obj.Seal") -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal_obj.Seal`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def table(self) -> PJTSealsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSealsTable`
        """
        return self._table

    _stored_part: _seal.Seal | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def part(self) -> _seal.Seal:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_seal.Seal`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id

            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.seals_table[part_id]
            
        if self._stored_part is not None:
            if self._obj is not None:
                self._stored_part.add_object(self._obj())
                
        return self._stored_part

    @property
    @_check_types.do
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        """Return the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_terminal.PJTTerminal`
        """
        terminal_id = self.terminal_id
        if terminal_id is not None:
            return self._table.db.pjt_terminals_table[terminal_id]

    @property
    @_check_types.do
    def terminal_id(self) -> bytes:
        """Return the terminal ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        return self._table.select('terminal_id', id=self._db_id)[0][0]

    @terminal_id.setter
    @_check_types.do
    def terminal_id(self, value: bytes) -> None:
        """Set the terminal ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._table.update(self._db_id, terminal_id=value)
        self._populate('terminal_id')

    _stored_cavity: "_pjt_cavity.PJTCavity" = None

    @property
    @_check_types.do
    def cavity(self) -> "_pjt_cavity.PJTCavity":
        """Return the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cavity.PJTCavity`
        """
        if self._stored_cavity is None and self._obj is not None:
            db_id = self.cavity_id

            if db_id is None:
                return None

            self._stored_cavity = self._table.db.pjt_cavities_table[db_id]
            self._stored_cavity.add_object(self._obj())

        return self._stored_cavity

    @property
    @_check_types.do
    def cavity_id(self) -> bytes:
        """Return the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        return self._table.select('cavity_id', id=self._db_id)[0][0]

    @cavity_id.setter
    @_check_types.do
    def cavity_id(self, value: bytes) -> None:
        """Set the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._table.update(self._db_id, cavity_id=value)
        self._populate('cavity_id')


class PJTSealControl(QtWidgets.QTabWidget, LazyTabMixin):
    """Represent a PJT seal control in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTSeal | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTSeal`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle3d_ctrl.set_obj(self.db_obj)
            self.angle_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position3d_ctrl.set_obj(self.db_obj)
            self.position_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.seal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """Initialise the :class:`PJTSealControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTSeal | None = None

        QtWidgets.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
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
        self.angle_pegboard_ctrl = AnglePegboardControl(angle_page)

        angle_page.addWidget(self.angle3d_ctrl)

        angle_page.addWidget(self.angle_pegboard_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position3d_ctrl = Position3DControl(position_page)
        self.position_pegboard_ctrl = PositionPegboardControl(position_page)

        position_page.addWidget(self.position3d_ctrl)

        position_page.addWidget(self.position_pegboard_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible3d_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')

        from ..global_db import seal as _seal  # NOQA

        self.seal_ctrl = _seal.SealControl(part_page)

        part_page.addWidget(self.seal_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
