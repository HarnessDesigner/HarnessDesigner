
from typing import TYPE_CHECKING, Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import NotesMixin


if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branches
    from . import pjt_concentric_layer as _pjt_concentric_layer

    from . import pjt_bundle as _pjt_bundle

    from ...objects import boot as _boot_obj


class PJTConcentricsTable(PJTTableBase):
    __table_name__ = 'pjt_concentrics'

    def _table_needs_update(self) -> bool:
        from ..create_database import concentrics

        return concentrics.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import concentrics

        concentrics.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import concentrics

        concentrics.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTConcentric"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentric(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentric":
        if isinstance(item, int):
            if item in self:
                return PJTConcentric(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, bundle_id: int | None, transition_branch_id: int | None) -> "PJTConcentric":

        db_id = PJTTableBase.insert(self, bundle_id=bundle_id, transition_branch_id=transition_branch_id)

        return PJTConcentric(self, db_id, self.project_id)


class PJTConcentric(PJTEntryBase, NotesMixin):
    _table: PJTConcentricsTable = None

    def build_monitor_packet(self):
        bundle = self.bundle
        transition_branch = self.transition_branch

        packet = {
            'pjt_concentrics': [self.db_id],
        }

        if bundle is not None:
            packet['pjt_bundles'] = [bundle.db_id]

        if transition_branch is not None:
            packet['pjt_transition_branches'] = [transition_branch.db_id]

        if bundle is not None:
            self.merge_packet_data(bundle.build_monitor_packet(), packet)
        if transition_branch is not None:
            self.merge_packet_data(transition_branch.build_monitor_packet(), packet)

        return packet

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
    def layers(self) -> list["_pjt_concentric_layer.PJTConcentricLayer"]:
        layers = []

        db_ids = self.table.db.pjt_concentric_layers_table.select("id", concentric_id=self.db_id)
        for db_id in db_ids:
            layers.append(self.table.db.pjt_concentric_layers_table[db_id[0]])

        return sorted(layers, key=lambda x: x.index)

    @property
    def table(self) -> PJTConcentricsTable:
        return self._table

    @property
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        bundle_id = self.bundle_id
        if bundle_id is None:
            return None

        return self._table.db.pjt_bundles_table[bundle_id]

    @property
    def bundle_id(self) -> int:
        return self._table.select('bundle_id', id=self._db_id)[0][0]

    @bundle_id.setter
    def bundle_id(self, value: int):
        self._table.update(self._db_id, bundle_id=value)
        self._populate('bundle_id')

    @property
    def transition_branch(self) -> "_pjt_transition_branches.PJTTransitionBranch":
        transition_branch_id = self.transition_branch_id
        if transition_branch_id is None:
            return None

        return self._table.db.pjt_transition_branches_table[transition_branch_id]

    @property
    def transition_branch_id(self) -> int:
        return self._table.select('transition_branch_id', id=self._db_id)[0][0]

    @transition_branch_id.setter
    def transition_branch_id(self, value: int):
        self._table.update(self._db_id, transition_branch_id=value)
        self._populate('transition_branch_id')

    @property
    def propgrid(self) -> _prop_grid.Category:
        group = _prop_grid.Category('Concentric')

        notes_prop = self._notes_propgrid

        group.Append(notes_prop)
        layers_group = _prop_grid.Property('Layers')

        for layer in self.layers:
            layers_group.Append(layer.propgrid)

        if self.transition_branch is not None:
            t_group, t_part_prop = self.transition_branch.propgrid
            attach_group = _prop_grid.Property('Transition Branch')
            project_group = _prop_grid.Property('Project')
            part_group = _prop_grid.Property('Part')

            for child in t_group._children:
                project_group.Append(child)

            for child in t_part_prop._children:
                part_group.Append(child)

            attach_group.Append(project_group)
            attach_group.Append(part_group)

            group.Append(attach_group)

        if self.bundle is not None:
            b_group, b_part_prop = self.bundle.propgrid
            attach_group = _prop_grid.Property('Bundle')
            project_group = _prop_grid.Property('Project')
            part_group = _prop_grid.Property('Part')

            for child in b_group._children:
                project_group.Append(child)

            for child in b_part_prop._children:
                part_group.Append(child)

            attach_group.Append(project_group)
            attach_group.Append(part_group)

            group.Append(attach_group)

        return group
