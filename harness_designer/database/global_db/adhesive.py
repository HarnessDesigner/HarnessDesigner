# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import DescriptionMixin


class AdhesivesTable(TableBase):
    """Represent an adhesives table in :mod:`harness_designer.database.global_db.adhesive`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'adhesives'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import adhesives

        return adhesives.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import adhesives

        adhesives.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)

        adhesives.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import adhesives

        adhesives.table.update_fields(self)

    def __iter__(self) -> _Iterable["Adhesive"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Adhesive']
        """
        for db_id in TableBase.__iter__(self):
            yield Adhesive(self, db_id)

    def __getitem__(self, item) -> "Adhesive":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Adhesive`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Adhesive(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', code=item)
        if db_id:
            return Adhesive(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, code: str, description: str) -> "Adhesive":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param code: Value for ``code``.
        :type code: str
        :param description: Value for ``description``.
        :type description: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Adhesive`
        """
        db_id = TableBase.insert(self, code=code, description=description)
        return Adhesive(self, db_id)


class Adhesive(EntryBase, DescriptionMixin):
    """Represent an adhesive in :mod:`harness_designer.database.global_db.adhesive`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: AdhesivesTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'adhesives': [self.db_id],
        }

        return packet

    _stored_code: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def code(self) -> str:
        """Return the code.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_code is DefaultStoredValue:
            self._stored_code = self._table.select('code', id=self._db_id)[0][0]

        return self._stored_code

    @code.setter
    def code(self, value: str):
        """Set the code.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_code = value
        self._table.update(self._db_id, code=value)
        self._populate('code')

    _stored_accessory_part_nums: DefaultStoredValueType | list[str] = DefaultStoredValue

    @property
    def accessory_part_nums(self) -> list[str]:
        """Return the accessory part nums.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        if self._stored_accessory_part_nums is DefaultStoredValue:
            part_nums = self._table.select('accessory_part_nums', id=self._db_id)[0][0]
            self._stored_accessory_part_nums = part_nums[1:-1].split(', ')

        return self._stored_accessory_part_nums

    @accessory_part_nums.setter
    def accessory_part_nums(self, value: list[str]):
        """Set the accessory part nums.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        self._stored_accessory_part_nums = value
        self._stored_accessories = DefaultStoredValue

        db_value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, accessory_part_nums=db_value)
        self._populate('accessory_part_nums')

    _stored_accessories: "DefaultStoredValueType | list[_accessory.Accessory]" = DefaultStoredValue

    @property
    def accessories(self) -> list["_accessory.Accessory"]:
        """Return the accessories.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_accessory.Accessory']
        """
        if self._stored_accessories is DefaultStoredValue:
            accessory_nums = eval(self._table.select('accessory_part_nums',
                                                     id=self._db_id)[0][0])
            res = []
            for part_number in accessory_nums:
                try:
                    res.append(self._table.db.accessories_table[part_number])
                except KeyError:
                    pass

            self._stored_accessories = res

        return self._stored_accessories


from . import accessory as _accessory  # NOQA
