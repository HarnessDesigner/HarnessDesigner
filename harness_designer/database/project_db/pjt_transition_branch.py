# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable, Union as _Union

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    Position3DMixin, PositionPegboardMixin, VisiblePegboardMixin, PartMixin
)
from ...ui import prop_ctrls as _prop_ctrls
from ..global_db import transition_branch as _transition_branch
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_transition as _pjt_transition
    from . import pjt_wire as _pjt_wire
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle as _pjt_bundle


class PJTTransitionBranchesTable(PJTTableBase):
    """Represent a PJT transition branches table in :mod:`harness_designer.database.project_db.pjt_transition_branch`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_transition_branches'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import transition_branches

        return transition_branches.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transition_branches

        transition_branches.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import transition_branches

        transition_branches.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTTransitionBranch"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTTransitionBranch']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTransitionBranch(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTTransitionBranch":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTransitionBranch`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTTransitionBranch or item in self:
                return PJTTransitionBranch(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, transition_id: bytes, point_id: bytes,
               branch_id: int, diameter: float) -> "PJTTransitionBranch":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the global transition branch this row represents.
        :type part_id: bytes
        :param transition_id: Identifier for the transition.
        :type transition_id: bytes
        :param point_id: Identifier for the point.
        :type point_id: bytes
        :param branch_id: Identifier for the branch.
        :type branch_id: int
        :param diameter: Value for ``diameter``.
        :type diameter: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTransitionBranch`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """

        if branch_id < 1 or branch_id > 6:
            raise RuntimeError('sanity check')

        db_id = PJTTableBase.insert(
            self, part_id=part_id, transition_id=transition_id,
            point3d_id=point_id, branch_id=branch_id, diameter=float(diameter),
            point_pegboard_id=None, table_point_peg_id=None, table_hidden=0)

        # No peg-board data table of its own (unlike housing/bundle/
        # transition) -- a transition has ONE table, listing the wires of
        # all its branches.
        return PJTTransitionBranch(self, db_id)


class PJTTransitionBranch(PJTEntryBase, Position3DMixin, PositionPegboardMixin, PartMixin,
                          VisiblePegboardMixin):
    """Represent a PJT transition branch in :mod:`harness_designer.database.project_db.pjt_transition_branch`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTTransitionBranchesTable = None

    @property
    @_check_types.do
    def table(self) -> PJTTransitionBranchesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTransitionBranchesTable`
        """
        return self._table

    @property
    @_check_types.do
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        """Every wire routed through this branch's own position, via
        ``pjt_wire_paths`` (one row per point per wire per view -- see
        that table's own docstring) -- NOT via concentric twisting.

        Concentric twisting is being redesigned (not every harness is
        concentric-twisted), so a transition branch carries no attachment
        to it at all any more -- ``pjt_wire_paths`` is the new, general
        "which wires pass through this point" mechanism, and works
        whether or not this branch (or its transition) is part of any
        concentric grouping.

        :returns: Every distinct wire with a route row tagged
            ``transition_branch_id=self.db_id``, across every view.
        :rtype: list[:class:`_pjt_wire.PJTWire`]
        """
        rows = self.table.db.pjt_wire_paths_table.for_transition_branch(self.db_id)

        seen = set()
        res = []
        for row in rows:
            wire = row.wire
            if wire.db_id not in seen:
                seen.add(wire.db_id)
                res.append(wire)

        return res

    @property
    @_check_types.do
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        """Return the bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_bundle.PJTBundle`
        """
        position_id = self.position3d_id
        bundles_table = self.table.db.pjt_bundles_table

        # A brand-new branch (nothing attached yet) has no bundle row
        # referencing its position at all -- the previous version of
        # this indexed [0][0] straight into the (possibly empty)
        # row list, crashing with IndexError, and its own fallback
        # confused "a list of rows" with "a single id" (indexing
        # [0][0] into a bytes id on the way out, which would itself
        # have failed the moment this branch actually got a bundle).
        rows = bundles_table.select('id', start_point3d_id=position_id)
        if not rows:
            rows = bundles_table.select('id', stop_point3d_id=position_id)

        if rows:
            return bundles_table[rows[0][0]]

    @property
    @_check_types.do
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        """Return the concentric.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_concentric.PJTConcentric`
        """
        rows = self.table.db.pjt_concentrics_table.select('id', transition_branch_id=self.db_id)
        # A plain transition branch has no pjt_concentrics row at all
        # any more (see .wires, which no longer needs one either) --
        # an empty result means "not concentric-twisted", not an
        # error, so this no longer indexes [0] blindly.
        if rows:
            return self.table.db.pjt_concentrics_table[rows[0][0]]

    @property
    @_check_types.do
    def transition(self) -> "_pjt_transition.PJTTransition":
        """Return the transition.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition.PJTTransition`
        """
        return self._table.db.pjt_transitions_table[self.transition_id]

    @property
    @_check_types.do
    def transition_id(self) -> bytes:
        """Return the transition ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        return self._table.select('transition_id', id=self._db_id)[0][0]

    @transition_id.setter
    @_check_types.do
    def transition_id(self, value: bytes) -> None:
        """Set the transition ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._table.update(self._db_id, transition_id=value)
        self._populate('transition_id')

    @property
    @_check_types.do
    def branch_id(self) -> int:
        """Return the branch ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('branch_id', id=self._db_id)[0][0]

    @branch_id.setter
    @_check_types.do
    def branch_id(self, value: int) -> None:
        """Set the branch ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, branch_id=value)
        self._populate('branch_id')

    @property
    @_check_types.do
    def diameter(self) -> float:
        """Return the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('diameter', id=self._db_id)[0][0]

    @diameter.setter
    @_check_types.do
    def diameter(self, value: float) -> None:
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, diameter=value)
        self._populate('diameter')

    _stored_part: _transition_branch.TransitionBranch | DefaultStoredValueType = DefaultStoredValue

    @_check_types.do
    def reload_from_db(self) -> None:
        """Execute the reload from database operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.transition.update_objects()

    @property
    @_check_types.do
    def part(self) -> _transition_branch.TransitionBranch:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_transition_branch.TransitionBranch`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id
            self._stored_part = self._table.db.global_db.transition_branches_table[part_id]
            self._stored_part.add_object(self)

        return self._stored_part

    @property
    @_check_types.do
    def propgrid(self) -> tuple[_prop_ctrls.Category, _prop_ctrls.Category]:
        """Return the propgrid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: tuple[_prop_ctrls.Category, _prop_ctrls.Category]
        """
        group = _prop_ctrls.Category('Project')

        position_prop = self._position3d_propgrid
        diameter_prop = _prop_ctrls.FloatProperty('Diameter', 'diameter', self.diameter,
                                                  min_value=0.01, max_value=99.99, increment=0.01, units='mm')

        group.Append(diameter_prop)
        group.Append(position_prop)

        part_prop = self._part_propgrid

        return group, part_prop
