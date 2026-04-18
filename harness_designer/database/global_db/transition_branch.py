from typing import Iterable as _Iterable, TYPE_CHECKING

import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase
from .mixins import NameMixin, NameControl

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
        self._populate('idx')

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
        self._populate('bulb_offset')

    @property
    def bulb_length(self) -> float:
        length = self._table.select('bulb_length', id=self._db_id)[0][0]

        if length is None:
            return 0.0

        return length

    @bulb_length.setter
    def bulb_length(self, value: float):
        self._table.update(self._db_id, bulb_length=value)
        self._populate('bulb_length')

    @property
    def compat_bundle_covers(self) -> list["_bundle_cover.BundleCover"]:
        min_dia = self.min_dia
        max_dia = self.max_dia

        res = []

        for bundle_cover in self._table.db.bundle_covers_table:
            if bundle_cover.min_dia < max_dia and bundle_cover.max_dia > min_dia:
                res.append(bundle_cover)

        return res

    @property
    def min_dia(self) -> float:
        min_dia = self._table.select('min_dia', id=self._db_id)[0][0]
        return min_dia

    @min_dia.setter
    def min_dia(self, value: float):
        self._table.update(self._db_id, min_dia=value)
        self._populate('min_dia')

    @property
    def max_dia(self) -> float:
        max_dia = self._table.select('max_dia', id=self._db_id)[0][0]
        return max_dia

    @max_dia.setter
    def max_dia(self, value: float):
        self._table.update(self._db_id, max_dia=value)
        self._populate('max_dia')

    @property
    def length(self) -> float:
        length = self._table.select('length', id=self._db_id)[0][0]
        return length

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)
        self._populate('length')

    @property
    def angle(self) -> float:
        angle = self._table.select('angle', id=self._db_id)[0][0]
        return angle

    @angle.setter
    def angle(self, value: float):
        self._table.update(self._db_id, angle=float(value))
        self._populate('angle')

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
        self._populate('offset')

    @property
    def flange_height(self) -> float:
        flange_height = self._table.select('flange_height', id=self._db_id)[0][0]
        return flange_height

    @flange_height.setter
    def flange_height(self, value: float):
        self._table.update(self._db_id, flange_height=value)
        self._populate('flange_height')

    @property
    def flange_width(self) -> float:
        flange_width = self._table.select('flange_width', id=self._db_id)[0][0]
        return flange_width

    @flange_width.setter
    def flange_width(self, value: float):
        self._table.update(self._db_id, flange_width=value)
        self._populate('flange_width')


class TransitionBranchControl(_prop_grid.Category):

    def set_obj(self, db_obj: TransitionBranch):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.length_ctrl.SetValue(0.01)
            self.angle_ctrl.SetValue(0.0)
            self.offset_ctrl.SetValue(None)
            self.bulb_offset_ctrl.SetValue(None)
            self.bulb_length_ctrl.SetValue(0.0)
            self.min_dia_ctrl.SetValue(0.01)
            self.max_dia_ctrl.SetValue(0.01)
            self.flange_height_ctrl.SetValue(0.0)
            self.flange_width_ctrl.SetValue(0.0)

            self.length_ctrl.Enable(False)
            self.angle_ctrl.Enable(False)
            self.offset_ctrl.Enable(False)
            self.bulb_offset_ctrl.Enable(False)
            self.bulb_length_ctrl.Enable(False)
            self.min_dia_ctrl.Enable(False)
            self.max_dia_ctrl.Enable(False)
            self.flange_height_ctrl.Enable(False)
            self.flange_width_ctrl.Enable(False)
        else:
            self.length_ctrl.SetValue(db_obj.length)
            self.angle_ctrl.SetValue(db_obj.angle)
            self.offset_ctrl.SetValue(db_obj.offset)
            self.bulb_offset_ctrl.SetValue(db_obj.bulb_offset)
            self.bulb_length_ctrl.SetValue(db_obj.bulb_length)
            self.min_dia_ctrl.SetValue(db_obj.min_dia)
            self.max_dia_ctrl.SetValue(db_obj.max_dia)
            self.flange_height_ctrl.SetValue(db_obj.flange_height)
            self.flange_width_ctrl.SetValue(db_obj.flange_width)

            self.length_ctrl.Enable(True)
            self.angle_ctrl.Enable(True)
            self.offset_ctrl.Enable(True)
            self.bulb_offset_ctrl.Enable(True)
            self.bulb_length_ctrl.Enable(True)
            self.min_dia_ctrl.Enable(True)
            self.max_dia_ctrl.Enable(True)
            self.flange_height_ctrl.Enable(True)
            self.flange_width_ctrl.Enable(True)

    def _on_length(self, evt):
        value = evt.GetValue()
        self.db_obj.length = value

    def _on_angle(self, evt):
        value = evt.GetValue()
        self.db_obj.angle = value

    def _on_bulb_length(self, evt):
        value = evt.GetValue()
        self.db_obj.bulb_length = value

    def _on_min_dia(self, evt):
        value = evt.GetValue()
        self.db_obj.min_dia = value

    def _on_max_dia(self, evt):
        value = evt.GetValue()
        self.db_obj.max_dia = value

    def _on_flange_height(self, evt):
        value = evt.GetValue()
        self.db_obj.flange_height = value

    def _on_flange_width(self, evt):
        value = evt.GetValue()
        self.db_obj.flange_width = value

    def SetIndex(self, index):
        self.SetLabel(f'Branch {index}')

    def __init__(self, parent):
        self.db_obj: TransitionBranch = None
        super().__init__(parent, 'Branch')

        self.name_ctrl = NameControl(self)

        self.length_ctrl = _prop_grid.FloatProperty(
            self, 'Length', 0.01,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        self.angle_ctrl = _prop_grid.FloatProperty(
            self, 'Angle', 0.0, min_value=-180.0,
            max_value=180.0, increment=0.1, units='°')

        self.offset_ctrl = _prop_grid.Position2DProperty(self, 'Offset')

        bulb_group = _prop_grid.Property(self, f'Bulb', orientation=wx.VERTICAL)

        self.bulb_offset_ctrl = _prop_grid.Position2DProperty(bulb_group, 'Offset')
        self.bulb_length_ctrl = _prop_grid.FloatProperty(
            bulb_group, 'Length', 0.0,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        size_group = _prop_grid.Property(bulb_group, 'Diameter', orientation=wx.VERTICAL)

        self.min_dia_ctrl = _prop_grid.FloatProperty(
            size_group, 'Minimum', 0.01,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        self.max_dia_ctrl = _prop_grid.FloatProperty(
            size_group, 'Maximum', 0.01,
            min_value=0.01, max_value=999.9, increment=0.01, units='mm')

        flange_group = _prop_grid.Property(self, 'Flange', orientation=wx.VERTICAL)

        self.flange_height_ctrl = _prop_grid.FloatProperty(
            flange_group, 'Height', 0.0,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        self.flange_width_ctrl = _prop_grid.FloatProperty(
            flange_group, 'Width', 0.0,
            min_value=0.00, max_value=999.9, increment=0.01, units='mm')

        self.length_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_length)
        self.angle_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_angle)
        self.bulb_length_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_bulb_length)
        self.min_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_min_dia)
        self.max_dia_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_max_dia)
        self.flange_height_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_flange_height)
        self.flange_width_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_flange_width)
