# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import transition as _transition
from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import angle as _angle
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Position3DMixin, Position3DControl,
    PartMixin,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    Visible3DMixin, Visible3DControl,
    SmoothMixin, SmoothControl
)


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
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTTransitionControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import transitions

        return transitions.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transitions

        transitions.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transitions

        transitions.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTTransition"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTTransition']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTransition(self, db_id, self.project_id)

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
        if isinstance(item, int):
            if item in self:
                return PJTTransition(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, center_id: int, angle: _angle.Angle, name: str) -> "PJTTransition":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int
        :param center_id: Identifier for the center.
        :type center_id: int
        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        :param name: Name value.
        :type name: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTransition`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, center_id=center_id,
                                    angle=str(list(angle.as_euler_float)), name=name)

        return PJTTransition(self, db_id, self.project_id)


class PJTTransition(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
                    NameMixin, Visible3DMixin, NotesMixin, SmoothMixin):
    """Represent a PJT transition in :mod:`harness_designer.database.project_db.pjt_transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTTransitionsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        packet = {
            'pjt_transitions': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        for branch in (
            self.branch1,
            self.branch2,
            self.branch3,
            self.branch4,
            self.branch5,
            self.branch6
        ):
            if branch is None:
                continue

            self.merge_packet_data(branch.build_monitor_packet(), packet)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_transition_obj.Transition":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_transition_obj.Transition`
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
    def table(self) -> PJTTransitionsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionsTable`
        """
        return self._table

    @property
    def branch1(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 1.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=1)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch2(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 2.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=2)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch3(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 3.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=3)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch4(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 4.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=4)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch5(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 5.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=5)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch6(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        """Return the branch 6.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branch.PJTTransitionBranch`
        """
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=6)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    _stored_part: "_transition.Transition" = None

    @property
    def part(self) -> "_transition.Transition":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_transition.Transition`
        """
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.transitions_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTTransitionControl(QTabWidget, LazyTabMixin):
    """Represent a PJT transition control in :mod:`harness_designer.database.project_db.pjt_transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTTransition):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTTransition`
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
            self.transition_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTTransitionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTTransition = None

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
