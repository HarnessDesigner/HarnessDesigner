# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


class PartMixin(BaseMixin):
    """Represent a part mixin in :mod:`harness_designer.database.project_db.mixins.part`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    _stored_part_id: int | None | DefaultStoredValueType = DefaultStoredValue
    _stored_part: DefaultStoredValueType | None = DefaultStoredValue

    @property
    def part_id(self) -> int:
        """Return the part ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_part_id is DefaultStoredValue:
            self._stored_part_id = self._table.select('part_id', id=self._db_id)[0][0]
            
        return self._stored_part_id

    @part_id.setter
    def part_id(self, value: int):
        """Set the part ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_part_id = value
        self._stored_part = DefaultStoredValue
        
        self._table.update(self._db_id, part_id=value)
        self._populate('part_id')
