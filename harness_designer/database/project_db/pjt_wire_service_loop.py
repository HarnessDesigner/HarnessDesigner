# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable, Union as _Union

import math
import numpy as np
import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from . import pjt_circuit as _pjt_circuit
from ..global_db import wire as _wire
from .mixins import (
    WireOperatingTempMixin,
    Angle3DMixin, Angle3DControl,
    AnglePegboardMixin, AnglePegboardControl,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    StartStopPositionPegboardMixin, StartStopPositionPegboardControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin,
    NameMixin, NameControl,
    NotesMixin,  NotesControl,
    SmoothMixin, SmoothControl
)
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire as _pjt_wire
    from ...objects import wire_service_loop as _wire_service_loop_obj
    from ... import ui as _ui


class PJTWireServiceLoopsTable(PJTTableBase):
    """Represent a PJT wire service loops table in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_wire_service_loops'

    _control: "PJTWireServiceLoopControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTWireServiceLoopControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoopControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe: "_ui.MainFrame") -> None:
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTWireServiceLoopControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wire_service_loops

        return wire_service_loops.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTWireServiceLoop"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTWireServiceLoop']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireServiceLoop(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTWireServiceLoop":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoop`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTWireServiceLoop or item in self:
                return PJTWireServiceLoop(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: bytes, name: str, start_point3d_id: bytes, stop_point3d_id: bytes,
               circuit_id: bytes | None, is_visible: bool, quat: np.ndarray) -> "PJTWireServiceLoop":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param start_point3d_id: Identifier for the start point 3D.
        :type start_point3d_id: bytes
        :param stop_point3d_id: Identifier for the stop point 3D.
        :type stop_point3d_id: bytes
        :param part_id: Identifier for the part.
        :type part_id: bytes
        :param circuit_id: Identifier for the circuit.
        :type circuit_id: bytes
        :param is_visible: Boolean flag for whether visible.
        :type is_visible: bool
        :param quat: Value for ``quat``.
        :type quat: :class:`np.ndarray`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoop`
        """

        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name, circuit_id=circuit_id,
            start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
            quat3d=str([float(str(v)) for v in quat.tolist()]), is_visible3d=int(is_visible),
            start_point_pegboard_id=None, stop_point_pegboard_id=None, notes='',
            angle3d='[0.0, 0.0, 0.0]', quat_pegboard='[1.0, 0.0, 0.0, 0.0]',
            angle_pegboard='[0.0, 0.0, 0.0]', is_visible_pegboard=1, smooth=None,
            operating_temp=None)

        self.db.pjt_circuits_table.members_changed(circuit_id)

        return PJTWireServiceLoop(self, db_id)


@capturable()
class PJTWireServiceLoop(PJTEntryBase, Angle3DMixin, AnglePegboardMixin, StartStopPosition3DMixin,
                         StartStopPositionPegboardMixin,
                         PartMixin, Visible3DMixin, VisiblePegboardMixin, NotesMixin, NameMixin, SmoothMixin,
                         WireOperatingTempMixin):
    """Represent a PJT wire service loop in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTWireServiceLoopsTable = None

    @_check_types.do
    def delete(self) -> None:
        """Delete this service loop row, then tell its circuit its member
        list changed.
        """
        circuit_id = self.circuit_id

        super().delete()

        self._table.db.pjt_circuits_table.members_changed(circuit_id)

    @_check_types.do
    def get_object(self) -> "_wire_service_loop_obj.WireServiceLoop":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_service_loop_obj.WireServiceLoop`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_wire_service_loop_obj.WireServiceLoop") -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop_obj.WireServiceLoop`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @dump_property(severity=2)
    @_check_types.do
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        """Return the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_terminal.PJTTerminal`
        """
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=start_position_id)

        stop_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=stop_position_id)

        if start_position_ids:
            return self.table.db.pjt_terminals_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_terminals_table[stop_position_ids[0][0]]

    @property
    @dump_property(severity=2)
    @_check_types.do
    def wire(self) -> "_pjt_wire.PJTWire":
        """Return the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_wire.PJTWire`
        """
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_wires_table.select(
            'id', start_point3d_id=start_position_id)

        stop_position_ids = self.table.db.pjt_wires_table.select(
            'id', stop_point3d_id=stop_position_id)

        if start_position_ids:
            return self.table.db.pjt_wires_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_wires_table[stop_position_ids[0][0]]

    @property
    @_check_types.do
    def length_mm(self) -> float:
        """Return the length of wire in the loop, in millimeters.

        The length of the loop that is drawn (``shapes/cylinder_helix.create_vbo``), measured along the wire's centre line: a
        straight lead-in and lead-out of one wire diameter each, and one turn of a helix whose centre track is two wire diameters
        across (the coil's inside diameter is one wire diameter, its outside diameter three) with a pitch of 1.15 wire diameters.
        Every figure scales with the wire's outside diameter.

        :returns: The length in millimeters.
        :rtype: float
        """
        diameter = float(self.part.od_mm)

        # create_vbo sweeps the wire along Helix(radius=diameter, pitch=height=diameter + diameter * 0.15), so the helix's
        # radius is one wire diameter: the centre line is a circle two wire diameters across
        radius = diameter
        pitch = height = diameter + diameter * 0.15
        num_turns = height / pitch

        total_circumference = 2 * math.pi * radius * num_turns

        length = math.sqrt(total_circumference ** 2 + height ** 2)

        # plus the two straight tails, a wire diameter each
        return length + diameter * 2.0

    @property
    @_check_types.do
    def length_m(self) -> float:
        """Return the length m.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.length_mm / 1000.0

    @property
    @_check_types.do
    def length_ft(self) -> float:
        """Return the length ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.length_m * 3.28084

    @property
    @_check_types.do
    def weight_g(self) -> float:
        """Return the weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.weight_g_m * self.length_m

    @property
    @_check_types.do
    def weight_lb(self) -> float:
        """Return the weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.weight_lb_ft * self.length_ft

    @property
    @_check_types.do
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._resistance_over(self.length_mm)

    @_check_types.do
    def _resistance_over(self, length_mm: float) -> float:
        """The resistance, in ohms, of *length_mm* of this wire service loop.

        :attr:`resistance` for a length the caller already has: working out
        ``length_mm`` can mean walking the whole route, so ``part_data()`` does it
        once and hands the number to everything that needs it.

        :param length_mm: The length in millimeters.
        :type length_mm: float
        :returns: The resistance in ohms.
        :rtype: float
        """
        resistance = self.part.resistance_1km
        # resistance per millimeter
        resistance /= 1000000.0

        return resistance * length_mm

    @property
    @_check_types.do
    def load(self) -> float:
        """The current, in amps, that flows through this wire service loop: what every
        load terminal beyond it draws, at the voltage that actually reaches
        them (the voltage terminal's voltage less the drop up to here).
        Everything between the voltage terminal and this wire service loop is not part of
        the number. ``0.0`` when it is in no circuit, or its circuit has no
        voltage terminal.

        :returns: The current in amps.
        :rtype: float
        """
        circuit_id = self.circuit_id
        if circuit_id is None:
            return 0.0

        return self._table.db.pjt_circuits_table[circuit_id].load_at(self)

    @property
    @_check_types.do
    def table(self) -> PJTWireServiceLoopsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoopsTable`
        """
        return self._table

    @property
    @dump_property(severity=2)
    @_check_types.do
    def circuit(self) -> _pjt_circuit.PJTCircuit:
        """Return the circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_circuit.PJTCircuit`
        """
        circuit_id = self.circuit_id
        if circuit_id is not None:
            return self._table.db.pjt_circuits_table[circuit_id]

    @property
    @_check_types.do
    def circuit_id(self) -> bytes | None:
        """Return the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes | None
        """
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    @_check_types.do
    def circuit_id(self, value: bytes | None) -> None:
        """Set the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes | None
        """
        old_circuit_id = self.circuit_id

        self._table.update(self._db_id, circuit_id=value)

        circuits_table = self._table.db.pjt_circuits_table
        circuits_table.members_changed(old_circuit_id, value)
        self._populate('circuit_id')

        # a circuit that is added or changes reaches every connected object
        if value != old_circuit_id:
            circuits_table.propagate(self, value)

    @property
    @dump_property(severity=2)
    @_check_types.do
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_visible', id=self._db_id)[0][0])

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool) -> None:
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible=int(value))
        self._populate('is_visible')

    _stored_part: _wire.Wire | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @dump_property(severity=2)
    @_check_types.do
    def part(self) -> _wire.Wire:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_wire.Wire`
        """
        if self._stored_part is DefaultStoredValue:
            part_id = self.part_id

            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.wires_table[part_id]

        if self._stored_part is not None:
            if self._obj is not None:
                self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTWireServiceLoopControl(QtWidgets.QTabWidget, LazyTabMixin):
    """Represent a PJT wire service loop control in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTWireServiceLoop | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTWireServiceLoop`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle3d_ctrl.set_obj(self.db_obj)
            self.angle_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position3d_ctrl.set_obj(self.db_obj)
            self.position_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._circuit_page:
            self.circuit_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.wire_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget):
        """Initialise the :class:`PJTWireServiceLoopControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTWireServiceLoop | None = None

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

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle3d_ctrl = Angle3DControl(angle_page)
        self.angle_pegboard_ctrl = AnglePegboardControl(angle_page)

        angle_page.addWidget(self.angle3d_ctrl)

        angle_page.addWidget(self.angle_pegboard_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position3d_ctrl = StartStopPosition3DControl(position_page)
        self.position_pegboard_ctrl = StartStopPositionPegboardControl(position_page)

        position_page.addWidget(self.position3d_ctrl)

        position_page.addWidget(self.position_pegboard_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible3d_ctrl)

        self._circuit_page = circuit_page = _prop_ctrls.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        circuit_page.addWidget(self.circuit_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.wire_ctrl = _wire.WireControl(part_page)

        part_page.addWidget(self.wire_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            circuit_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
