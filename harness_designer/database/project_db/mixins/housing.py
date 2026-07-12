# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import pjt_housing as _pjt_housing


class HousingMixin(BaseMixin):
    """Represent a housing mixin in :mod:`harness_designer.database.project_db.mixins.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_housing: "DefaultStoredValueType | _pjt_housing.PJTHousing | None" = DefaultStoredValue

    @property
    def housing(self) -> "_pjt_housing.PJTHousing":
        """Return the housing.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_housing.PJTHousing`
        """
        if self._stored_housing is DefaultStoredValue:
            db_id = self.housing_id
            if db_id is None:
                self._stored_housing = None
            else:
                self._stored_housing = self._table.db.pjt_housings_table[db_id]
            
        return self._stored_housing

    _stored_housing_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def housing_id(self) -> int:
        """Return the housing ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_housing_id is DefaultStoredValue:
            self._stored_housing_id = self._table.select('housing_id', id=self._db_id)[0][0]
        
        return self._stored_housing_id

    @housing_id.setter
    def housing_id(self, value: int):
        """Set the housing ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_housing_id = value
        self._stored_housing = DefaultStoredValue
        
        self._table.update(self._db_id, housing_id=value)
        self._populate('housing_id')
