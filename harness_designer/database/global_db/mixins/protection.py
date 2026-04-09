from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin

if TYPE_CHECKING:
    from .. import protection as _protection


class ProtectionMixin(BaseMixin):

    @property
    def protection_id(self) -> int:
        return self._table.select('protection_id', id=self._db_id)[0][0]

    @protection_id.setter
    def protection_id(self, value: int):
        self._table.update(self._db_id, protection_id=value)

    @property
    def protections(self) -> "_protection.Protection":
        protection_id = self.protection_id
        return self.table.db.protections_table[protection_id]

    @property
    def _protections_propgrid(self) -> _prop_grid.Property:
        prop = self.protections.propgrid

        return prop
