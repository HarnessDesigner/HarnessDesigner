from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import family as _family  # NOQA


class FamilyMixin(BaseMixin):

    @property
    def family(self) -> "_family.Family":
        from .. import family as _family  # NOQA

        family_id = self._table.select('family_id', id=self._db_id)
        return _family.Family(self._table.db.families_table, family_id[0][0])

    @family.setter
    def family(self, value: "_family.Family"):
        self._table.update(self._db_id, family_id=value.db_id)

    @property
    def family_id(self) -> int:
        return self._table.select('family_id', id=self._db_id)[0][0]

    @family_id.setter
    def family_id(self, value: int):
        self._table.update(self._db_id, family_id=value)

    @property
    def _family_propgrid(self) -> _prop_grid.Property:
        prop = self.family.propgrid
        return prop
