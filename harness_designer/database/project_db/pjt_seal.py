# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import seal as _seal
from .pjt_bases import PJTEntryBase, PJTTableBase
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


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from . import pjt_terminal as _pjt_terminal
    from ...objects import seal as _seal_obj


class PJTSealsTable(PJTTableBase):
    """Represent a PJT seals table in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_seals'

    _control: "PJTSealControl" = None

    @property
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
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTSealControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import seals

        return seals.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seals

        seals.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import seals

        seals.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTSeal"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTSeal']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSeal(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTSeal":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSeal`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTSeal(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d_id: int, housing_id: int | None,
               terminal_id: int | None, cavity_id: int = None) -> "PJTSeal":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int
        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: int
        :param housing_id: Identifier for the housing.
        :type housing_id: int | None
        :param terminal_id: Identifier for the terminal.
        :type terminal_id: int | None
        :param cavity_id: Identifier for the cavity.
        :type cavity_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSeal`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, point3d_id=position3d_id,
                                    housing_id=housing_id, terminal_id=terminal_id,
                                    cavity_id=cavity_id)

        return PJTSeal(self, db_id, self.project_id)


class PJTSeal(PJTEntryBase, Angle3DMixin, Position3DMixin, NotesMixin, Scale3DMixin,
              PartMixin, HousingMixin, Visible3DMixin, NameMixin, SmoothMixin):
    """Represent a PJT seal in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTSealsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        housing = self.housing
        terminal = self.terminal
        cavity = self.cavity

        packet = {
            'pjt_seal': [self.db_id],
            'cavities': [self.part_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        if housing is not None:
            self.merge_packet_data(housing.build_monitor_packet(), packet)
        if terminal is not None:
            self.merge_packet_data(terminal.build_monitor_packet(), packet)
        if cavity is not None:
            self.merge_packet_data(cavity.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_seal_obj.Seal":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_seal_obj.Seal`
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

    def set_object(self, obj: "_seal_obj.Seal"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal_obj.Seal`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTSealsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSealsTable`
        """
        return self._table

    _stored_part: "_seal.Seal" = None

    @property
    def part(self) -> "_seal.Seal":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_seal.Seal`
        """
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.seals_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    _stored_terminal: "_pjt_terminal.PJTTerminal" = None

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        """Return the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_terminal.PJTTerminal`
        """
        if self._stored_terminal is None and self._obj is not None:
            db_id = self.terminal_id

            if db_id is None:
                return None

            self._stored_terminal = self._table.db.pjt_terminals_table[db_id]
            self._stored_terminal.add_object(self._obj())

        return self._stored_terminal

    @property
    def terminal_id(self) -> int:
        """Return the terminal ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('terminal_id', id=self._db_id)[0][0]

    @terminal_id.setter
    def terminal_id(self, value: int):
        """Set the terminal ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, terminal_id=value)
        self._populate('terminal_id')

    _stored_cavity: "_pjt_cavity.PJTCavity" = None

    @property
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
    def cavity_id(self) -> int:
        """Return the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('cavity_id', id=self._db_id)[0][0]

    @cavity_id.setter
    def cavity_id(self, value: int):
        """Set the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, cavity_id=value)
        self._populate('cavity_id')


class PJTSealControl(QTabWidget, LazyTabMixin):
    """Represent a PJT seal control in :mod:`harness_designer.database.project_db.pjt_seal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTSeal):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTSeal`
        """
        self._lazy_set_obj(db_obj)

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
            self.seal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTSealControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTSeal = None

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
