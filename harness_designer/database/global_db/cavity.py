# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6.QtWidgets import QTabWidget
from typing import Iterable as _Iterable, TYPE_CHECKING

import uuid
import numpy as np

from ...ui import prop_ctrls as _prop_ctrls
from .bases import EntryBase, TableBase
from .mixins import NameMixin, DimensionMixin, DimensionControl
from ...geometry import point as _point
from ...geometry import angle as _angle
from ..common_db.lazy_tab_mixin import LazyTabMixin


if TYPE_CHECKING:
    from . import housing as _housing
    from . import terminal as _terminal


class CavitiesTable(TableBase):
    """Represent a cavities table in :mod:`harness_designer.database.global_db.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'cavities'

    _control: "CavityControl" = None

    @property
    def control(self) -> "CavityControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`CavityControl`
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
        cls._control = CavityControl(mainframe)
        cls._control.hide()

        # for i in range(20):
        #     control = CavityControl(mainframe)
        #     control.hide()
        #     control.SetIndex(i + 1)
        #     cls._controls.append(control)

    _controls: list["CavityControl"] = []

    def get_control(self, index):
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        controls_len = len(self._controls)

        if controls_len - 1 < index:
            for i in range(controls_len - 1, index):
                ctrl = CavityControl(self.db.mainframe)
                ctrl.SetIndex(i + 1)
                ctrl.hide()
                self._controls.append(ctrl)

        return self._controls[index]

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import cavities

        return cavities.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        from ..create_database import cavities

        cavities.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import cavities

        cavities.table.update_fields(self)

    def __getitem__(self, item) -> "Cavity":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Cavity`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Cavity(self, item)
            raise IndexError(str(item))

        raise KeyError(item)

    def __iter__(self) -> _Iterable["Cavity"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Cavity']
        """
        for db_id in TableBase.__iter__(self):
            yield Cavity(self, db_id)

    def insert(self, housing_id: int, idx: int) -> "Cavity":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param housing_id: Identifier for the housing.
        :type housing_id: int
        :param idx: Value for ``idx``.
        :type idx: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Cavity`
        """
        db_id = TableBase.insert(self, housing_id=housing_id, idx=idx)

        return Cavity(self, db_id)


class Cavity(EntryBase, NameMixin, DimensionMixin):
    """Represent a cavity in :mod:`harness_designer.database.global_db.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: CavitiesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'cavities': [self.db_id]
        }

        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    @property
    def housing(self) -> "_housing.Housing":
        """Return the housing.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_housing.Housing`
        """
        from .housing import Housing

        housing_id = self.housing_id
        return Housing(self._table.db.housings_table, housing_id)

    @property
    def housing_id(self) -> int:
        """Return the housing ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('housing_id', id=self._db_id)[0][0]

    @property
    def idx(self) -> int:
        """Return the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('idx', id=self._db_id)[0][0]

    @idx.setter
    def idx(self, value: int):
        """Set the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, idx=value)
        self._populate('idx')

    @property
    def terminal_sizes(self) -> list[float]:
        """Return the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[float]
        """
        value = self._table.select('terminal_sizes', id=self._db_id)[0][0]
        if not value.startswith('['):
            value = f'[{value}]'

        return eval(value)

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        """Set the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[float]
        """
        for i, item in enumerate(value):
            value[i] = round(item, 6)

        self._table.update(self._db_id, terminal_sizes=str(value)[1:-1])
        self._populate('terminal_sizes')

    _position3d_id: str = None

    def __update_position3d(self, point: _point.Point):
        """Update the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
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
        """Update the position 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        """
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
        """Update the angle 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        euler = str(list(angle.as_euler_float))
        quat = str(list(angle.as_quat_float))

        if 'nan' in euler or 'nan' in quat:
            return

        self._table.update(self._db_id, angle3d=euler, quat3d=quat)

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
        """Update the angle 2D.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        euler = str(list(angle.as_euler_float))
        quat = str(list(angle.as_quat_float))

        if 'nan' in euler or 'nan' in quat:
            return

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
    def aabb(self) -> np.ndarray | None:
        value = self._table.select('aabb', id=self._db_id)[0][0]
        if value is None:
            return value

        value = np.array(eval(value), dtype=np.float32)
        return value

    @aabb.setter
    def aabb(self, value: np.ndarray):
        value = [[float(str(item)) for item in items]
                 for items in value.tolist()]

        self._table.update(self._db_id, aabb=str(value))

    @property
    def obb(self) -> np.ndarray | None:
        value = self._table.select('obb', id=self._db_id)[0][0]
        if value is None:
            return value

        value = np.array(eval(value), dtype=np.float32)
        return value

    @obb.setter
    def obb(self, value: np.ndarray):
        value = [[float(str(item)) for item in items]
                 for items in value.tolist()]

        self._table.update(self._db_id, obb=str(value))

    @property
    def round_terminal(self) -> bool:
        """Return the round terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('round_terminal', id=self._db_id)[0][0])

    @round_terminal.setter
    def round_terminal(self, value: bool):
        """Set the round terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, round_terminal=int(value))
        self._populate('round_terminal')

    @property
    def render_terminal_marker(self) -> bool:
        """Return whether a synthetic terminal-plane marker should be rendered.

        Housings with a single continuous terminal-side plane (no distinct
        recessed mesh surface per cavity) have no way to distinguish cavities
        by mesh geometry alone. When this flag is set, the OBB (already
        stored per cavity) and ``round_terminal`` are used to render and
        click-test a synthetic circle/rectangle marker in place of real mesh
        geometry.
        """
        return bool(self._table.select('render_terminal_marker', id=self._db_id)[0][0])

    @render_terminal_marker.setter
    def render_terminal_marker(self, value: bool):
        """Set whether a synthetic terminal-plane marker should be rendered."""
        self._table.update(self._db_id, render_terminal_marker=(1 if value else None))
        self._populate('render_terminal_marker')

    @property
    def terminal_surf_indices(self) -> list[int]:
        """Return the mesh-surface indices selected as this cavity's terminal
        face in the housing editor, or ``[]`` if never assigned.

        Indices are into ``MeshSurfacePicker.surfaces`` for this part's mesh
        (see ``objects3d/housing.py`` ``match_cavity_surfaces``) — stable as
        long as the underlying model isn't re-simplified/re-imported.
        """
        value = self._table.select('terminal_surf_indices', id=self._db_id)[0][0]
        if value is None:
            return []

        return list(eval(value))

    @terminal_surf_indices.setter
    def terminal_surf_indices(self, value: list[int]):
        """Set the terminal-face mesh-surface indices."""
        self._table.update(self._db_id, terminal_surf_indices=str(list(value)))
        self._populate('terminal_surf_indices')

    @property
    def wire_surf_indices(self) -> list[int]:
        """Return the mesh-surface indices selected as this cavity's wire
        face in the housing editor, or ``[]`` if never assigned.

        See ``terminal_surf_indices`` for details.
        """
        value = self._table.select('wire_surf_indices', id=self._db_id)[0][0]
        if value is None:
            return []

        return list(eval(value))

    @wire_surf_indices.setter
    def wire_surf_indices(self, value: list[int]):
        """Set the wire-face mesh-surface indices."""
        self._table.update(self._db_id, wire_surf_indices=str(list(value)))
        self._populate('wire_surf_indices')

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, length=value)
        self._populate('length')

    @property
    def width(self) -> float:
        """Return the width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
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
        """Set the width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        if self.round_terminal:
            self._table.update(self._db_id, width=value, height=value)
        else:
            self._table.update(self._db_id, width=value)

        self._populate('width')

    @property
    def height(self) -> float:
        """Return the height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
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
        """Set the height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        if self.round_terminal:
            self._table.update(self._db_id, width=value, height=value)
        else:
            self._table.update(self._db_id, height=value)

        self._populate('height')

    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        width, height, length = scale.as_float

        if self.round_terminal and width != height:
            width = height = min(width, height)

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
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
        """Return the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_terminal.Terminal']
        """
        terminal_sizes = self.terminal_sizes
        round_terminal = self.round_terminal

        res = []

        for terminal in self.housing.compat_terminals:
            if terminal.round_terminal == round_terminal:
                blade_size = terminal.blade_size
                if (
                    (blade_size and blade_size in terminal_sizes) or
                    not terminal_sizes
                ):
                    res.append(terminal)

        return res


class CavityControl(QTabWidget, LazyTabMixin):
    """Represent a cavity control in :mod:`harness_designer.database.global_db.cavity`.

    A housing loads all of its cavities as tabs in a notebook (see
    ``HousingControl``), so this is itself a notebook — like every other
    per-part-type control (``PJTTerminalControl`` is the reference) — rather
    than a ``Category`` page wrapping a second, nested notebook.
    """

    _label = 'Cavity'

    def GetLabel(self) -> str:
        """Return the tab label a parent notebook should use for this control."""
        return self._label

    def SetLabel(self, value: str) -> None:
        """Set the tab label a parent notebook should use for this control."""
        self._label = value

    def SetIndex(self, index):
        """Execute the set index operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param index: Index value.
        :type index: UNKNOWN
        """
        self.SetLabel(f'Cavity {index}')

    def set_obj(self, db_obj: Cavity):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`Cavity`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        db_obj = self.db_obj

        if page is self._general_page:
            if db_obj is None:
                self.index_ctrl.SetValue(0)
                self.terminal_sizes_ctrl.SetValue([])
                self.round_terminal_ctrl.SetValue(False)

                self.index_ctrl.setEnabled(False)
                self.terminal_sizes_ctrl.setEnabled(False)
                self.round_terminal_ctrl.setEnabled(False)
            else:
                self.index_ctrl.SetValue(db_obj.idx)
                self.terminal_sizes_ctrl.SetValue(db_obj.terminal_sizes)
                self.round_terminal_ctrl.SetValue(db_obj.round_terminal)

                self.index_ctrl.setEnabled(True)
                self.terminal_sizes_ctrl.setEnabled(True)
                self.round_terminal_ctrl.setEnabled(True)
        elif page is self.dimension_page:
            self.dimension_page.set_obj(db_obj)
        elif page is self._position_page:
            self.position3d_ctrl.SetValue(None if db_obj is None else db_obj.position3d)
            self.position2d_ctrl.SetValue(None if db_obj is None else db_obj.position2d)
        elif page is self._angle_page:
            self.angle3d_ctrl.SetValue(None if db_obj is None else db_obj.angle3d)

        self._tab_loaded[index] = True

    def _on_round_terminal(self, evt):
        """Handle the round terminal event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.round_terminal = value

    def _on_terminal_sizes(self, evt):
        """Handle the terminal sizes event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.terminal_sizes = value

    def _on_index(self, evt):
        """Handle the index event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        value = evt.GetValue()
        self.db_obj.idx = value

    def __init__(self, parent):
        """Initialise the :class:`CavityControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: Cavity = None
        self._label = 'Cavity'

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.index_ctrl = _prop_ctrls.IntProperty(general_page, 'Index', min_value=0, max_value=999)
        self.round_terminal_ctrl = _prop_ctrls.BoolProperty(general_page, 'Is Round')
        self.terminal_sizes_ctrl = _prop_ctrls.ArrayFloatProperty(general_page, 'Terminal sizes')

        general_page.addWidget(self.index_ctrl)
        general_page.addWidget(self.round_terminal_ctrl)
        general_page.addWidget(self.terminal_sizes_ctrl)

        self.dimension_page = DimensionControl(self)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = _prop_ctrls.Position2DProperty(position_page, '2D Position')
        self.position3d_ctrl = _prop_ctrls.Position3DProperty(position_page, '3D Position')

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle3d_ctrl = _prop_ctrls.Angle3DProperty(angle_page, '3D Angle')

        angle_page.addWidget(self.angle3d_ctrl)

        self.round_terminal_ctrl.propertyChanged.connect(self._on_round_terminal)
        self.index_ctrl.propertyChanged.connect(self._on_index)
        self.terminal_sizes_ctrl.propertyChanged.connect(self._on_terminal_sizes)

        for page in (
            general_page,
            self.dimension_page,
            position_page,
            angle_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
