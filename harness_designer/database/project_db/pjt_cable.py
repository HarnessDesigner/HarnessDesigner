# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A placed cable: a shielded wire part, or one with more than one conductor.

The cable is the physical thing that is placed, routed, drawn and listed once in the bill of materials. What a circuit
contains is its conductors (:mod:`.pjt_cable_conductor`), not the cable, so a cable has no circuit, resistance or
operating temperature. It has the 3D and peg-board position of a wire (start, stop and interior waypoints through
``pjt_cable_paths``, keyed on the cable's id) and no schematic presence, like a bundle. See ``TWISTED_WIRE_DESIGN.md``
section 8a in the repo root for the whole design.

The cable's property control (:class:`PJTCableControl`) is the one the object editor shows for a selected cable; the split
distances and the roll are shown there and changed from the cable's right-click menu (a split moves the conductors' end points,
so it is not a plain field).
"""

from typing import TYPE_CHECKING, Iterable as _Iterable

import colorsys
import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import wire as _wire
from .pjt_bases import PJTEntryBase, PJTTableBase
from .pjt_wire import delete_layouts_at
from .mixins import (
    StartStopPosition3DMixin, StartStopPosition3DControl,
    StartStopPositionPegboardMixin, StartStopPositionPegboardControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin, VisiblePegboardControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)
from ...geometry import line as _line
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from . import pjt_cable_conductor as _pjt_cable_conductor
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point_pegboard as _pjt_point_pegboard
    from ...objects import cable as _cable_obj
    from ... import ui as _ui
    from ...geometry import point as _point


class PJTCablesTable(PJTTableBase):
    """Table of placed cables (``pjt_cables``)."""

    __table_name__ = 'pjt_cables'

    _control: "PJTCableControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTCableControl":
        """The property control the object editor shows for a cable (one for the whole session, see ``start_control``).

        :rtype: :class:`PJTCableControl`
        :raises RuntimeError: Raised when ``start_control`` has not run.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe: "_ui.MainFrame") -> None:
        """Make the cable property control (called once, as the main frame is built).

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        """
        cls._control = PJTCableControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import cables

        return cables.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Create the ``pjt_cables`` table in the database."""
        from ..create_database import cables

        cables.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Add any missing fields to the ``pjt_cables`` table."""
        from ..create_database import cables

        cables.pjt_table.update_fields(self)

    # The colours of the cables' rows in the peg-board wire tables are DARK (they sit on a dark theme): hues spread by the golden
    # angle, so each new cable lands far from the ones before it, at this saturation and value (HSV, 0..1).
    BG_SATURATION = 0.55
    BG_VALUE = 0.40

    @_check_types.do
    def next_bg_color(self) -> int:
        """A dark background colour no other cable of the project has, as ``0xRRGGBB``.

        :rtype: int
        """
        used = {row[0] for row in self.select('bg_color') if row[0] is not None}
        index = len(used)

        while True:
            hue = (index * 0.381966) % 1.0
            red, green, blue = colorsys.hsv_to_rgb(hue, self.BG_SATURATION, self.BG_VALUE)
            value = (round(red * 255) << 16) | (round(green * 255) << 8) | round(blue * 255)

            if value not in used:
                return value

            index += 1

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTCable"]:
        """Iterate over every cable of the open project.

        :returns: An iterator of :class:`PJTCable` rows.
        :rtype: _Iterable['PJTCable']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCable(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTCable":
        """Return the cable with the given database id.

        :param item: Row id to look up.
        :type item: int | bytes | str
        :returns: The matching row.
        :rtype: :class:`PJTCable`
        :raises KeyError: Raised when ``item`` is not an ``int`` or ``bytes``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTCable or item in self:
                return PJTCable(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, start_point3d_id: bytes | None, stop_point3d_id: bytes | None,
               start_point_pegboard_id: bytes | None, stop_point_pegboard_id: bytes | None,
               is_visible3d: bool, is_visible_pegboard: bool) -> "PJTCable":
        """Insert a cable row. Its conductors are not made here: see ``PJTCableConductorsTable.insert``.

        Both ends start out unsplit (``start_split_mm`` and ``stop_split_mm`` are 0.0).

        Conductors are made later, by ``PJTCableConductorsTable.insert_for_cable``, once the cable's end points are
        final: each conductor's end points are children of the cable's, so they must not be made while the cable is
        still being placed (its end point is replaced every time a waypoint is committed).

        :param part_id: The catalog wire (``Wire.is_cable`` is true for it).
        :type part_id: bytes
        :param name: The cable's name.
        :type name: str
        :param start_point3d_id: 3D point of the start end.
        :type start_point3d_id: bytes | None
        :param stop_point3d_id: 3D point of the stop end.
        :type stop_point3d_id: bytes | None
        :param start_point_pegboard_id: Peg-board point of the start end.
        :type start_point_pegboard_id: bytes | None
        :param stop_point_pegboard_id: Peg-board point of the stop end.
        :type stop_point_pegboard_id: bytes | None
        :param is_visible3d: Whether the cable shows in the 3D editor.
        :type is_visible3d: bool
        :param is_visible_pegboard: Whether the cable shows on the peg board.
        :type is_visible_pegboard: bool
        :returns: The new row.
        :rtype: :class:`PJTCable`
        """
        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name, bundle_id=None, transition_id=None,
            start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
            start_point_pegboard_id=start_point_pegboard_id, stop_point_pegboard_id=stop_point_pegboard_id,
            start_split_mm=0.0, stop_split_mm=0.0, roll_deg=0.0, bg_color=self.next_bg_color(),
            start_shield_splice_id=None, stop_shield_splice_id=None, notes='',
            is_visible3d=int(is_visible3d), is_visible_pegboard=int(is_visible_pegboard), smooth=None)

        return PJTCable(self, db_id)


@capturable()
class PJTCable(PJTEntryBase, StartStopPosition3DMixin, PartMixin, StartStopPositionPegboardMixin,
               Visible3DMixin, VisiblePegboardMixin, NameMixin, NotesMixin, SmoothMixin):
    """A placed cable (``pjt_cables``)."""

    _table: PJTCablesTable = None

    @_check_types.do
    def get_object(self) -> "_cable_obj.Cable":
        """Return the live cable object this row is bound to; ``None`` while there is none.

        :rtype: :class:`_cable_obj.Cable`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Forget the cable object once it has been garbage collected.

        :param _: The dead reference.
        :type _: weakref.ref
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_cable_obj.Cable") -> None:
        """Bind the live cable object to this row (weakly), and tell whoever waited for it.

        :param obj: The object, or ``None`` to unbind.
        :type obj: :class:`_cable_obj.Cable`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def table(self) -> PJTCablesTable:
        """Return the cables table.

        :rtype: :class:`PJTCablesTable`
        """
        return self._table

    @property
    @_check_types.do
    def part(self) -> "_wire.Wire":
        """Return the catalog wire this cable was placed from.

        :rtype: :class:`_wire.Wire`
        """
        return self._table.db.global_db.wires_table[self.part_id]

    @property
    @dump_property(severity=2)
    @_check_types.do
    def start_split_mm(self) -> float:
        """How far from the start end the conductors are split apart; 0.0 while that end is not split.

        :rtype: float
        """
        return self._table.select('start_split_mm', id=self._db_id)[0][0]

    @start_split_mm.setter
    @_check_types.do
    def start_split_mm(self, value: float) -> None:
        """Set how far from the start end the conductors are split apart.

        :param value: Distance in mm; 0.0 for an end that is not split.
        :type value: float
        """
        self._table.update(self._db_id, start_split_mm=value)
        self._populate('start_split_mm')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def stop_split_mm(self) -> float:
        """How far from the stop end the conductors are split apart; 0.0 while that end is not split.

        :rtype: float
        """
        return self._table.select('stop_split_mm', id=self._db_id)[0][0]

    @stop_split_mm.setter
    @_check_types.do
    def stop_split_mm(self, value: float) -> None:
        """Set how far from the stop end the conductors are split apart.

        :param value: Distance in mm; 0.0 for an end that is not split.
        :type value: float
        """
        self._table.update(self._db_id, stop_split_mm=value)
        self._populate('stop_split_mm')

    @property
    @dump_property(severity=2)
    @_check_types.do
    def roll_deg(self) -> float:
        """How far a ribbon cable's flat side is turned about the trunk's axis at the start, degrees.

        :rtype: float
        """
        return self._table.select('roll_deg', id=self._db_id)[0][0]

    @roll_deg.setter
    @_check_types.do
    def roll_deg(self, value: float) -> None:
        """Set the roll of a ribbon cable.

        :param value: Degrees.
        :type value: float
        """
        self._table.update(self._db_id, roll_deg=value)
        self._populate('roll_deg')

    @property
    @_check_types.do
    def bg_color(self) -> int:
        """The background colour of this cable's rows in the peg-board wire tables, ``0xRRGGBB``. A cable that has none yet (made
        before the column existed) is given a dark one no other cable has, which is stored, so it stays the same.

        :rtype: int
        """
        value = self._table.select('bg_color', id=self._db_id)[0][0]

        if value is None:
            value = self._table.next_bg_color()
            self._table.update(self._db_id, bg_color=value)

        return value

    @bg_color.setter
    @_check_types.do
    def bg_color(self, value: int) -> None:
        """Set the background colour of this cable's rows in the peg-board wire tables.

        :param value: ``0xRRGGBB``.
        :type value: int
        """
        self._table.update(self._db_id, bg_color=int(value) & 0xFFFFFF)
        self._populate('bg_color')

    @property
    @_check_types.do
    def start_shield_splice_id(self) -> bytes | None:
        """The solder sleeve (``pjt_splices`` row id) that finishes the shield at the cable's start end; ``None`` for none.

        :rtype: bytes | None
        """
        return self._table.select('start_shield_splice_id', id=self._db_id)[0][0]

    @start_shield_splice_id.setter
    @_check_types.do
    def start_shield_splice_id(self, value: bytes | None) -> None:
        """Set (or clear) the solder sleeve of the start end.

        :param value: A ``pjt_splices`` row id, or ``None``.
        :type value: bytes | None
        """
        self._table.update(self._db_id, start_shield_splice_id=value)
        self._populate('start_shield_splice_id')

    @property
    @_check_types.do
    def stop_shield_splice_id(self) -> bytes | None:
        """The solder sleeve (``pjt_splices`` row id) that finishes the shield at the cable's stop end; ``None`` for none.

        :rtype: bytes | None
        """
        return self._table.select('stop_shield_splice_id', id=self._db_id)[0][0]

    @stop_shield_splice_id.setter
    @_check_types.do
    def stop_shield_splice_id(self, value: bytes | None) -> None:
        """Set (or clear) the solder sleeve of the stop end.

        :param value: A ``pjt_splices`` row id, or ``None``.
        :type value: bytes | None
        """
        self._table.update(self._db_id, stop_shield_splice_id=value)
        self._populate('stop_shield_splice_id')

    # which ends have the shield clipped off: 0 none, 1 start, 2 stop, 3 both (the two bits)
    SHIELD_CLIPPED_START = 1
    SHIELD_CLIPPED_STOP = 2

    @property
    @_check_types.do
    def shield_clipped(self) -> int:
        """Which ends have the shield clipped off: 0 = neither, 1 = the start end, 2 = the stop end, 3 = both.

        :rtype: int
        """
        return int(self._table.select('shield_clipped', id=self._db_id)[0][0] or 0)

    @shield_clipped.setter
    @_check_types.do
    def shield_clipped(self, value: int) -> None:
        """Set which ends have the shield clipped off.

        :param value: 0 neither, 1 start, 2 stop, 3 both.
        :type value: int
        """
        if value not in (0, 1, 2, 3):
            raise ValueError(f'shield_clipped must be 0, 1, 2 or 3, got {value!r}')

        self._table.update(self._db_id, shield_clipped=int(value))
        self._populate('shield_clipped')

    @_check_types.do
    def shield_end_clipped(self, start: bool) -> bool:
        """Whether the shield is clipped off at one end.

        :param start: ``True`` for the start end, ``False`` for the stop end.
        :type start: bool
        """
        bit = self.SHIELD_CLIPPED_START if start else self.SHIELD_CLIPPED_STOP
        return bool(self.shield_clipped & bit)

    @_check_types.do
    def set_shield_end_clipped(self, start: bool, clipped: bool) -> None:
        """Clip off, or put back, the shield at one end; the other end is left as it is.

        :param start: ``True`` for the start end, ``False`` for the stop end.
        :type start: bool
        :param clipped: Whether the shield is clipped at that end.
        :type clipped: bool
        """
        bit = self.SHIELD_CLIPPED_START if start else self.SHIELD_CLIPPED_STOP
        value = self.shield_clipped

        self.shield_clipped = (value | bit) if clipped else (value & ~bit)

    @_check_types.do
    def shield_splice_id(self, start: bool) -> bytes | None:
        """The solder sleeve of one end.

        :param start: ``True`` for the start end, ``False`` for the stop end.
        :type start: bool
        :rtype: bytes | None
        """
        return self.start_shield_splice_id if start else self.stop_shield_splice_id

    @_check_types.do
    def set_shield_splice_id(self, start: bool, value: bytes | None) -> None:
        """Set (or clear) the solder sleeve of one end.

        :param start: ``True`` for the start end, ``False`` for the stop end.
        :type start: bool
        :param value: A ``pjt_splices`` row id, or ``None``.
        :type value: bytes | None
        """
        if start:
            self.start_shield_splice_id = value
        else:
            self.stop_shield_splice_id = value

    @property
    @_check_types.do
    def conductors(self) -> list["_pjt_cable_conductor.PJTCableConductor"]:
        """Every conductor of the cable, then its shield if it has one, in ``idx`` order.

        :rtype: list[:class:`_pjt_cable_conductor.PJTCableConductor`]
        """
        return self._table.db.pjt_cable_conductors_table.for_cable(self._db_id)

    @property
    @_check_types.do
    def waypoints3d(self) -> list["_pjt_point3d.PJTPoint3D"]:
        """Every interior 3D waypoint of the cable's trunk, in order (the start and stop ends are not included).

        :rtype: list[:class:`_pjt_point3d.PJTPoint3D`]
        """
        points_table = self._table.db.pjt_points3d_table
        point_ids = self._table.db.pjt_cable_paths_table.point_ids(self.db_id, '3d')

        return [points_table[point_id] for point_id in point_ids]

    @property
    @_check_types.do
    def waypoints_pegboard(self) -> list["_pjt_point_pegboard.PJTPointPegboard"]:
        """Every interior peg-board waypoint of the cable's trunk, in order. Independent of :attr:`waypoints3d`.

        :rtype: list[:class:`_pjt_point_pegboard.PJTPointPegboard`]
        """
        points_table = self._table.db.pjt_points_pegboard_table
        point_ids = self._table.db.pjt_cable_paths_table.point_ids(self.db_id, 'pegboard')

        return [points_table[point_id] for point_id in point_ids]

    @property
    @_check_types.do
    def length_mm(self) -> float:
        """The length of the whole cable in mm: every stretch from the start, through each interior waypoint, to the stop.

        :rtype: float
        """
        points = [self.start_position3d, *(p.point for p in self.waypoints3d), self.stop_position3d]

        total = 0.0
        for a, b in zip(points, points[1:]):
            total += _line.Line(a, b).length()

        return total

    @property
    @_check_types.do
    def length_m(self) -> float:
        """The length in metres.

        :rtype: float
        """
        return self.length_mm / 1000.0

    @property
    @_check_types.do
    def length_ft(self) -> float:
        """The length in feet.

        :rtype: float
        """
        return self.length_m * 3.28084

    @property
    @_check_types.do
    def weight_g(self) -> float:
        """The cable's weight in grams: the whole cable, every conductor in it.

        :rtype: float
        """
        return self.part.weight_g_m * self.length_m

    @property
    @_check_types.do
    def weight_lb(self) -> float:
        """The cable's weight in pounds.

        :rtype: float
        """
        return self.part.weight_lb_ft * self.length_ft

    @_check_types.do
    def delete(self) -> None:
        """Delete the cable, its conductors, its route and the layout markers at its waypoints.

        The waypoint point rows are left alone, as for a wire (a point can be shared; the orphan sweep removes them).
        """
        layouts_table = self._table.db.pjt_wire_layouts_table

        for point in self.waypoints3d:
            delete_layouts_at(layouts_table, 'point3d_id', point.db_id)

        for point in self.waypoints_pegboard:
            delete_layouts_at(layouts_table, 'point_pegboard_id', point.db_id)

        for conductor in self.conductors:
            conductor.delete()

        # the sleeves of the shield go with the cable (the column is cleared first: it references the splice row)
        for start in (True, False):
            sleeve_id = self.shield_splice_id(start)

            if sleeve_id is not None:
                self.set_shield_splice_id(start, None)
                splices_table = self._table.db.pjt_splices_table

                if sleeve_id in splices_table:
                    splices_table[sleeve_id].delete()

        self._table.db.pjt_cable_paths_table.delete_for_wire(self.db_id)

        super().delete()


class PJTCableControl(QtWidgets.QTabWidget, LazyTabMixin):
    """The property control of a placed cable: name, notes, position, visibility, length and weight, how it is split and the
    catalog part it was placed from. Its conductors have a control of their own (``PJTCableConductorControl``)."""

    @_check_types.do
    def _update_position3d(self, _: "_point.Point") -> None:
        """Show the length and weight again after an end of the cable moved."""
        self._show_info()

    @_check_types.do
    def _show_info(self) -> None:
        """Fill the Info page from the cable (or empty it)."""
        db_obj = self.db_obj

        if db_obj is None:
            for ctrl in (self.length_mm_ctrl, self.length_m_ctrl, self.length_ft_ctrl, self.weight_g_ctrl,
                         self.weight_lb_ctrl, self.start_split_ctrl, self.stop_split_ctrl, self.roll_ctrl,
                         self.conductor_count_ctrl):
                ctrl.SetValue('')

            return

        self.length_mm_ctrl.SetValue(str(db_obj.length_mm))
        self.length_m_ctrl.SetValue(str(db_obj.length_m))
        self.length_ft_ctrl.SetValue(str(db_obj.length_ft))
        self.weight_g_ctrl.SetValue(str(db_obj.weight_g))
        self.weight_lb_ctrl.SetValue(str(db_obj.weight_lb))

        start = db_obj.start_split_mm
        stop = db_obj.stop_split_mm
        self.start_split_ctrl.SetValue(f'{start:.1f}' if start > 0.0 else 'not split')
        self.stop_split_ctrl.SetValue(f'{stop:.1f}' if stop > 0.0 else 'not split')
        self.roll_ctrl.SetValue(f'{db_obj.roll_deg:.1f}' if db_obj.part.is_ribbon else '')
        self.conductor_count_ctrl.SetValue(str(len(db_obj.conductors)))

    @_check_types.do
    def set_obj(self, db_obj: "PJTCable | None") -> None:
        """Show *db_obj* (``None`` clears the control and lets go of the cable).

        :param db_obj: The cable's row.
        :type db_obj: :class:`PJTCable`
        """
        if self.db_obj is not None:
            self.db_obj.start_position3d.unbind(self._update_position3d)
            self.db_obj.stop_position3d.unbind(self._update_position3d)

        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        page = self.widget(index)

        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._info_page:
            self._show_info()
        elif page is self._position_page:
            self.position3d_ctrl.set_obj(self.db_obj)
            self.position_pegboard_ctrl.set_obj(self.db_obj)

            if self.db_obj is not None:
                self.db_obj.start_position3d.bind(self._update_position3d)
                self.db_obj.stop_position3d.bind(self._update_position3d)
        elif page is self._visible_page:
            self.visible3d_ctrl.set_obj(self.db_obj)
            self.visible_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.wire_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)

        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`PJTCableControl` instance.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QWidget`
        """
        self.db_obj: PJTCable | None = None

        QtWidgets.QTabWidget.__init__(self, parent)
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.note_ctrl)
        general_page.addWidget(self.smooth_ctrl)

        self._info_page = info_page = _prop_ctrls.Category(self, 'Info')

        length_group = _prop_ctrls.Property(info_page, 'Length', orientation='vertical')
        info_page.addWidget(length_group)

        self.length_mm_ctrl = _prop_ctrls.StringProperty(length_group, 'Millimeter', read_only=True)
        self.length_m_ctrl = _prop_ctrls.StringProperty(length_group, 'Meter', read_only=True)
        self.length_ft_ctrl = _prop_ctrls.StringProperty(length_group, 'Foot', read_only=True)

        length_group.addWidget(self.length_mm_ctrl)
        length_group.addWidget(self.length_m_ctrl)
        length_group.addWidget(self.length_ft_ctrl)

        weight_group = _prop_ctrls.Property(info_page, 'Weight', orientation='vertical')
        info_page.addWidget(weight_group)

        self.weight_g_ctrl = _prop_ctrls.StringProperty(weight_group, 'Gram', read_only=True)
        self.weight_lb_ctrl = _prop_ctrls.StringProperty(weight_group, 'Pound', read_only=True)

        weight_group.addWidget(self.weight_g_ctrl)
        weight_group.addWidget(self.weight_lb_ctrl)

        conductor_group = _prop_ctrls.Property(info_page, 'Conductors', orientation='vertical')
        info_page.addWidget(conductor_group)

        self.conductor_count_ctrl = _prop_ctrls.StringProperty(conductor_group, 'Count', read_only=True)
        self.start_split_ctrl = _prop_ctrls.StringProperty(conductor_group, 'Start Split', units='mm', read_only=True)
        self.stop_split_ctrl = _prop_ctrls.StringProperty(conductor_group, 'Stop Split', units='mm', read_only=True)
        self.roll_ctrl = _prop_ctrls.StringProperty(conductor_group, 'Ribbon Roll', units='deg', read_only=True)

        conductor_group.addWidget(self.conductor_count_ctrl)
        conductor_group.addWidget(self.start_split_ctrl)
        conductor_group.addWidget(self.stop_split_ctrl)
        conductor_group.addWidget(self.roll_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position3d_ctrl = StartStopPosition3DControl(position_page)
        self.position_pegboard_ctrl = StartStopPositionPegboardControl(position_page)

        position_page.addWidget(self.position3d_ctrl)
        position_page.addWidget(self.position_pegboard_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)
        self.visible_pegboard_ctrl = VisiblePegboardControl(visible_page)

        visible_page.addWidget(self.visible3d_ctrl)
        visible_page.addWidget(self.visible_pegboard_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.wire_ctrl = _wire.WireControl(part_page)

        part_page.addWidget(self.wire_ctrl)

        for page in (
            general_page,
            info_page,
            position_page,
            visible_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
