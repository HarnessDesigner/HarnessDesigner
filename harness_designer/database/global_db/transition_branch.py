from typing import Iterable as _Iterable, TYPE_CHECKING

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import NameMixin

from ...geometry import point as _point

if TYPE_CHECKING:
    from . import transition as _transition
    from . import bundle_cover as _bundle_cover


class TransitionBranchesTable(TableBase):
    __table_name__ = 'transition_branches'

    def _table_needs_update(self) -> bool:
        from ..create_database import transition_branches

        return transition_branches.table.is_ok(self)

    def _add_table_to_db(self, _):
        from ..create_database import transition_branches

        transition_branches.table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import transition_branches

        transition_branches.table.update_fields(self)

    def __iter__(self) -> _Iterable["TransitionBranch"]:
        for db_id in TableBase.__iter__(self):
            yield TransitionBranch(self, db_id)

    def __getitem__(self, item) -> "TransitionBranch":
        if isinstance(item, int):
            if item in self:
                return TransitionBranch(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, transition_id: int, idx: int, name: int, bulb_offset: _point.Point | None,
               bulb_length: float | None, min_dia: float, max_dia: float, length: float,
               angle: float, offset: _point.Point | None, flange_height: float | None,
               flange_width: float | None) -> "TransitionBranch":

        db_id = TableBase.insert(self, transition_id=transition_id, idx=idx, name=name,
                                 bulb_offset=bulb_offset, bulb_length=bulb_length,
                                 min_dia=min_dia, max_dia=max_dia,
                                 length=length, angle=angle, offset=offset,
                                 flange_height=flange_height, flange_width=flange_width)

        return TransitionBranch(self, db_id)


class TransitionBranch(EntryBase, NameMixin):
    _table: TransitionBranchesTable = None

    def build_monitor_packet(self):
        packet = {
            'transition_branches': [self.db_id],
            'transitions': [self.transition_id]
        }

        return packet

    @property
    def transition(self) -> "_transition.Transition":
        from .transition import Transition

        tran_id = self.transition_id

        return Transition(self._table.db.transitions_table, tran_id)

    @property
    def transition_id(self) -> int:
        return self._table.select('tran_id', id=self._db_id)[0][0]

    @property
    def idx(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        self._table.update(self._db_id, idx=value)

    @property
    def bulb_offset(self) -> _point.Point:
        offset = self._table.select('bulb_offset', id=self._db_id)[0][0]
        if offset is None:
            return _point.Point(0.0, 0.0)

        offset = eval(offset)

        return _point.Point(offset[0], offset[1], 0)

    @bulb_offset.setter
    def bulb_offset(self, value: _point.Point):
        self._table.update(self._db_id, bulb_offset=str(list(value.as_float)))

    @property
    def bulb_length(self) -> float:
        length = self._table.select('bulb_length', id=self._db_id)[0][0]

        if length is None:
            return 0.0

        return length

    @bulb_length.setter
    def bulb_length(self, value: float):
        self._table.update(self._db_id, bulb_length=value)

    @property
    def compat_bundle_covers(self) -> list["_bundle_cover.BundleCover"]:
        min_dia = self.min_dia
        max_dia = self.max_dia

        res = []

        for bundle_cover in self._table.db.bundle_covers_table:
            if bundle_cover.min_size < max_dia and bundle_cover.max_size > min_dia:
                res.append(bundle_cover)

        return res

    @property
    def min_dia(self) -> float:
        min_dia = self._table.select('min_dia', id=self._db_id)[0][0]
        return min_dia

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)

    @property
    def max_dia(self) -> float:
        max_dia = self._table.select('max_dia', id=self._db_id)[0][0]
        return max_dia

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, max_dia=value)

    @property
    def length(self) -> float:
        length = self._table.select('length', id=self._db_id)[0][0]
        return length

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)

    @property
    def angle(self) -> float:
        angle = self._table.select('angle', id=self._db_id)[0][0]
        return angle

    @angle.setter
    def angle(self, value: float):
        self._table.update(self._db_id, angle=float(value))

    @property
    def offset(self) -> _point.Point:
        offset = self._table.select('offset', id=self._db_id)[0][0]
        if offset is None:
            return None

        offset = eval(offset)

        return _point.Point(offset[0], offset[1], 0)

    @offset.setter
    def offset(self, value: _point.Point):
        self._table.update(self._db_id, offset=str(list(value.as_float)))

    @property
    def flange_height(self) -> float:
        flange_height = self._table.select('flange_height', id=self._db_id)[0][0]
        return flange_height

    @flange_height.setter
    def flange_height(self, value: float):
        self._table.update(self._db_id, flange_height=value)

    @property
    def flange_width(self) -> float:
        flange_width = self._table.select('flange_width', id=self._db_id)[0][0]
        return flange_width

    @flange_width.setter
    def flange_width(self, value: float):
        self._table.update(self._db_id, flange_width=value)

    @property
    def propgrid(self) -> _prop_grid.Property:

        branch_prop = _prop_grid.Property(f'Branch {self.idx}')

        bulb_prop = _prop_grid.Property(f'Bulb')

        bulb_offset = self.bulb_offset

        bulb_offset_prop = _prop_grid.Property('Offset', 'bulb_offset')

        x = _prop_grid.FloatProperty(
            'X', 'x', bulb_offset.x,
            min_value=-999.9, max_value=999.9, increment=0.01, units='mm')

        y = _prop_grid.FloatProperty(
            'Y', 'y', bulb_offset.y,
            min_value=-999.9, max_value=999.9, increment=0.01, units='mm')

        bulb_offset_prop.Append(x)
        bulb_offset_prop.Append(y)

        bulb_length_prop = _prop_grid.FloatProperty(
            'Length', 'bulb_length', self.bulb_length,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        bulb_prop.Append(bulb_offset_prop)
        bulb_prop.Append(bulb_length_prop)

        size_prop = _prop_grid.Property(f'Size (diameter)')

        min_dia_prop = _prop_grid.FloatProperty(
            'Minimum', 'min_dia', self.min_dia,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        max_dia_prop = _prop_grid.FloatProperty(
            'Maximum', 'max_dia', self.max_dia,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        size_prop.Append(min_dia_prop)
        size_prop.Append(max_dia_prop)

        length_prop = _prop_grid.FloatProperty(
            'Length', 'length', self.length,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        angle_prop = _prop_grid.FloatProperty(
            'Angle', 'angle', self.angle, min_value=-180.0,
            max_value=180.0, increment=0.1, units='°')

        flange_prop = _prop_grid.Property(f'Flange')

        flange_height_prop = _prop_grid.FloatProperty(
            'Flange Height', 'flange_height', self.flange_height,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        flange_width_prop = _prop_grid.FloatProperty(
            'Flange Width', 'flange_width', self.flange_width,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        flange_prop.Append(flange_height_prop)
        flange_prop.Append(flange_width_prop)
        offset = self.offset

        offset_prop = _prop_grid.Property('Offset', 'offset')

        x = _prop_grid.FloatProperty(
            'X', 'x', offset.x,
            min_value=-999.9, max_value=999.9, increment=0.01, units='mm')

        y = _prop_grid.FloatProperty(
            'Y', 'y', offset.y,
            min_value=-999.9, max_value=999.9, increment=0.01, units='mm')

        offset_prop.Append(x)
        offset_prop.Append(y)

        branch_prop.Append(offset_prop)
        branch_prop.Append(length_prop)
        branch_prop.Append(size_prop)
        branch_prop.Append(angle_prop)
        branch_prop.Append(bulb_prop)
        branch_prop.Append(flange_prop)

        return branch_prop
