# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from PySide6.QtGui import QPixmap
from ..bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType

from . import solid as _solid
from . import fluid as _fluid
from . import supp as _supp


class IPRatingsTable(TableBase):
    """Represent an ip ratings table in :mod:`harness_designer.database.global_db.ip.__init__`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'ip_ratings'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ...create_database import ip_ratings

        return ip_ratings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ...create_database import ip_ratings

        ip_ratings.table.add_to_db(self)
        ip_ratings.add_records(self._con, splash)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ...create_database import ip_ratings

        ip_ratings.table.update_fields(self)

    def __iter__(self) -> _Iterable["IPRating"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['IPRating']
        """
        for db_id in TableBase.__iter__(self):
            yield IPRating(self, db_id)

    def __getitem__(self, item) -> "IPRating":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPRating`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return IPRating(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return IPRating(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, solid_id: int, fluid_id: int, supp_id: int) -> "IPRating":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param solid_id: Identifier for the solid.
        :type solid_id: int
        :param fluid_id: Identifier for the fluid.
        :type fluid_id: int
        :param supp_id: Identifier for the supp.
        :type supp_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPRating`
        """
        db_id = TableBase.insert(self, name=name, solid_id=solid_id, fluid_id=fluid_id, supp_id=supp_id)
        return IPRating(self, db_id)


class IPRating(EntryBase):
    """Represent an ip rating in :mod:`harness_designer.database.global_db.ip.__init__`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: IPRatingsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'ip_ratings': [self.db_id],
            'ip_solids': [self.ip_solid_id],
            'ip_fluids': [self.ip_fluid_id],
            'ip_supps': [self.ip_supp_id]
        }

        return packet

    _stored_name: str | DefaultStoredValueType = DefaultStoredValue

    @property
    def name(self):
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self._stored_name is DefaultStoredValue:
            self._stored_name = self._table.select('name', id=self._db_id)[0][0]

        return self._stored_name

    _stored_ip_solid: "DefaultStoredValueType | _solid.IPSolid" = DefaultStoredValue

    @property
    def ip_solid(self) -> _solid.IPSolid:
        """Return the ip solid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_solid.IPSolid`
        """
        if self._stored_ip_solid is DefaultStoredValue:
            ip_solid_id = self.ip_solid_id
            self._stored_ip_solid = self._table.db.ip_solids_table[ip_solid_id]

        return self._stored_ip_solid

    @ip_solid.setter
    def ip_solid(self, value: _solid.IPSolid):
        """Set the ip solid.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: :class:`_solid.IPSolid`
        """
        self._stored_ip_solid = value
        self._stored_ip_solid_id = value.db_id

        self._table.update(self._db_id, solid_id=value.db_id)

    _stored_ip_solid_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def ip_solid_id(self) -> int:
        """Return the ip solid ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_ip_solid_id is DefaultStoredValue:
            self._stored_ip_solid_id = self._table.select('solid_id', id=self._db_id)[0][0]

        return self._stored_ip_solid_id

    @ip_solid_id.setter
    def ip_solid_id(self, value: int):
        """Set the ip solid ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_ip_solid_id = value
        self._stored_ip_solid = DefaultStoredValue

        self._table.update(self._db_id, solid_id=value)

    _stored_ip_fluid: "DefaultStoredValueType | _fluid.IPFluid" = DefaultStoredValue

    @property
    def ip_fluid(self) -> _fluid.IPFluid:
        """Return the ip fluid.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_fluid.IPFluid`
        """
        if self._stored_ip_fluid is DefaultStoredValue:
            ip_fluid_id = self.ip_fluid_id
            self._stored_ip_fluid = self._table.db.ip_fluids_table[ip_fluid_id]

        return self._stored_ip_fluid

    @ip_fluid.setter
    def ip_fluid(self, value: _fluid.IPFluid):
        """Set the ip fluid.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: :class:`_fluid.IPFluid`
        """
        self._stored_ip_fluid = value
        self._stored_ip_fluid_id = value.db_id

        self._table.update(self._db_id, fluid_id=value.db_id)

    _stored_ip_fluid_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def ip_fluid_id(self) -> int:
        """Return the ip fluid ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_ip_fluid_id is DefaultStoredValue:
            self._stored_ip_fluid_id = self._table.select('fluid_id', id=self._db_id)[0][0]

        return self._stored_ip_fluid_id

    @ip_fluid_id.setter
    def ip_fluid_id(self, value: int):
        """Set the ip fluid ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_ip_fluid_id = value
        self._stored_ip_fluid = DefaultStoredValue

        self._table.update(self._db_id, fluid_id=value)

    _stored_ip_supp: "DefaultStoredValueType | _supp.IPSupp | None" = DefaultStoredValue

    @property
    def ip_supp(self) -> _supp.IPSupp | None:
        """Return the ip supp.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: _supp.IPSupp | None
        """
        if self._stored_ip_supp is DefaultStoredValue:
            ip_supp_id = self.ip_supp_id
            if ip_supp_id is None:
                self._stored_ip_supp = None
            else:
                self._stored_ip_supp = self._table.db.ip_supps_table[ip_supp_id]

        return self._stored_ip_supp

    @ip_supp.setter
    def ip_supp(self, value: _supp.IPSupp | None):
        """Set the ip supp.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: _supp.IPSupp | None
        """
        self._stored_ip_supp = value

        if value is None:
            self._stored_ip_supp_id = None
            self._table.update(self._db_id, supp_id=None)
        else:
            self._stored_ip_supp_id = value.db_id
            self._table.update(self._db_id, supp_id=value.db_id)

    _stored_ip_supp_id: int | None | DefaultStoredValueType = DefaultStoredValue

    @property
    def ip_supp_id(self) -> int | None:
        """Return the ip supp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int | None
        """
        if self._stored_ip_supp_id is DefaultStoredValue:
            self._stored_ip_supp_id = self._table.select('supp_id', id=self._db_id)[0][0]

        return self._stored_ip_supp_id

    @ip_supp_id.setter
    def ip_supp_id(self, value: int | None):
        """Set the ip supp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int | None
        """
        self._stored_ip_supp_id = value
        self._stored_ip_supp = DefaultStoredValue

        self._table.update(self._db_id, supp_id=value)

    @property
    def short_desc(self) -> str:
        """Return the short desc.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        supp = self.ip_supp
        if supp is None:
            return f'{self.ip_solid.short_desc}\n{self.ip_fluid.short_desc}'

        return f'{self.ip_solid.short_desc}\n{self.ip_fluid.short_desc}\n{supp.description}'

    @property
    def description(self) -> str:
        """Return the description.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        supp = self.ip_supp
        if supp is None:
            return f'{self.ip_solid.description}\n\n{self.ip_fluid.description}'

        return f'{self.ip_solid.description}\n\n{self.ip_fluid.description}\n\n{supp.description}'

    @property
    def pixmap(self) -> QPixmap:
        """Return the pixmap.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`QPixmap`
        """
        simg = self.ip_solid.icon
        fimg = self.ip_fluid.icon

        img = simg | fimg

        return img.pixmap
