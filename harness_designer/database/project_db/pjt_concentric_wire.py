# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import NotesMixin, Position2DMixin


if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_wire as _pjt_wire
    from . import pjt_concentric_layer as _pjt_concentric_layer
    from ...objects import boot as _boot_obj


class PJTConcentricWiresTable(PJTTableBase):
    """Represent a PJT concentric wires table in :mod:`harness_designer.database.project_db.pjt_concentric_wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_concentric_wires'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import concentric_wires

        return concentric_wires.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentric_wires

        concentric_wires.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import concentric_wires

        concentric_wires.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTConcentricWire"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTConcentricWire']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentricWire(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentricWire":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentricWire`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTConcentricWire(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, layer_id: int, idx: int, wire_id: int, is_filler: bool) -> "PJTConcentricWire":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param layer_id: Identifier for the layer.
        :type layer_id: int
        :param idx: Value for ``idx``.
        :type idx: int
        :param wire_id: Identifier for the wire.
        :type wire_id: int
        :param is_filler: Boolean flag for whether filler.
        :type is_filler: bool
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTConcentricWire`
        """
        db_id = PJTTableBase.insert(self, layer_id=layer_id, idx=idx,
                                    wire_id=wire_id, is_filler=int(is_filler))

        return PJTConcentricWire(self, db_id, self.project_id)


class PJTConcentricWire(PJTEntryBase, NotesMixin, Position2DMixin):
    """Represent a PJT concentric wire in :mod:`harness_designer.database.project_db.pjt_concentric_wire`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTConcentricWiresTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        layer = self.layer
        wire = self.wire

        packet = {
            'pjt_concentric_wires': [self.db_id],
            'pjt_wires': [wire.db_id],
            'pjt_points2d': [self.point_id],
            'pjt_concentric_layers': [layer.db_id]
        }

        self.merge_packet_data(layer.build_monitor_packet(), packet)
        self.merge_packet_data(wire.build_monitor_packet(), packet)

        return packet
    #
    # def get_object(self) -> "_boot_obj.Boot":
    #     if self._obj is not None:
    #         return self._obj()
    #
    #     return self._obj

    # def __release_obj_ref(self, _):
    #     self._obj = None
    #
    # def set_object(self, obj: "_boot_obj.Boot"):
    #     if obj is not None:
    #         self._obj = weakref.ref(obj, self.__release_obj_ref)
    #     else:
    #         self._obj = obj
    #
    # def get_object(self) -> "_boot_obj.Boot":
    #     return self._obj
    #
    # def set_object(self, obj: "_boot_obj.Boot"):
    #     self._obj = obj

    @property
    def table(self) -> PJTConcentricWiresTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTConcentricWiresTable`
        """
        return self._table

    @property
    def layer(self) -> "_pjt_concentric_layer.PJTConcentricLayer":
        """Return the layer.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_concentric_layer.PJTConcentricLayer`
        """
        layer_id = self.layer_id
        return self._table.db.pjt_concentric_layers_table[layer_id]

    @property
    def layer_id(self) -> int:
        """Return the layer ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('layer_id', id=self._db_id)[0][0]

    @layer_id.setter
    def layer_id(self, value: int):
        """Set the layer ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, layer_id=value)
        self._populate('layer_id')

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
    def is_filler(self) -> bool:
        """Return the is filler.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return bool(self._table.select('is_filler', id=self._db_id)[0][0])

    @is_filler.setter
    def is_filler(self, value: bool):
        """Set the is filler.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, is_filler=int(value))
        self._populate('is_filler')

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        """Return the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_wire.PJTWire`
        """
        wire_id = self.wire_id
        return self.table.db.pjt_wires_table[wire_id]

    @property
    def wire_id(self) -> int:
        """Return the wire ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    def wire_id(self, value: int):
        """Set the wire ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, wire_id=value)
        self._populate('wire_id')

    @property
    def propgrid(self) -> _prop_ctrls.Property:
        """Return the propgrid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_prop_ctrls.Property`
        """
        group = _prop_ctrls.Property(f'Wire {self.idx}')

        notes_prop = self._notes_propgrid
        position_prop = self._position2d_propgrid

        is_filler_prop = _prop_ctrls.BoolProperty('Is Filler Wire', 'is_filler', self.is_filler)

        group.Append(notes_prop)
        group.Append(is_filler_prop)
        group.Append(position_prop)

        return group
