# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import wire as _wire
from . import pjt_circuit as _pjt_circuit
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import line as _line
from .mixins import (
    StartStopPosition3DMixin, StartStopPosition3DControl,
    StartStopPosition2DMixin, StartStopPosition2DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_terminal as _pjt_terminal
    from . import pjt_wire_marker as _pjt_wire_marker
    from ...geometry import point as _point
    from ...objects import wire as _wire_obj


class PJTWiresTable(PJTTableBase):
    """Represent a PJT wires table in :mod:`harness_designer.database.project_db.pjt_wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_wires'

    _control: "PJTWireControl" = None

    @property
    def control(self) -> "PJTWireControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireControl`
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
        cls._control = PJTWireControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wires

        return wires.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wires

        wires.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wires

        wires.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWire"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTWire']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWire(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWire":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWire`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTWire(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str, circuit_id: int, start_point3d_id: int | None, stop_point3d_id: int | None,
               start_point2d_id: int | None, stop_point2d_id: int | None, is_visible3d: bool, is_visible2d: bool,
               layer_view_point_id: int | None, layer_id: int | None, is_filler_wire: bool) -> "PJTWire":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int
        :param circuit_id: Identifier for the circuit.
        :type circuit_id: int
        :param start_point3d_id: Identifier for the start point 3D.
        :type start_point3d_id: int | None
        :param stop_point3d_id: Identifier for the stop point 3D.
        :type stop_point3d_id: int | None
        :param start_point2d_id: Identifier for the start point 2D.
        :type start_point2d_id: int | None
        :param stop_point2d_id: Identifier for the stop point 2D.
        :type stop_point2d_id: int | None
        :param is_visible3d: Boolean flag for whether visible 3D.
        :type is_visible3d: bool
        :param is_visible2d: Boolean flag for whether visible 2D.
        :type is_visible2d: bool
        :param layer_view_point_id: Identifier for the layer view point.
        :type layer_view_point_id: int | None
        :param layer_id: Identifier for the layer.
        :type layer_id: int | None
        :param is_filler_wire: Boolean flag for whether filler wire.
        :type is_filler_wire: bool
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWire`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, name=name, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
                                    start_point2d_id=start_point2d_id, stop_point2d_id=stop_point2d_id,
                                    is_visible3d=int(is_visible3d), is_visible2d=int(is_visible2d),
                                    layer_view_point_id=layer_view_point_id, layer_id=layer_id,
                                    is_filler_wire=int(is_filler_wire))

        return PJTWire(self, db_id, self.project_id)


class PJTWire(PJTEntryBase, StartStopPosition3DMixin, PartMixin, StartStopPosition2DMixin,
              Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin, SmoothMixin):
    """Represent a PJT wire in :mod:`harness_designer.database.project_db.pjt_wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTWiresTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        layer_view_position_id = self.layer_view_position_id

        start_position2d_id = self.start_position2d_id
        stop_position2d_id = self.stop_position2d_id

        start_position3d_id = self.start_position3d_id
        stop_position3d_id = self.stop_position3d_id

        packet = {
            'pjt_wires': [self.db_id],
            'wires': [self.part_id]
        }

        if None not in (start_position3d_id, stop_position3d_id):
            packet['pjt_points3d'] = [start_position3d_id, stop_position3d_id]

        if None not in (start_position2d_id, stop_position2d_id):
            packet['pjt_points2d'] = [start_position2d_id, stop_position2d_id]

        if layer_view_position_id is not None:
            if 'pjt_points2d' not in packet:
                packet['pjt_points2d'] = []

            packet['pjt_points2d'].append(layer_view_position_id)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_obj.Wire":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_obj.Wire`
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

    def set_object(self, obj: "_wire_obj.Wire"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_obj.Wire`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def terminals(self) -> list["_pjt_terminal.PJTTerminal"]:
        """Return the terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_terminal.PJTTerminal']
        """
        start_position_id = self.start_position3d_id
        stop_position_id = self.stop_position3d_id

        start_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=start_position_id)
        stop_position_ids = self.table.db.pjt_terminals_table.select('id', wire_point3d_id=stop_position_id)

        res = []

        if start_position_ids:
            res.append(self.table.db.pjt_terminals_table[start_position_ids[0][0]])

        if stop_position_ids:
            res.append(self.table.db.pjt_terminals_table[stop_position_ids[0][0]])

        return res

    @property
    def wire_markers(self) -> list["_pjt_wire_marker.PJTWireMarker"]:
        """Return the wire markers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire_marker.PJTWireMarker']
        """
        db_ids = self._table.db.pjt_wire_markers_table.select('id', wire_id=self.db_id)
        res = []
        for db_id in db_ids:
            res.append(self._table.db.pjt_wire_markers_table[db_id[0]])

        return res

    _stored_layer_view_position: "_pjt_point2d.PJTPoint2D | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def layer_view_position(self) -> "_point.Point":
        """Return the layer view position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_layer_view_position is DefaultStoredValue:
            point_id = self.layer_view_position_id

            if point_id is None:
                self._stored_layer_view_position = None
            else:
                self._stored_layer_view_position = self._table.db.pjt_points2d_table[point_id]

        if self._stored_layer_view_position is not None:
            if self._obj is not None:
                self._stored_layer_view_position.add_object(self._obj())

            point = self._stored_layer_view_position.point
        else:
            point = None

        return point

    _stored_layer_view_position_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def layer_view_position_id(self) -> int:
        """Return the layer view position ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_layer_view_position_id is DefaultStoredValue:
            self._stored_layer_view_position_id = self._table.select('layer_view_point_id', id=self._db_id)[0][0]

        return self._stored_layer_view_position_id

    @layer_view_position_id.setter
    def layer_view_position_id(self, value: int):
        """Set the layer view position ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_layer_view_position_id = value
        self._stored_layer_view_position = DefaultStoredValue

        self._table.update(self._db_id, layer_view_point_id=value)
        self._populate('layer_view_position_id')

    _stored_layer_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def layer_id(self) -> int | None:
        """Return the layer ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        if self._stored_layer_id is DefaultStoredValue:
            self._stored_layer_id = self._table.select('layer_id', id=self._db_id)[0][0]

        return self._stored_layer_id

    @layer_id.setter
    def layer_id(self, value: int | None):
        """Set the layer ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int | None
        """
        self._stored_layer_id = value
        self._table.update(self._db_id, layer_id=value)
        self._populate('layer_id')

    _stored_is_filler_wire: bool | DefaultStoredValueType = DefaultStoredValue

    @property
    def is_filler_wire(self) -> bool:
        """Return the is filler wire.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        if self._stored_is_filler_wire is DefaultStoredValue:
            self._stored_is_filler_wire = bool(self._table.select('is_filler_wire', id=self._db_id)[0][0])

        return self._stored_is_filler_wire

    @is_filler_wire.setter
    def is_filler_wire(self, value: bool):
        """Set the is filler wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._stored_is_filler_wire = value
        self._table.update(self._db_id, is_filler_wire=int(value))
        self._populate('is_filler_wire')

    @property
    def length_mm(self) -> float:
        """Return the length mm.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return _line.Line(self.start_position3d, self.stop_position3d).length()

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
        length = _line.Line(self.start_position3d, self.stop_position3d).length()
        return resistance * length

    @property
    def table(self) -> PJTWiresTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWiresTable`
        """
        return self._table

    _stored_circuit: "_pjt_circuit.PJTCircuit | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        """Return the circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_circuit.PJTCircuit`
        """
        if self._stored_circuit is DefaultStoredValue:
            circuit_id = self.circuit_id
            if circuit_id is None:
                self._stored_circuit = None
            else:
                self._stored_circuit = self._table.db.pjt_circuits_table[circuit_id]

        return self._stored_circuit

    _stored_circuit_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def circuit_id(self) -> int:
        """Return the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_circuit_id is DefaultStoredValue:
            self._stored_circuit_id = self._table.select('circuit_id', id=self._db_id)[0][0]

        return self._stored_circuit_id

    @circuit_id.setter
    def circuit_id(self, value: int):
        """Set the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_circuit_id = value
        self._stored_circuit = DefaultStoredValue

        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    _stored_part: "_wire.Wire | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    def part(self) -> "_wire.Wire":
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


class PJTWireControl(QTabWidget, LazyTabMixin):
    """Represent a PJT wire control in :mod:`harness_designer.database.project_db.pjt_wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def _update_position3d(self, _):
        """Update the position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self.length_mm_ctrl.SetValue(str(self.db_obj.length_mm))
        self.length_m_ctrl.SetValue(str(self.db_obj.length_m))
        self.length_ft_ctrl.SetValue(str(self.db_obj.length_ft))
        self.weight_g_ctrl.SetValue(str(self.db_obj.weight_g))
        self.weight_lb_ctrl.SetValue(str(self.db_obj.weight_lb))
        self.resistance_ctrl.SetValue(str(self.db_obj.resistance))

    def set_obj(self, db_obj: PJTWire):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTWire`
        """
        if self.db_obj is not None:
            self.db_obj.start_position3d.unbind(self._update_position3d)
            self.db_obj.stop_position3d.unbind(self._update_position3d)
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.is_filler_wire_ctrl.SetValue(False)
                self.is_filler_wire_ctrl.setEnabled(False)
            else:
                self.is_filler_wire_ctrl.SetValue(self.db_obj.is_filler_wire)
                self.is_filler_wire_ctrl.setEnabled(True)
        elif page is self._info_page:
            if self.db_obj is None:
                self.length_mm_ctrl.SetValue('')
                self.length_m_ctrl.SetValue('')
                self.length_ft_ctrl.SetValue('')
                self.weight_g_ctrl.SetValue('')
                self.weight_lb_ctrl.SetValue('')
                self.resistance_ctrl.SetValue('')
            else:
                self.length_mm_ctrl.SetValue(str(self.db_obj.length_mm))
                self.length_m_ctrl.SetValue(str(self.db_obj.length_m))
                self.length_ft_ctrl.SetValue(str(self.db_obj.length_ft))
                self.weight_g_ctrl.SetValue(str(self.db_obj.weight_g))
                self.weight_lb_ctrl.SetValue(str(self.db_obj.weight_lb))
                self.resistance_ctrl.SetValue(str(self.db_obj.resistance))
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
            if self.db_obj is not None:
                self.db_obj.start_position3d.bind(self._update_position3d)
                self.db_obj.stop_position3d.bind(self._update_position3d)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._circuit_page:
            self.circuit_ctrl.set_obj(None if self.db_obj is None else self.db_obj.circuit)
        elif page is self._part_page:
            self.wire_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTWireControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTWire = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)
        self.is_filler_wire_ctrl = _prop_ctrls.BoolProperty(general_page, 'Is Filler Wire')

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.note_ctrl)
        general_page.addWidget(self.smooth_ctrl)
        general_page.addWidget(self.is_filler_wire_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')

        self.position2d_ctrl = StartStopPosition2DControl(position_page)
        self.position3d_ctrl = StartStopPosition3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

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

        electrical_group = _prop_ctrls.Property(info_page, 'Electrical', orientation='vertical')
        info_page.addWidget(electrical_group)

        self.resistance_ctrl = _prop_ctrls.StringProperty(electrical_group, 'Resistance', units='Ω', read_only=True)

        electrical_group.addWidget(self.resistance_ctrl)

        self._circuit_page = circuit_page = _prop_ctrls.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        circuit_page.addWidget(self.circuit_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.wire_ctrl = _wire.WireControl(part_page)

        part_page.addWidget(self.wire_ctrl)

        for page in (
            general_page,
            info_page,
            position_page,
            visible_page,
            circuit_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
