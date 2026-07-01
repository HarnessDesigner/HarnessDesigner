# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import math
import numpy as np
import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase
from . import pjt_circuit as _pjt_circuit
from ..global_db import wire as _wire
from .mixins import (
    Angle3DMixin, Angle3DControl,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin,  NotesControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire as _pjt_wire
    from ...objects import wire_service_loop as _wire_service_loop_obj


class PJTWireServiceLoopsTable(PJTTableBase):
    """Represent a PJT wire service loops table in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_wire_service_loops'

    _control: "PJTWireServiceLoopControl" = None

    @property
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
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTWireServiceLoopControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wire_service_loops

        return wire_service_loops.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_service_loops

        wire_service_loops.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWireServiceLoop"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTWireServiceLoop']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireServiceLoop(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireServiceLoop":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoop`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTWireServiceLoop(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str, start_point3d_id: int, stop_point3d_id: int,
               circuit_id: int, is_visible: bool, quat: np.ndarray) -> "PJTWireServiceLoop":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param start_point3d_id: Identifier for the start point 3D.
        :type start_point3d_id: int
        :param stop_point3d_id: Identifier for the stop point 3D.
        :type stop_point3d_id: int
        :param part_id: Identifier for the part.
        :type part_id: int
        :param circuit_id: Identifier for the circuit.
        :type circuit_id: int
        :param is_visible: Boolean flag for whether visible.
        :type is_visible: bool
        :param quat: Value for ``quat``.
        :type quat: :class:`np.ndarray`
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoop`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, name=name, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id,
                                    stop_point3d_id=stop_point3d_id,
                                    quat=str([float(str(v)) for v in quat.tolist()]),
                                    is_visible=int(is_visible))

        return PJTWireServiceLoop(self, db_id, self.project_id)


class PJTWireServiceLoop(PJTEntryBase, Angle3DMixin, StartStopPosition3DMixin,
                         PartMixin, Visible3DMixin, NotesMixin, NameMixin, SmoothMixin):
    """Represent a PJT wire service loop in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTWireServiceLoopsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        circuit = self.circuit

        packet = {
            'pjt_wire_service_loops': [self.db_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d],
        }

        if circuit is not None:
            self.merge_packet_data(circuit.build_monitor_packet(), packet)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_service_loop_obj.WireServiceLoop":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_service_loop_obj.WireServiceLoop`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    def set_object(self, obj: "_wire_service_loop_obj.WireServiceLoop"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop_obj.WireServiceLoop`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def terminal(self) -> "_pjt_terminal.PJTTerminal":
        """Return the terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_terminal.PJTTerminal`
        """
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=start_position_id)[0][0]

        stop_position_ids = self.table.db.pjt_terminals_table.select(
            'id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_terminals_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_terminals_table[stop_position_ids[0][0]]

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        """Return the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_wire.PJTWire`
        """
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_wires_table.select(
            'id', wire_point3d_id=start_position_id)[0][0]

        stop_position_ids = self.table.db.pjt_wires_table.select(
            'id', wire_point3d_id=stop_position_id)[0][0]

        if start_position_ids:
            return self.table.db.pjt_wires_table[start_position_ids[0][0]]

        if stop_position_ids:
            return self.table.db.pjt_wires_table[stop_position_ids[0][0]]

    @property
    def length_mm(self) -> float:
        """Return the length mm.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        diameter = self.part.od_mm
        pitch = diameter + diameter * 0.15
        height = diameter + diameter * 0.15

        length = ((height / pitch) *
                  math.sqrt(math.pow(math.pi * diameter, 2.0) +
                            math.pow(pitch, 2.0)))
        length += diameter

        return length

    @property
    def length_m(self) -> float:
        """Return the length m.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.length_mm / 1000.0

    @property
    def length_ft(self) -> float:
        """Return the length ft.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.length_m * 3.28084

    @property
    def weight_g(self) -> float:
        """Return the weight g.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.weight_g_m * self.length_m

    @property
    def weight_lb(self) -> float:
        """Return the weight lb.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.weight_lb_ft * self.length_ft

    @property
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        resistance = self.part.resistance_1km

        # resistance per millimeter
        resistance /= 1000000.0

        return resistance * self.length_mm

    @property
    def table(self) -> PJTWireServiceLoopsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireServiceLoopsTable`
        """
        return self._table

    _stored_circuit: "_pjt_circuit.PJTCircuit" = None

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        """Return the circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_circuit.PJTCircuit`
        """
        if self._stored_circuit is None and self._obj is not None:
            circuit_id = self.circuit_id

            if circuit_id is None:
                return None

            self._stored_circuit = self._table.db.pjt_circuits_table[circuit_id]
            self._stored_circuit.add_object(self._obj())

        return self._stored_circuit

    @property
    def circuit_id(self) -> int | None:
        """Return the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int | None):
        """Set the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int | None
        """
        if value is None:
            self._stored_circuit = None

        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_visible', id=self._db_id)[0][0])

    @is_visible.setter
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_visible=int(value))
        self._populate('is_visible')

    _stored_part: "_wire.Wire" = None

    @property
    def part(self) -> "_wire.Wire":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_wire.Wire`
        """
        if self._stored_part is None and self._obj is not None:

            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.wires_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTWireServiceLoopControl(QTabWidget, LazyTabMixin):
    """Represent a PJT wire service loop control in :mod:`harness_designer.database.project_db.pjt_wire_service_loop`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTWireServiceLoop):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTWireServiceLoop`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._angle_page:
            self.angle3d_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._circuit_page:
            self.circuit_ctrl.set_obj(None if self.db_obj is None else self.db_obj.circuit)
        elif page is self._part_page:
            self.wire_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTWireServiceLoopControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTWireServiceLoop = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
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

        angle_page.addWidget(self.angle3d_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position3d_ctrl = StartStopPosition3DControl(position_page)

        position_page.addWidget(self.position3d_ctrl)

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
