from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from wx import propgrid as wxpg

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import Position3DMixin, Visible3DMixin, NotesMixin

if TYPE_CHECKING:
    from . import pjt_bundle as _pjt_bundle

    from ...objects import bundle_layout as _bundle_layout_obj


class PJTBundleLayoutsTable(PJTTableBase):
    __table_name__ = 'pjt_bundle_layouts'

    def get_from_position3d_id(self, position3d_id) -> "PJTBundleLayout":
        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

    def _table_needs_update(self) -> bool:
        from ..create_database import bundle_cover_layouts

        return bundle_cover_layouts.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTBundleLayout"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundleLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundleLayout":
        if isinstance(item, int):
            if item in self:
                return PJTBundleLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, coord_id: int, diameter: float) -> "PJTBundleLayout":
        db_id = PJTTableBase.insert(self, coord_id=coord_id, diameter=diameter)

        return PJTBundleLayout(self, db_id, self.project_id)


class PJTBundleLayout(PJTEntryBase, Position3DMixin, Visible3DMixin, NotesMixin):
    _table: PJTBundleLayoutsTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_bundle_layouts': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }
        return packet

    def get_object(self) -> "_bundle_layout_obj.BundleLayout":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_bundle_layout_obj.BundleLayout"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def attached_bundles(self) -> list["_pjt_bundle.PJTBundle"]:
        res = []
        point_id = self.position3d_id
        db_ids = self._table.db.pjt_bundles_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)

        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTBundleLayoutsTable:
        return self._table

    @property
    def diameter(self) -> float:
        return self._table.select('diameter', id=self._db_id)[0][0]

    @diameter.setter
    def diameter(self, value: float):
        self._table.update(self._db_id, diameter=value)
        self._process_callbacks()

    @property
    def propgrid(self) -> wxpg.PGProperty:
        group = wxpg.PropertyCategory('Project')

        notes_prop = self._notes_propgrid
        position_prop = self._position3d_propgrid
        visible_prop = self._visible3d_propgrid

        group.AppendChild(notes_prop)
        group.AppendChild(position_prop)
        group.AppendChild(visible_prop)

        return group
