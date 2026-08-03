# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from .... import check_types as _check_types


class PartMixin(BaseMixin):
    """Represent a part mixin in :mod:`harness_designer.database.project_db.mixins.part`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_part_id: bytes | None | DefaultStoredValueType = DefaultStoredValue
    _stored_part: DefaultStoredValueType | None = DefaultStoredValue

    @property
    @_check_types.do
    def part_id(self) -> bytes:
        """Return the part ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        if self._stored_part_id is DefaultStoredValue:
            self._stored_part_id = self._table.select('part_id', id=self._db_id)[0][0]

        return self._stored_part_id

    @part_id.setter
    @_check_types.do
    def part_id(self, value: bytes):
        """Set the part ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_part_id = value
        self._stored_part = DefaultStoredValue
        
        self._table.update(self._db_id, part_id=value)
        self._populate('part_id')
