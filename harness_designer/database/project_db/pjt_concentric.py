# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import NotesMixin
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branches
    from . import pjt_concentric_layer as _pjt_concentric_layer
    from . import pjt_bundle as _pjt_bundle
    from ...objects import boot as _boot_obj


class PJTConcentricsTable(PJTTableBase):
    """Represent a PJT concentrics table in :mod:`harness_designer.database.project_db.pjt_concentric`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_concentrics'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import concentrics

        return concentrics.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentrics

        concentrics.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentrics

        concentrics.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTConcentric"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTConcentric']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentric(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTConcentric":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentric`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in self:
                return PJTConcentric(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, bundle_id: bytes | None, transition_branch_id: bytes | None) -> "PJTConcentric":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param bundle_id: Identifier for the bundle.
        :type bundle_id: bytes | None
        :param transition_branch_id: Identifier for the transition branch.
        :type transition_branch_id: bytes | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentric`
        """

        db_id = PJTTableBase.insert(self, bundle_id=bundle_id, transition_branch_id=transition_branch_id)

        return PJTConcentric(self, db_id)


class PJTConcentric(PJTEntryBase, NotesMixin):
    """Represent a PJT concentric in :mod:`harness_designer.database.project_db.pjt_concentric`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTConcentricsTable = None

    # def get_object(self) -> "_boot_obj.Boot":
    #     if self._obj is not None:
    #         return self._obj()
    #
    #     return self._obj
    #
    # def __release_obj_ref(self, _):
    #     self._obj = None
    #
    # def set_object(self, obj: "_boot_obj.Boot"):
    #     if obj is not None:
    #         self._obj = weakref.ref(obj, self.__release_obj_ref)
    #     else:
    #         self._obj = obj

    @property
    @_check_types.do
    def layers(self) -> list["_pjt_concentric_layer.PJTConcentricLayer"]:
        """Return the layers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_concentric_layer.PJTConcentricLayer']
        """
        layers = []

        db_ids = self.table.db.pjt_concentric_layers_table.select("id", concentric_id=self.db_id)
        for db_id in db_ids:
            layers.append(self.table.db.pjt_concentric_layers_table[db_id[0]])

        return sorted(layers, key=lambda x: x.idx)

    @property
    @_check_types.do
    def table(self) -> PJTConcentricsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricsTable`
        """
        return self._table

    _stored_bundle: "_pjt_bundle.PJTBundle | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        """Return the bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_bundle.PJTBundle`
        """
        if self._stored_bundle is DefaultStoredValue:
            bundle_id = self.bundle_id
            if bundle_id is None:
                self._stored_bundle = None
            else:
                self._stored_bundle = self._table.db.pjt_bundles_table[bundle_id]

        return self._stored_bundle

    _stored_bundle_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def bundle_id(self) -> bytes:
        """Return the bundle ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        if self._stored_bundle_id is DefaultStoredValue:
            self._stored_bundle_id = self._table.select('bundle_id', id=self._db_id)[0][0]

        return self._stored_bundle_id

    @bundle_id.setter
    @_check_types.do
    def bundle_id(self, value: bytes):
        """Set the bundle ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_bundle_id = value
        self._stored_bundle = DefaultStoredValue

        self._table.update(self._db_id, bundle_id=value)
        self._populate('bundle_id')

    _stored_transition_branch: "_pjt_transition_branches.PJTTransitionBranch | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def transition_branch(self) -> "_pjt_transition_branches.PJTTransitionBranch":
        """Return the transition branch.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_transition_branches.PJTTransitionBranch`
        """
        if self._stored_transition_branch is DefaultStoredValue:
            transition_branch_id = self.transition_branch_id
            if transition_branch_id is None:
                self._stored_transition_branch = None
            else:
                self._stored_transition_branch = self._table.db.pjt_transition_branches_table[transition_branch_id]

        return self._stored_transition_branch

    _stored_transition_branch_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def transition_branch_id(self) -> bytes:
        """Return the transition branch ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        if self._stored_transition_branch_id is DefaultStoredValue:
            self._stored_transition_branch_id = self._table.select('transition_branch_id', id=self._db_id)[0][0]

        return self._stored_transition_branch_id

    @transition_branch_id.setter
    @_check_types.do
    def transition_branch_id(self, value: bytes):
        """Set the transition branch ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_transition_branch_id = value
        self._stored_transition_branch = DefaultStoredValue

        self._table.update(self._db_id, transition_branch_id=value)
        self._populate('transition_branch_id')

    @property
    @_check_types.do
    def propgrid(self) -> _prop_ctrls.Category:
        """Return the propgrid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_prop_ctrls.Category`
        """
        group = _prop_ctrls.Category('Concentric')

        notes_prop = self._notes_propgrid

        group.Append(notes_prop)
        layers_group = _prop_ctrls.Property('Layers')

        for layer in self.layers:
            layers_group.Append(layer.propgrid)

        if self.transition_branch is not None:
            t_group, t_part_prop = self.transition_branch.propgrid
            attach_group = _prop_ctrls.Property('Transition Branch')
            project_group = _prop_ctrls.Property('Project')
            part_group = _prop_ctrls.Property('Part')

            for child in t_group._children:  # NOQA
                project_group.Append(child)

            for child in t_part_prop._children:  # NOQA
                part_group.Append(child)

            attach_group.Append(project_group)
            attach_group.Append(part_group)

            group.Append(attach_group)

        if self.bundle is not None:
            b_group, b_part_prop = self.bundle.propgrid
            attach_group = _prop_ctrls.Property('Bundle')
            project_group = _prop_ctrls.Property('Project')
            part_group = _prop_ctrls.Property('Part')

            for child in b_group._children:  # NOQA
                project_group.Append(child)

            for child in b_part_prop._children:  # NOQA
                part_group.Append(child)

            attach_group.Append(project_group)
            attach_group.Append(part_group)

            group.Append(attach_group)

        return group
