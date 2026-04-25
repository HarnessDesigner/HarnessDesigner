import uuid
from typing import Iterable as _Iterable, TYPE_CHECKING

import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .bases import EntryBase, TableBase
from .mixins import NameMixin, DimensionMixin, DimensionControl
from ...geometry import point as _point
from ...geometry import angle as _angle

if TYPE_CHECKING:
    from . import housing as _housing
    from . import terminal as _terminal


class CavitiesTable(TableBase):
    __table_name__ = 'cavities'

    _control: "CavityControl" = None

    @property
    def control(self) -> "CavityControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = CavityControl(mainframe)
        cls._control.Show(False)

        # for i in range(20):
        #     control = CavityControl(mainframe)
        #     control.Show(False)
        #     control.SetIndex(i + 1)
        #     cls._controls.append(control)

    _controls: list["CavityControl"] = []

    def get_control(self, index):
        controls_len = len(self._controls)

        if controls_len - 1 < index:
            for i in range(controls_len - 1, index):
                ctrl = CavityControl(self.db.mainframe)
                ctrl.SetIndex(i + 1)
                ctrl.Show(False)
                self._controls.append(ctrl)

        return self._controls[index]

    def _table_needs_update(self) -> bool:
        from ..create_database import cavities

        return cavities.table.is_ok(self)

    def _add_table_to_db(self, _):
        from ..create_database import cavities

        cavities.table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import cavities

        cavities.table.update_fields(self)

    def __getitem__(self, item) -> "Cavity":
        if isinstance(item, int):
            if item in self:
                return Cavity(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def __iter__(self) -> _Iterable["Cavity"]:
        for db_id in TableBase.__iter__(self):
            yield Cavity(self, db_id)

    def insert(self, housing_id: int, idx: int) -> "Cavity":
        db_id = TableBase.insert(self, housing_id=housing_id, idx=idx)

        return Cavity(self, db_id)


class Cavity(EntryBase, NameMixin, DimensionMixin):
    _table: CavitiesTable = None

    def build_monitor_packet(self):
        packet = {
            'cavities': [self.db_id]
        }

        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    @property
    def housing(self) -> "_housing.Housing":
        from .housing import Housing

        housing_id = self.housing_id
        return Housing(self._table.db.housings_table, housing_id)

    @property
    def housing_id(self) -> int:
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @property
    def idx(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    def terminal_sizes(self) -> list[float]:
        return eval(self._table.select('terminal_sizes', id=self._db_id)[0][0])

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        for i, item in enumerate(value):
            value[i] = round(item, 6)

        self._table.update(self._db_id, terminal_sizes=str(value))
        self._populate('terminal_sizes')

    _position3d_id: str = None

    def __update_position3d(self, point: _point.Point):
        self._table.update(self._db_id, point3d=str(list(point.as_float)))

    @property
    def position3d(self) -> _point.Point:
        """
        This is relitive to the housing location
        """
        if self._position3d_id is None:
            self._position3d_id = str(uuid.uuid4())

        x, y, z = eval(self._table.select('point3d', id=self._db_id)[0][0])
        point = _point.Point(x, y, z, self._position3d_id)
        point.bind(self.__update_position3d)

        return point

    _position2d_id: str = None

    def __update_position2d(self, point: _point.Point):
        self._table.update(self._db_id, point2d=str(list(point.as_float[:-1])))

    @property
    def position2d(self) -> _point.Point:
        """
        This is relitive to the housing location
        """
        if self._position2d_id is None:
            self._position2d_id = str(uuid.uuid4())

        x, y = eval(self._table.select('point2d', id=self._db_id)[0][0])
        point = _point.Point(x, y, db_id=self._position3d_id)

        point.bind(self.__update_position2d)

        return point

    _angle3d_id: str = None

    def _update_angle3d(self, angle: _angle.Angle):
        euler = list(angle.as_euler_float)
        quat = list(angle.as_quat_float)
        self._table.update(self._db_id, angle3d=str(euler), quat3d=str(quat))

    @property
    def angle3d(self) -> _angle.Angle:
        """
        This is relitive to the housing angle
        """
        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        euler = eval(self._table.select('angle3d', id=self._db_id)[0][0])
        quat = eval(self._table.select('quat3d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler, self._angle3d_id)
        angle.bind(self._update_angle3d)

        return angle

    _angle2d_id: str = None

    def _update_angle2d(self, angle: _angle.Angle):
        euler = [angle.x, angle.y, angle.z]
        quat = angle.as_quat_float
        self._table.update(self._db_id, angle2d=str(euler), quat2d=str(quat))

    @property
    def angle2d(self):
        """
        This is relitive to the housing angle
        """
        if self._angle2d_id is None:
            self._angle2d_id = str(uuid.uuid4())

        euler = eval(self._table.select('angle2d', id=self._db_id)[0][0])
        quat = eval(self._table.select('quat2d', id=self._db_id)[0][0])

        angle = _angle.Angle.from_quat(quat, euler, self._angle2d_id)
        angle.bind(self._update_angle2d)

        return angle

    @property
    def round_terminal(self) -> bool:
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        self._table.update(self._db_id, round_terminal=int(value))
        self._populate('round_terminal')

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=round(value, 6))
        self._populate('length')

    @property
    def width(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                width = min(width, height)
                self._table.update(self._db_id, width=width, height=width)
            return width

        else:
            return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, width=round(value, 6))

        self._populate('width')

    @property
    def height(self) -> float:
        if self.round_terminal:
            width, height = self._table.select('width', 'height', id=self._db_id)[0]
            if width != height:
                height = min(width, height)
                self._table.update(self._db_id, width=height, height=height)

            return height

        else:
            return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        if self.round_terminal:
            self._table.update(self._db_id, width=round(value, 6), height=round(value, 6))
        else:
            self._table.update(self._db_id, height=round(value, 6))

        self._populate('height')

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            if self.round_terminal:
                if y > 0:
                    x = y

                    self._table.update(self._db_id, width=y)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, width=1.0)
                x = 1.0

        if y <= 0:
            if self.round_terminal:
                if x > 0:
                    y = x

                    self._table.update(self._db_id, height=x)
                else:
                    self._table.update(self._db_id, width=1.0, height=1.0)
                    x = y = 1.0
            else:
                self._table.update(self._db_id, height=1.0)
                y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        terminal_sizes = self.terminal_sizes
        round_terminal = self.round_terminal

        res = []

        for terminal in self.housing.compat_terminals:
            if (
                not terminal_sizes and
                terminal.round_terminal == round_terminal
            ):
                res.append(terminal)
            elif terminal_sizes:
                for terminal_size in terminal_sizes:
                    if (
                        terminal.blade_size == terminal_size and
                        terminal.round_terminal == round_terminal
                    ):
                        res.append(terminal)

        return res


class CavityControl(_prop_grid.Category):

    def SetIndex(self, index):
        self.SetLabel(f'Cavity {index}')

    def set_obj(self, db_obj: Cavity):
        self.db_obj = db_obj

        self.dimension_page.set_obj(db_obj)

        if db_obj is None:
            self.index_ctrl.SetValue(0)
            self.terminal_sizes_ctrl.SetValue([])
            self.round_terminal_ctrl.SetValue(False)

            self.position3d_ctrl.SetValue(None)
            self.position2d_ctrl.SetValue(None)
            self.angle3d_ctrl.SetValue(None)

            self.index_ctrl.Enable(False)
            self.terminal_sizes_ctrl.Enable(False)
            self.round_terminal_ctrl.Enable(False)
        else:
            self.index_ctrl.SetValue(db_obj.idx)
            self.terminal_sizes_ctrl.SetValue(db_obj.terminal_sizes)
            self.round_terminal_ctrl.SetValue(db_obj.round_terminal)

            self.position3d_ctrl.SetValue(db_obj.position3d)
            self.position2d_ctrl.SetValue(db_obj.position2d)
            self.angle3d_ctrl.SetValue(db_obj.angle3d)

            self.index_ctrl.Enable(True)
            self.terminal_sizes_ctrl.Enable(True)
            self.round_terminal_ctrl.Enable(True)

    def _on_round_terminal(self, evt):
        value = evt.GetValue()
        self.db_obj.round_terminal = value

    def _on_terminal_sizes(self, evt):
        value = evt.GetValue()
        self.db_obj.terminal_sizes = value

    def _on_index(self, evt):
        value = evt.GetValue()
        self.db_obj.idx = value

    def __init__(self, parent):
        self.db_obj: Cavity = None

        super().__init__(parent, 'Cavity')

        self.nb = wx.Notebook(self, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self.nb, 'General')

        self.index_ctrl = _prop_grid.IntProperty(general_page, 'Index', min_value=0, max_value=999)
        self.round_terminal_ctrl = _prop_grid.BoolProperty(general_page, 'Is Round')
        self.terminal_sizes_ctrl = _prop_grid.ArrayFloatProperty(general_page, 'Terminal sizes')

        self.dimension_page = DimensionControl(self.nb)

        position_page = _prop_grid.Category(self.nb, 'Position')
        self.position2d_ctrl = _prop_grid.Position2DProperty(position_page, '2D Position')
        self.position3d_ctrl = _prop_grid.Position3DProperty(position_page, '3D Position')

        angle_page = _prop_grid.Category(self.nb, 'Angle')
        self.angle3d_ctrl = _prop_grid.Angle3DProperty(angle_page, '3D Angle')

        self.round_terminal_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_round_terminal)
        self.index_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_index)
        self.terminal_sizes_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_terminal_sizes)

        for page in (
            general_page,
            self.dimension_page,
            position_page,
            angle_page
        ):
            self.nb.AddPage(page, page.GetLabel())
            page.Realize()
