# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import NotesMixin


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_concentric_wire as _pjt_concentric_wire


class PJTConcentricLayersTable(PJTTableBase):
    """Represent a PJT concentric layers table in :mod:`harness_designer.database.project_db.pjt_concentric_layer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_concentric_layers'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import concentric_layers

        return concentric_layers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentric_layers

        concentric_layers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentric_layers

        concentric_layers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTConcentricLayer"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTConcentricLayer']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentricLayer(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentricLayer":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentricLayer`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTConcentricLayer(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, idx: int, num_wires: int, num_fillers: int,
               concentric_id: int, diameter: float) -> "PJTConcentricLayer":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param idx: Value for ``idx``.
        :type idx: int
        :param num_wires: Value for ``num_wires``.
        :type num_wires: int
        :param num_fillers: Value for ``num_fillers``.
        :type num_fillers: int
        :param concentric_id: Identifier for the concentric.
        :type concentric_id: int
        :param diameter: Value for ``diameter``.
        :type diameter: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentricLayer`
        """

        db_id = PJTTableBase.insert(self, idx=idx, num_wires=num_wires, num_fillers=num_fillers,
                                    concentric_id=concentric_id, diameter=diameter)

        return PJTConcentricLayer(self, db_id, self.project_id)


class PJTConcentricLayer(PJTEntryBase, NotesMixin):
    """Represent a PJT concentric layer in :mod:`harness_designer.database.project_db.pjt_concentric_layer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTConcentricLayersTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        concentric = self.concentric

        packet = {
            'pjt_concentric_layers': [self.db_id],
            'pjt_concentrics': [concentric.db_id]
        }

        self.merge_packet_data(concentric.build_monitor_packet(), packet)

        return packet

    # def get_object(self) -> "_boot_obj.Boot":
    #     if self._obj is not None:
    #         return self._obj()
    #
    #     return self._obj
    #
    # def __release_obj_ref(self, _):
    #     self._obj = None
    #
    # def set_object(self, obj: "_boot_obj.Boot"):
    #     if obj is not None:
    #         self._obj = weakref.ref(obj, self.__release_obj_ref)
    #     else:
    #         self._obj = obj
    #

    @property
    def table(self) -> PJTConcentricLayersTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricLayersTable`
        """
        return self._table

    @property
    def wires(self) -> list["_pjt_concentric_wire.PJTConcentricWire"]:
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_concentric_wire.PJTConcentricWire']
        """
        res = []
        db_ids = self._table.db.pjt_concentric_wires_table.select('id', layer_id=self.db_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_concentric_wires_table[db_id[0]])

        return res

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        """Return the concentric.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_concentric.PJTConcentric`
        """
        concentric_id = self.concentric_id
        return self._table.db.pjt_concentrics_table[concentric_id]

    @property
    def concentric_id(self) -> int:
        """Return the concentric ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('concentric_id', id=self._db_id)[0][0]

    @concentric_id.setter
    def concentric_id(self, value: int):
        """Set the concentric ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, concentric_id=value)
        self._populate('concentric_id')

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
    def num_wires(self) -> int:
        """Return the num wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('num_wires', id=self._db_id)[0][0]

    @num_wires.setter
    def num_wires(self, value: int):
        """Set the num wires.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, num_wires=value)
        self._populate('num_wires')

    @property
    def num_fillers(self) -> int:
        """Return the num fillers.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('num_fillers', id=self._db_id)[0][0]

    @num_fillers.setter
    def num_fillers(self, value: int):
        """Set the num fillers.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, num_fillers=value)
        self._populate('num_fillers')

    @property
    def diameter(self) -> float:
        """Return the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._table.select('diameter', id=self._db_id)[0][0]

    @diameter.setter
    def diameter(self, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._table.update(self._db_id, diameter=value)
        self._populate('diameter')

    @property
    def propgrid(self) -> _prop_ctrls.Property:
        """Return the propgrid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_prop_ctrls.Property`
        """

        group = _prop_ctrls.Property(f'Layer {self.idx}')

        notes_prop = self._notes_propgrid

        num_fillers_prop = _prop_ctrls.IntProperty(
            'Filler Count', 'num_fillders',
            self.num_fillers, min_value=0, max_value=999)

        num_wires = _prop_ctrls.IntProperty(
            'Wire Count', 'num_wires',
            self.num_wires, min_value=0, max_value=999)

        diameter = _prop_ctrls.FloatProperty(
            'Diameter', 'diameter', self.diameter,
            min_value=0.0, max_value=999.0, increment=0.1, units='mm')

        wire_prop = _prop_ctrls.Property(f'Wires')

        for wire in self.wires:
            wire_prop.Append(wire.propgrid)

        group.Append(notes_prop)
        group.Append(num_fillers_prop)
        group.Append(num_wires)
        group.Append(diameter)
        group.Append(wire_prop)

        return group
