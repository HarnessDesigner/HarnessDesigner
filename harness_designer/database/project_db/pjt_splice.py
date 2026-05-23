# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# TODO: Rewrite the splices so they accept models and a set number
#       of splice points. It also needs to be written so there can be a
#       single splice point and the number of connected wires would be
#       dictated by the diameter of the splice

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..global_db import splice as _splice
from . import pjt_circuit as _pjt_circuit
from .pjt_bases import PJTEntryBase, PJTTableBase
from ...geometry import point as _point
from .mixins import (
    PartMixin,
    Position2DMixin, Position2DControl,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl
)


if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_wire as _pjt_wire
    from ...objects import splice as _splice_obj


class PJTSplicesTable(PJTTableBase):
    """Represent a PJT splices table in :mod:`harness_designer.database.project_db.pjt_splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_splices'

    _control: "PJTSpliceControl" = None

    @property
    def control(self) -> "PJTSpliceControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSpliceControl`
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
        cls._control = PJTSpliceControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import splices

        return splices.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import splices

        splices.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import splices

        splices.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTSplice"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTSplice']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSplice(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTSplice":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSplice`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTSplice(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, start_point3d_id: int, stop_point3d_id: int,
               branch_point3d_id: int, point2d_id: int, circuit_id: int) -> "PJTSplice":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int
        :param start_point3d_id: Identifier for the start point 3D.
        :type start_point3d_id: int
        :param stop_point3d_id: Identifier for the stop point 3D.
        :type stop_point3d_id: int
        :param branch_point3d_id: Identifier for the branch point 3D.
        :type branch_point3d_id: int
        :param point2d_id: Identifier for the point 2D.
        :type point2d_id: int
        :param circuit_id: Identifier for the circuit.
        :type circuit_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTSplice`
        """

        db_id = PJTTableBase.insert(self, part_id=part_id, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
                                    branch_point3d_id=branch_point3d_id, point2d_id=point2d_id)

        return PJTSplice(self, db_id, self.project_id)


class PJTSplice(PJTEntryBase, PartMixin, StartStopPosition3DMixin, Position2DMixin,
                Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin):
    """Represent a PJT splice in :mod:`harness_designer.database.project_db.pjt_splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTSplicesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        packet = {
            'pjt_cavities': [self.db_id],
            'cavities': [self.part_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d_id, self.branch_position3d_id],
            'pjt_points2d': [self.position2d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_splice_obj.Splice":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_splice_obj.Splice`
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

    def set_object(self, obj: "_splice_obj.Splice"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice_obj.Splice`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTSplicesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTSplicesTable`
        """
        return self._table

    @property
    def wires(self) -> list[list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"]]:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[list['_pjt_wire.PJTWire'], list['_pjt_wire.PJTWire'], list['_pjt_wire.PJTWire']]
        """
        start_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.start_position3d_id)
        start_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.start_position3d_id)

        stop_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.stop_position3d_id)
        stop_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.stop_position3d_id)

        branch_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.branch_position3d_id)
        branch_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.branch_position3d_id)

        def _get_wires(rows):
            """Return the wires.

            UNKNOWN details are inferred from the callable name and signature.

            :param rows: Value for ``rows``.
            :type rows: UNKNOWN
            :returns: Return value. UNKNOWN details.
            :rtype: UNKNOWN
            """
            ret_ = []
            for row in rows:
                ret_.append(self._table.db.pjt_wires_table[row[0]])

            return ret_

        start_wires = _get_wires(start_db_ids1)
        start_wires.extend(_get_wires(start_db_ids2))

        stop_wires = _get_wires(stop_db_ids1)
        stop_wires.extend(_get_wires(stop_db_ids2))

        branch_wires = _get_wires(branch_db_ids1)
        branch_wires.extend(_get_wires(branch_db_ids2))

        return [start_wires, stop_wires, branch_wires]

    _stored_branch_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def branch_position3d(self) -> "_point.Point":
        """Return the branch position 3D.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        if self._stored_branch_position3d is None and self._obj is not None:

            point_id = self.branch_position3d_id
            self._stored_branch_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_branch_position3d.add_object(self._obj())

        return self._stored_branch_position3d.point

    @property
    def branch_position3d_id(self) -> int:
        """Return the branch position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        point_id = self._table.select('branch_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(
                f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.branch_position3d_id = point_id

        return point_id

    @branch_position3d_id.setter
    def branch_position3d_id(self, value: int):
        """Set the branch position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, branch_point3d_id=value)
        self._populate('branch_position3d_id')

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        """Return the circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_circuit.PJTCircuit`
        """
        circuit_id = self.circuit_id
        return self._table.db.pjt_circuits_table[circuit_id]

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
        self._table.update(self._db_id, circuit_id=value)
        self._populate('circuit_id')

    @property
    def resistance(self) -> float:
        """Return the resistance.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.part.resistance

    @property
    def part(self) -> "_splice.Splice":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_splice.Splice`
        """
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.splices_table[part_id]


class PJTSpliceControl(QTabWidget):
    """Represent a PJT splice control in :mod:`harness_designer.database.project_db.pjt_splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTSplice):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTSplice`
        """
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.splice_ctrl.set_obj(None)
            self.branch_position3d_ctrl.SetValue(None)
            self.circuit_ctrl.set_obj(None)
        else:
            self.splice_ctrl.set_obj(db_obj.part)
            self.branch_position3d_ctrl.SetValue(db_obj.branch_position3d)
            self.circuit_ctrl.set_obj(db_obj.circuit)

    def __init__(self, parent):
        """Initialise the :class:`PJTSpliceControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTSplice = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        position_page = _prop_ctrls.Category(self, 'Position')

        self.position2d_ctrl = Position2DControl(position_page)
        self.branch_position3d_ctrl = _prop_ctrls.Position3DProperty(position_page, '3D Branch Position')
        self.position3d_ctrl = StartStopPosition3DControl(position_page)

        visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        circuit_page = _prop_ctrls.Category(self, 'Circuit')
        self.circuit_ctrl = _pjt_circuit.PJTCircuitControl(circuit_page)

        part_page = _prop_ctrls.Category(self, 'Part')
        self.splice_ctrl = _splice.SpliceControl(part_page)

        for page in (
            general_page,
            position_page,
            visible_page,
            circuit_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())
            page.Realize()
