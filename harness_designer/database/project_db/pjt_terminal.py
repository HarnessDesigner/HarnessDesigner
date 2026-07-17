# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase
from . import pjt_point3d as _pjt_point3d
from . import pjt_seal as _pjt_seal
from ...geometry import point as _point
from . import pjt_circuit as _pjt_circuit
from ..global_db import terminal as _terminal
from ... import logger as _logger
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Angle2DMixin, Angle2DControl,
    AnglePegMixin,
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    PositionPegMixin,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl,
    HousingMixin,
    Scale3DMixin, Scale3DControl
)


if TYPE_CHECKING:
    from . import pjt_cavity as _pjt_cavity
    from ...objects import terminal as _terminal_obj


class PJTTerminalsTable(PJTTableBase):
    """Represent a PJT terminals table in :mod:`harness_designer.database.project_db.pjt_terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_terminals'

    _control: "PJTTerminalControl" = None

    @property
    def control(self) -> "PJTTerminalControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTerminalControl`
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
        cls._control = PJTTerminalControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import terminals

        return terminals.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import terminals

        terminals.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import terminals

        terminals.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTTerminal"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTTerminal']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTerminal(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTerminal":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTerminal`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTTerminal(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, name: str, position2d_id: int, position3d_id: int, cavity_id: int) -> "PJTTerminal":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int
        :param position2d_id: Identifier for the position 2D.
        :type position2d_id: int
        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: int
        :param cavity_id: Identifier for the cavity.
        :type cavity_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTTerminal`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, name=name, cavity_id=cavity_id,
                                    point2d_id=position2d_id, point3d_id=position3d_id)

        terminal = PJTTerminal(self, db_id, self.project_id)

        # PJTCavity.terminal caches the reverse lookup (DefaultStoredValue
        # sentinel) — it has no way to know a new row now points at it, so
        # the cache is primed here directly instead of left to go stale.
        # See the cavity_id setter below for the move/reassign case.
        if cavity_id is not None:
            self.db.pjt_cavities_table[cavity_id]._stored_terminal = terminal  # NOQA

        return terminal


class PJTTerminal(PJTEntryBase, Angle3DMixin, Angle2DMixin, AnglePegMixin,
                  Position3DMixin, NotesMixin,
                  Position2DMixin, PositionPegMixin, PartMixin, Visible3DMixin,
                  Visible2DMixin, NameMixin,
                  HousingMixin, SmoothMixin, Scale3DMixin):
    """Represent a PJT terminal in :mod:`harness_designer.database.project_db.pjt_terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTTerminalsTable = None

    def delete(self) -> None:
        """Delete this terminal, clearing its cavity's cached back-reference
        first (see the cavity_id setter/PJTTerminalsTable.insert) so
        PJTCavity.terminal doesn't keep pointing at a now-deleted row.
        """
        cavity_id = self.cavity_id

        PJTEntryBase.delete(self)

        if cavity_id is not None:
            self._table.db.pjt_cavities_table[cavity_id]._stored_terminal = None  # NOQA

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        circuit = self.circuit
        cavity = self.cavity

        packet = {
            'pjt_terminals': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id],
            'pjt_points_peg': [self.position_peg_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        if cavity is not None:
            self.merge_packet_data(cavity.build_monitor_packet(), packet)

        if circuit is not None:
            self.merge_packet_data(circuit.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_terminal_obj.Terminal":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_terminal_obj.Terminal`
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

    def set_object(self, obj: "_terminal_obj.Terminal"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal_obj.Terminal`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def is_start(self) -> bool:
        """Return the is start.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        value = bool(self._table.select('is_start', id=self._db_id)[0][0])
        if value:
            # Read the raw column instead of self.load — that property
            # itself checks is_start, which would recurse right back here.
            raw_load = self._table.select('load', id=self._db_id)[0][0]
            if raw_load:
                _logger.warning('You cannot have a load set for the start terminal of a circuit')

                value = False
                self.is_start = False

        return value

    @is_start.setter
    def is_start(self, value: bool):
        """Set the is start.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if value and self.load:
            raise RuntimeError('You cannot have a load for '
                               'the start terminal of a circuit')

        if value:
            self.__check_for_other_starts()

        self._table.update(self._db_id, is_start=int(value))
        self._populate('is_start')

    def __check_for_other_starts(self):
        """Execute the check for other starts operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        db_ids = self._table.select('db_id', circuit_id=self.circuit_id, is_start=1)
        for db_id in db_ids:
            if db_id[0] != self.db_id:
                _logger.warning('A circuit cannot have multiple start points. setting '
                                'other terminal so it is not a start point')

                self._table.update(db_id[0], is_start=0)

    @property
    def voltage_drop(self) -> float:
        """Return the voltage drop.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self.is_start:
            return 0.0

        return self._table.select('voltage_drop', id=self._db_id)[0][0]

    @voltage_drop.setter
    def voltage_drop(self, value: float):
        """Set the voltage drop.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self.is_start:
            raise RuntimeError('voltage from can only be applied '
                               'to the end terminal of a circuit')

        self._table.update(self._db_id, voltage_drop=value)
        self._populate('voltage_drop')

    @property
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.resistance

    @property
    def volts(self) -> float:
        """Return the volts.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if not self.is_start:
            return 0.0

        return self._table.select('volts', id=self._db_id)[0][0]

    @volts.setter
    def volts(self, value: float):
        """Set the volts.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self.is_start:
            raise RuntimeError('volts can only be applied to the start terminal '
                               'not the end terminals of a circuit')

        self._table.update(self._db_id, volts=value)
        self._populate('volts')

    @property
    def load(self) -> float:
        """Return the load.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self.is_start:
            return 0.0

        return self._table.select('load', id=self._db_id)[0][0]

    @load.setter
    def load(self, value: float):
        """Set the load.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self.is_start:
            raise RuntimeError('loads can only be applied to the end terminals '
                               'not the start terminals of a circuit')

        self._table.update(self._db_id, load=value)
        self._populate('load')

    @property
    def table(self) -> PJTTerminalsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTTerminalsTable`
        """
        return self._table

    _stored_cavity: "_pjt_cavity.PJTCavity" = None

    @property
    def cavity(self) -> "_pjt_cavity.PJTCavity":
        """Return the cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_cavity.PJTCavity`
        """
        if self._stored_cavity is None and self._obj is not None:
            cavity_id = self.cavity_id

            if cavity_id is None:
                return None

            self._stored_cavity = self._table.db.pjt_cavities_table[cavity_id]
            self._stored_cavity.add_object(self._obj())

        return self._stored_cavity

    @property
    def cavity_id(self) -> int:
        """Return the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('cavity_id', id=self._db_id)[0][0]

    @cavity_id.setter
    def cavity_id(self, value: int):
        """Set the cavity ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        old_cavity_id = self.cavity_id

        self._stored_cavity = None

        self._table.update(self._db_id, cavity_id=value)
        self._populate('cavity_id')

        # Keep PJTCavity.terminal's cache (a reverse lookup PJTCavity has no
        # way to invalidate on its own) in sync with this row's new home —
        # see PJTTerminalsTable.insert for the initial-placement case.
        if old_cavity_id is not None and old_cavity_id != value:
            self._table.db.pjt_cavities_table[old_cavity_id]._stored_terminal = None  # NOQA

        if value is not None:
            self._table.db.pjt_cavities_table[value]._stored_terminal = self  # NOQA

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
                return

            self._stored_circuit = self._table.db.pjt_circuits_table[circuit_id]
            self._stored_circuit.add_object(self._obj())

        return self._stored_circuit

    @property
    def circuit_id(self) -> int:
        """Return the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int):
        """Set the circuit ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_circuit = None

        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    @property
    def seal(self) -> "_pjt_seal.PJTSeal":
        """Return the seal.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_seal.PJTSeal`
        """
        db_ids = self._table.db.pjt_seals_table.select('id', terminal_id=self.db_id)

        for db_id in db_ids:
            try:
                seal = self._table.db.pjt_seals_table[db_id[0]]
            except IndexError:
                continue

            return seal

    @property
    def wire_point3d_id(self) -> "int | None":
        """Return the ``pjt_points3d`` row id for the wire attachment point
        (see :attr:`wire_position3d`), lazily creating and persisting it on
        first access when the ``wire_point3d_id`` column is NULL.  ``None``
        only when the terminal's part or 3-D model has no geometry available.
        """
        if self._stored_wire_position3d is not None:
            return self._stored_wire_position3d.db_id

        wire_point3d_id = self._table.select('wire_point3d_id', id=self._db_id)[0][0]
        if wire_point3d_id is None:
            wire_point3d_id = self._compute_wire_position3d()

        return wire_point3d_id

    _stored_wire_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def wire_position3d(self) -> "_point.Point":
        """Return the wire attachment point (center of the terminal's back OBB face).

        Lazily creates and persists the point on first access when the
        ``wire_point3d_id`` column is NULL.  Returns ``None`` only when the
        terminal's part or 3-D model has no geometry available.
        """
        if self._stored_wire_position3d is None:
            wire_point3d_id = self.wire_point3d_id
            if wire_point3d_id is None:
                return None
            self._stored_wire_position3d = self._table.db.pjt_points3d_table[wire_point3d_id]
        return self._stored_wire_position3d.point

    def _compute_wire_position3d(self) -> "int | None":
        """Compute and persist the wire attachment point.

        The position is the center of the back OBB face (face opposite the
        terminal's forward face) rotated into world space by the terminal's
        current angle and offset by the terminal's current position.

        When no mesh has been processed yet (``model3d.obb`` is ``None``),
        the OBB and AABB are built from the part's physical dimensions and
        stored to the global DB so subsequent callers find them there.

        Returns the new ``pjt_points3d`` row id, or ``None`` when the
        terminal has no part assigned.
        """
        import numpy as np

        part = self.part
        if part is None:
            return None

        model3d = part.model3d
        if model3d is None:
            return None

        local_obb = model3d.obb
        if local_obb is None:
            half_w = part.width / 2.0
            half_h = part.height / 2.0
            half_l = part.length / 2.0
            local_obb = np.array([
                [-half_w, -half_h, -half_l],
                [+half_w, -half_h, -half_l],
                [-half_w, +half_h, -half_l],
                [+half_w, +half_h, -half_l],
                [-half_w, -half_h, +half_l],
                [+half_w, -half_h, +half_l],
                [-half_w, +half_h, +half_l],
                [+half_w, +half_h, +half_l],
            ], dtype=np.float32)
            model3d.obb = local_obb
            model3d.aabb = np.array([
                [-half_w, -half_h, -half_l],
                [+half_w, +half_h, +half_l],
            ], dtype=np.float32)

        fwd_face, _ = model3d.forward_up
        if fwd_face == -1:
            fwd_face = 4  # default: −Z side is the insertion face (cavity convention)

        back_face = fwd_face ^ 1
        axis = back_face // 2
        sign = back_face % 2
        sorted_i = np.argsort(local_obb[:, axis])
        corner_i = sorted_i[:4] if sign == 0 else sorted_i[4:]

        back_center = local_obb[corner_i].mean(axis=0)

        back_pt = _point.Point(
            float(str(np.float32(back_center[0]))),
            float(str(np.float32(back_center[1]))),
            float(str(np.float32(back_center[2])))
        )
        back_pt @= self.angle3d
        back_pt += self.position3d

        x, y, z = back_pt.as_float

        self._table.execute(
            'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
            (self._table.project_id, x, y, z)
        )
        self._table.commit()
        wire_point3d_id = self._table.lastrowid
        self._table.update(self._db_id, wire_point3d_id=wire_point3d_id)
        return wire_point3d_id

    _stored_seal_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def seal_position3d(self) -> "_point.Point":
        """Return the per-terminal seal position.

        Returns ``None`` until the seal is created and ``seal_point3d_id``
        is set via the :attr:`seal_point3d_id` setter.
        """
        if self._stored_seal_position3d is None:
            seal_point3d_id = self._table.select('seal_point3d_id', id=self._db_id)[0][0]
            if seal_point3d_id is None:
                return None
            self._stored_seal_position3d = self._table.db.pjt_points3d_table[seal_point3d_id]
        return self._stored_seal_position3d.point

    @property
    def seal_point3d_id(self) -> "int | None":
        """Return the DB row id of the seal position point, or ``None``."""
        return self._table.select('seal_point3d_id', id=self._db_id)[0][0]

    @seal_point3d_id.setter
    def seal_point3d_id(self, value: int):
        """Persist *value* as the seal position point id and invalidate the cache."""
        self._stored_seal_position3d = None
        self._table.update(self._db_id, seal_point3d_id=value)

    _stored_part: "_terminal.Terminal" = None

    @property
    def part(self) -> "_terminal.Terminal":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_terminal.Terminal`
        """
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.terminals_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTTerminalControl(QTabWidget, LazyTabMixin):
    """Represent a PJT terminal control in :mod:`harness_designer.database.project_db.pjt_terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTTerminal):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTTerminal`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.note_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.is_start_ctrl.SetValue(False)
                self.voltage_drop_ctrl.SetValue(0.0)
                self.volts_ctrl.SetValue(0.0)
                self.load_ctrl.SetValue(0.0)
                self.is_start_ctrl.setEnabled(False)
                self.voltage_drop_ctrl.setEnabled(False)
                self.volts_ctrl.setEnabled(False)
                self.load_ctrl.setEnabled(False)
            else:
                is_start = self.db_obj.is_start
                self.is_start_ctrl.SetValue(is_start)
                if is_start:
                    self.voltage_drop_ctrl.setEnabled(True)
                    self.volts_ctrl.setEnabled(True)
                    self.voltage_drop_ctrl.SetValue(self.db_obj.voltage_drop)
                    self.volts_ctrl.SetValue(self.db_obj.volts)
                    self.load_ctrl.setEnabled(False)
                    self.load_ctrl.SetValue(0.0)
                else:
                    self.voltage_drop_ctrl.setEnabled(False)
                    self.volts_ctrl.setEnabled(False)
                    self.voltage_drop_ctrl.SetValue(0.0)
                    self.volts_ctrl.SetValue(0.0)
                    self.load_ctrl.setEnabled(True)
                    self.load_ctrl.SetValue(self.db_obj.load)
        elif page is self._angle_page:
            self.angle2d_ctrl.set_obj(self.db_obj)
            self.angle3d_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
        elif page is self._seal_page:
            self.seal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.seal)
        elif page is self._circuit_page:
            self.circuit_ctrl.set_obj(None if self.db_obj is None else self.db_obj.circuit)
        elif page is self._part_page:
            self.terminal_ctrl.set_obj(None if self.db_obj is None else self.db_obj.part)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTTerminalControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTTerminal = None

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

        self.is_start_ctrl = _prop_ctrls.BoolProperty(general_page, 'Is Start')
        self.voltage_drop_ctrl = _prop_ctrls.FloatProperty(general_page, 'Allowed Voltage Drop', min_value=0.0, max_value=9999.99, increment=0.01, units='VDC/VAC')
        self.volts_ctrl = _prop_ctrls.FloatProperty(general_page, 'Volts', min_value=0.0, max_value=44000.00, increment=0.01, units='VDC/VAC')
        self.load_ctrl = _prop_ctrls.FloatProperty(general_page, 'Load', min_value=0.0, max_value=9999.99, increment=0.01, units='A')

        general_page.addWidget(self.is_start_ctrl)
        general_page.addWidget(self.voltage_drop_ctrl)
        general_page.addWidget(self.volts_ctrl)
        general_page.addWidget(self.load_ctrl)

        self._angle_page = angle_page = _prop_ctrls.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        angle_page.addWidget(self.angle2d_ctrl)
        angle_page.addWidget(self.angle3d_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

        self._seal_page = seal_page = _prop_ctrls.Category(self, 'Seal')
        self.seal_ctrl = _pjt_seal.PJTSealControl(seal_page)

        seal_page.addWidget(self.seal_ctrl)

        self._circuit_page = circuit_page = _prop_ctrls.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        circuit_page.addWidget(self.circuit_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.terminal_ctrl = _terminal.TerminalControl(part_page)

        part_page.addWidget(self.terminal_ctrl)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            seal_page,
            circuit_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
